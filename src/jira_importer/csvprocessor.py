#!/usr/bin/env python
# -*- coding: utf-8 -*-
#lint:disable=unused-variable
#agent:disable=unused-variable
#agent:disable=unreachable-code

from typing import Dict, List, Optional, Any, Tuple, Literal

"""
Script Name: csvprocessor.py
Description: This script processes a CSV file for Jira import, validating and correcting data according to specified rules.
Author: Julien (@tom4897)
License: MIT
Date: 2025
"""

import logging
import csv
import re
from tqdm import tqdm # type: ignore
from app import App
from typing import List
from contextlib import nullcontext
from console import ConsoleUI, fmt, ui


unique_key_column = 'summary'

#todo: refactor this class to use a more object-oriented approach
#todo: dataclass for the config, validation results
class CSVProcessor:
    def __init__(self, path, config) -> None:
        if config is None:
            raise ValueError("Config is required")

        # Initialize instance variables instead of class variables
        self.header: List[str] = []
        self.data: List[List[str]] = []
        self.current_row_index: int = 1
        self.complex_child_issues: List[Dict[str, Any]] = []
        self.issue_id_list: List[str] = []
        self.config = None

        self.problem_list: List[Tuple[str, Literal["error", "warning", "fix"], int]] = []

        # Load configuration and process CSV
        self.config = config
        self.load_config_values(config)
        self.path = path
        self.read()
        self.header = self.format_header()
        self.column_indices = self.extract_column_indices()
        self.data = self.format_data()

    def add_problem(self, message: str, problem_type: Literal["error", "warning", "fix"], row_index: Optional[int] = None) -> None:
        """Add a problem to the problem list with the specified type and row index."""
        if row_index is None:
            row_index = self.current_row_index
        self.problem_list.append((message, problem_type, row_index))

    def add_error(self, message: str, row_index: Optional[int] = None) -> None:
        self.add_problem(message, "error", row_index)

    def add_warning(self, message: str, row_index: Optional[int] = None) -> None:
        self.add_problem(message, "warning", row_index)

    def add_fix(self, message: str, row_index: Optional[int] = None) -> None:
        self.add_problem(message, "fix", row_index)

    def get_problem_list(self) -> List[Tuple[str, Literal["error", "warning", "fix"], int]]:
        return self.problem_list

    def get_errors(self) -> List[Tuple[str, Literal["error", "warning", "fix"], int]]:
        return [problem for problem in self.problem_list if problem[1] == "error"]

    def get_warnings(self) -> List[Tuple[str, Literal["error", "warning", "fix"], int]]:
        return [problem for problem in self.problem_list if problem[1] == "warning"]

    def get_fixes(self) -> List[Tuple[str, Literal["error", "warning", "fix"], int]]:
        return [problem for problem in self.problem_list if problem[1] == "fix"]

    def get_error_count(self) -> int:
        return len(self.get_errors())

    def get_warning_count(self) -> int:
        return len(self.get_warnings())

    def get_fix_count(self) -> int:
        return len(self.get_fixes())

    def load_config_values(self, config) -> None:
        """Load validation settings and skip flags from config."""
        # Load validation lists
        self.config_components = config.get_value('jira.validation.components', default=[])
        self.config_priorities = config.get_value('jira.validation.priorities', default=[])
        self.config_issuetypes = config.get_value('jira.validation.issue_types', default=[])
        self.config_fixversions = config.get_value('jira.validation.fix_versions', default=[])
        self.config_min_sprint_value = config.get_value('jira.validation.min_sprint_value', default=0)
        self.config_project_key = config.get_value('jira.project.key', default=0)

        # Load validation control settings
        self.skip_all_validation = config.get_value('app.validation.skip_all', default=False)
        self.skip_checks = config.get_value('app.validation.skip_checks', default={})

        # Load statuses (currently unused but available)
        self.config_statuses = config.get_value('jira.validation.statuses', default=[])

        # Set validation flags based on skip_checks
        self.skip_description_check = self.skip_checks.get('description', False)
        self.skip_fixversion_check = self.skip_checks.get('fixversion', False)
        self.skip_component_check = self.skip_checks.get('component', False)
        self.skip_child_issue_id_check = self.skip_checks.get('child_issue_id', False)
        self.skip_story_parent_link_check = self.skip_checks.get('story_for_parent_link', False)
        self.skip_sprint_check = self.skip_checks.get('sprint', False)
        self.skip_assignee_check = self.skip_checks.get('assignee', False)

    def read(self) -> None:
        """Read CSV file and extract header and data."""
        try:
            with open(self.path, mode='r', newline='', encoding='utf-8', errors='ignore') as infile:
                csv_reader = csv.reader(infile)
                try:
                    self.header = next(csv_reader)
                except StopIteration:
                    logging.error(f"The file '{self.path}' is empty.")
                    App.event_fatal()
                self.data = [row for row in csv_reader]
        except FileNotFoundError:
            logging.error(f"File '{self.path}' not found.")
            App.event_fatal()

    def format_header(self) -> List[str]:
        """Normalize header column names for processing."""
        logging.debug(f"Original header: {self.header}")
        formatted_header = [re.sub(r'\d+', '', column).strip().lower() for column in self.header]
        logging.debug(f"Formatted header: {formatted_header}")
        return formatted_header

    def format_data(self) -> List[List[str]]:
        """Process and validate CSV data rows."""
        total = len(self.data)
        if total == 0:
            return []

        formatted_rows: List[List[str]] = []

        # lookups
        expected_len = len(self.header)
        do_validate = bool(self.config_components and self.config_priorities and self.config_issuetypes)

        # Use a set for O(1) membership; let _should_skip_row decide details
        skip_keywords = {"skip", "comment", "note", "WorkItem"}

        progress_cm = ui.progress()

        with progress_cm as progress:
            task = progress.add_task("Processing data", total=total)

            for self.current_row_index, row in enumerate(self.data, start=2):
                try:
                    # 1) Skip empty rows
                    if not any(row):
                        self.add_warning(f"Row skipped due to empty row: {row}")
                        continue

                    # 2) Skip based on row type / keywords
                    if self._should_skip_row(row, skip_keywords):
                        continue

                    # 3) Validate column count
                    if len(row) != expected_len:
                        logging.error(f"Row skipped due to incorrect number of columns: {row}")
                        self.add_error(f"Row skipped due to incorrect number of columns: {row}")
                        continue

                    # 4) Optional row-level validation
                    if do_validate:
                        self.row_validator(row)

                    # 5) Keep it
                    formatted_rows.append(row)
                finally:
                    if task is not None:
                        progress.advance(task)
                        progress.refresh()

        return formatted_rows

    def _should_skip_row(self, row: List[str], skip_keywords: List[str]) -> bool:
        """Determine if a row should be skipped based on rowtype."""
        try:
            rowtype_index = self.header.index('rowtype')
            if row[rowtype_index].strip().casefold() in skip_keywords:
                logging.debug(f"Row skipped ({row[rowtype_index].strip().casefold()}): {row[2] if len(row) > 2 else 'N/A'}")
                return True
        except ValueError:
            # rowtype column not found, continue processing
            pass
        return False

    def extract_column_indices(self) -> Dict[str, Optional[int]]:
        """Extract column indices from CSV header for validation and processing.

        Returns:
            Dictionary mapping column keys to their indices, None if not found.

        Raises:
            ValueError: If required columns are missing.
        """
        # Define required and optional columns using standard column names
        required_columns = {
            'summary': 'summary',
            'priority': 'priority',
            'issuetype': 'issuetype',
            'issue_id': 'issue id',  # Keep hardcoded as it's not in field mappings
        }

        optional_columns = {
            'project_key': 'project key',  # Keep hardcoded as it's not in field mappings
            'assignee': 'assignee',
            'description': 'description',
            'parent': 'parent',
            'epic_link': 'epic link',
            'epic_name': 'epic name',
            'component': 'component',
            'fixversion': 'fixversion',
            'origest': 'origest',
            'estimate': 'estimate',
            'sprint': 'sprint',
            'rowtype': 'rowtype'  # Keep hardcoded as it's not in field mappings
        }

        logging.debug(f"Required columns: {required_columns}")
        logging.debug(f"Optional columns: {optional_columns}")

        # Check for required columns first
        missing_columns = []
        column_indices = {}

        logging.debug(f"Searching for required columns: {list(required_columns.values())}")

        for key, column_name in required_columns.items():
            try:
                column_indices[key] = self.header.index(column_name)
                logging.debug(f"Found required column '{column_name}' at index {column_indices[key]}")
            except ValueError:
                missing_columns.append(column_name)
                logging.warning(f"Required column '{column_name}' not found in header")

        if missing_columns:
            error_msg = f"Required columns missing: {', '.join(missing_columns)}. Available columns: {self.header}"
            logging.error(error_msg)
            raise ValueError(error_msg)

        # Handle optional columns
        for key, column_name in optional_columns.items():
            try:
                column_indices[key] = self.header.index(column_name)
            except ValueError:
                column_indices[key] = None
                logging.debug(f"Optional column '{column_name}' not found in header")

        # Handle special case for child-issue columns (can be multiple)
        child_issue_indices = [i for i, col in enumerate(self.header) if col == 'child-issue']
        column_indices['child_issue_indices'] = child_issue_indices

        if child_issue_indices:
            logging.debug(f"Found {len(child_issue_indices)} child-issue columns at indices: {child_issue_indices}")

        # Validate that all indices are within bounds
        self._validate_column_indices(column_indices)

        logging.info(f"Successfully extracted column indices: {list(column_indices.keys())}")
        #ui.success(f"Successfully extracted column indices: {list(column_indices.keys())}")
        return column_indices

    def _validate_column_indices(self, column_indices: Dict[str, Optional[int]]) -> None:
        """Validate that column indices are within header bounds."""
        header_length = len(self.header)
        for key, index in column_indices.items():
            # Skip validation for special cases like child_issue_indices which is a list
            if key == 'child_issue_indices':
                continue

            if index is not None and (index < 0 or index >= header_length):
                logging.warning(f"Column index for '{key}' ({index}) is out of bounds (0-{header_length-1})")

    def get_column_value(self, row: List[str], column_key: str, default: str = "") -> str:
        """Safely get column value from row using column key.

        Args:
            row: Row data to extract from
            column_key: Key for column index lookup
            default: Default value if column not found

        Returns:
            Column value or default if not found
        """
        if not hasattr(self, 'column_indices') or self.column_indices is None:
            return default

        index = self.column_indices.get(column_key)
        if index is None or index < 0 or index >= len(row):
            return default

        return row[index].strip() if row[index] else default

    def row_validator(self, row) -> List[str]:
        """Run all validation checks on a single row."""
        if self.column_indices is None:
            return row  # or handle the error as needed

        # Skip all validation if configured
        if self.skip_all_validation:
            logging.warning(f"Skipping all validation for row {self.current_row_index}.")
            return row

        # Extract indices from the dictionary
        indices = self.column_indices
        summary_index = indices['summary']
        priority_index = indices['priority']
        issuetype_index = indices['issuetype']
        component_index = indices['component']
        fixversion_index = indices['fixversion']
        sprint_index = indices['sprint']
        issue_id_index = indices['issue_id']
        project_key_index = indices['project_key']
        child_issue_id_indices = indices['child_issue_indices']
        assignee_index = indices['assignee']
        rowtype_index = indices['rowtype']
        estimate_index = indices['estimate']
        origest_index = indices['origest']
        description_index = indices['description']
        parent_index = indices['parent']
        epic_link_index = indices['epic_link']
        epic_name_index = indices['epic_name']

        # Check required fields
        self.check_summary(row, summary_index)
        self.check_issue_type(row, issuetype_index)
        self.check_priority_value(row, priority_index)

        # process estimate
        if estimate_index is not None and origest_index is not None:
            self.process_estimate(row, estimate_index, origest_index)

        # Only run checks if not skipped and indices are valid
        if not self.skip_component_check and component_index is not None:
            self.check_components(row, component_index)

        if not self.skip_description_check and description_index is not None:
            self.check_description(row, description_index)

        self.check_for_duplicate_issue_id(row, issue_id_index)
        self.issue_id_list.append(row[issue_id_index])
        self.check_issue_id(row, issue_id_index)

        if not self.skip_story_parent_link_check:
            self.check_story_for_parent_link(row, issuetype_index)

        if not self.skip_fixversion_check and fixversion_index is not None:
            self.check_fixversions(row, fixversion_index)

        if not self.skip_sprint_check and sprint_index is not None:
            self.check_sprint(row, sprint_index)

        if project_key_index is not None:
            self.check_project_key(row, project_key_index)

        if not self.skip_assignee_check:
            self.check_assignee(row, assignee_index)

        if not self.skip_child_issue_id_check:
            for child_issue_id_index in child_issue_id_indices:
                self.check_child_issue_id(row, child_issue_id_index)

        return row

    def check_assignee(self, row, assignee_index) -> None:
        """Validate assignee ID length and format."""
        if assignee_index is None:
            logging.debug(f"Skipping assignee check - column not found in header")
            return

        # Check if assignee_index is within bounds
        if assignee_index >= len(row):
            logging.debug(f"Skipping assignee check - index {assignee_index} out of bounds for row length {len(row)}")
            return

        assignee = row[assignee_index].strip() if row[assignee_index] else ""
        logging.debug(f"Checking assignee: '{assignee}' in row {self.current_row_index}")

                # Basic assignee validation - could be enhanced with config later
        if assignee:
            # Check for common assignee ID lengths (24, 43 characters)
            if len(assignee) not in [24, 43]:
                warning_msg = (
                    f"Row {self.current_row_index}: Assignee '{assignee}' length is {len(assignee)} "
                    f"(expected 24 or 43 characters)."
                )
                self.add_warning(warning_msg)
                logging.warning(warning_msg)

        #todo: Check against assignee list if available

    def check_for_duplicate_issue_id(self, row, issue_id_index) -> None:
        """Check for duplicate issue IDs across all rows."""
        issue_id = row[issue_id_index]
        if issue_id in self.issue_id_list:
            logging.debug(f"Duplicated Issue ID: {issue_id} in row {self.current_row_index}")
            self.add_error(f"Duplicated Issue ID {issue_id} in row {self.current_row_index}.")


    def check_issue_id(self, row, column_index) -> None:
        """Validate and normalize issue ID format."""
        issue_id = row[column_index]
        if isinstance(issue_id, str) and re.match(r'^-?\d+(\.\d+)?$', issue_id):
            row[column_index] = (issue_id.split('.')[0])
        elif isinstance(issue_id, float):
            row[column_index] = int(issue_id)
        else:
            self.add_error(f"Invalid Issue ID value '{issue_id}' in row {self.current_row_index}.")

    def check_child_issue_id(self, row, column_index) -> bool:
        """Validate child issue ID format and handle complex ranges."""
        issue_id = row[column_index]
        is_complex = False

        # Early return for empty/None values
        if not issue_id or not str(issue_id).strip():
            return is_complex

        # Convert to string and strip for consistent processing
        issue_id_str = str(issue_id).strip()

        # Handle '0' value - treat as empty
        if issue_id_str == '0':
            row[column_index] = ""
            return is_complex

        # Handle valid numeric values (integer or float)
        if re.match(r'^-?\d+(\.\d+)?$', issue_id_str):
            row[column_index] = issue_id_str.split('.')[0]
            return is_complex

        # Handle range format (e.g., '0-99', '1-4')
        if re.match(r'^\d+-\d+$', issue_id_str):
            start, end = issue_id_str.split('-')
            row[column_index] = ""
            self.complex_child_issues.append({
                'row_index': self.current_row_index,
                'start': start,
                'end': end
            })
            is_complex = True
            logging.warning(f"Unsupported feature: Complex Child Issue ID '{issue_id_str}' detected in row {self.current_row_index}.")
            return is_complex

        # Handle invalid values
        logging.debug(f"Invalid Child Issue ID value '{issue_id_str}' in row {self.current_row_index}.")
        self.add_error(f"Invalid Child Issue ID value '{issue_id_str}' in row {self.current_row_index}.")
        return is_complex

    def check_story_for_parent_link(self, row, issuetype_index) -> None:
        """Ensure stories have parent/epic links."""
        if row[issuetype_index].casefold() == 'story':
            # The column is often named 'parent' but sometimes named 'epic link'
            parent_link_index = None
            if 'parent' in self.header:
                parent_link_index = self.header.index('parent')
            elif 'epic link' in self.header:
                parent_link_index = self.header.index('epic link')
            else:
                warning_msg = f"Could not find a 'parent' or an 'epic link' column for Story in row {self.current_row_index}."
                self.add_warning(warning_msg)
                logging.warning(warning_msg)
                return

            # Check if parent_link_index is within bounds
            if parent_link_index is not None and parent_link_index < len(row):
                if not row[parent_link_index]:
                    warning_msg = f"Story does not have a parent Link in row {self.current_row_index}."
                    self.add_warning(warning_msg)
                    logging.warning(warning_msg)
            else:
                warning_msg = f"Parent link index {parent_link_index} out of bounds for row {self.current_row_index}."
                self.add_warning(warning_msg)
                logging.warning(warning_msg)

    def check_description(self, row, description_index) -> None:
        """Validate description field is not empty."""
        if description_index is None:
            logging.debug(f"Skipping description check - column not found in header")
            return
        if row[description_index] is None or not row[description_index].strip():
            warning_msg = f"Description value is empty {self.current_row_index}."
            self.add_warning(warning_msg)
            logging.warning(warning_msg)

    def check_summary(self, row, summary_index) -> None:
        """Validate summary length (5-255 characters)."""
        if summary_index is None:
            logging.debug(f"Skipping summary check - column not found in header")
            return
        if row[summary_index] and len(row[summary_index]) > 255:
            warning_msg = f"Summary value exceeds 255 characters in row {self.current_row_index}."
            self.add_warning(warning_msg)
            logging.warning(warning_msg)
        if not row[summary_index] or len(row[summary_index]) < 5:
            warning_msg = f"Summary value is less than 5 characters in row {self.current_row_index}."
            self.add_warning(warning_msg)
            logging.warning(warning_msg)

    def check_components(self, row, component_index) -> None:
        """Validate components against config-defined list."""
        if component_index is None:
            logging.debug(f"Skipping component check - column not found in header")
            return
        components = row[component_index].split(',') if row[component_index] else []
        components_normalized = [component.casefold() for component in self.config_components]
        for component in components:
            if component.casefold() not in components_normalized:
                error_msg = f"Invalid Component value '{component}' in row {self.current_row_index}."
                self.add_error(error_msg)
                logging.error(error_msg)

    def check_issue_type(self, row, issuetype_index) -> None:
        """Validate issue type against config-defined list."""
        if issuetype_index is None:
            logging.debug(f"Skipping issue type check - column not found in header")
            return
        issuetypes_normalized = [issuetype.casefold() for issuetype in self.config_issuetypes]
        if row[issuetype_index].casefold() not in issuetypes_normalized:
            error_msg = f"Invalid Issue Type value '{row[issuetype_index]}' in row {self.current_row_index}."
            self.add_error(error_msg)
            logging.error(error_msg)

    def check_priority_value(self, row, priority_index) -> None:
        """Validate priority value and auto-fix numeric format."""
        if priority_index is None:
            logging.debug(f"Skipping priority check - column not found in header")
            return
        priorities_normalized = [priority.casefold() for priority in self.config_priorities]
        if row[priority_index].isdigit():
            if (int(row[priority_index]) < 1) or (int(row[priority_index]) > 3):
                error_msg = f"Invalid Priority value '{row[priority_index]}' in row {self.current_row_index}."
                self.add_error(error_msg)
                logging.error(error_msg)
            else:
                if row[priority_index] in ['1', '2', '3']:
                    old_priority = row[priority_index]
                    row[priority_index] = f"0{row[priority_index]}"
                    self.add_fix(f"Priority value '{row[priority_index]}' in row {self.current_row_index} has been fixed. (Original value: {old_priority})")
        elif row[priority_index].casefold() not in priorities_normalized:
            error_msg = f"Invalid Priority value '{row[priority_index]}' in row {self.current_row_index}."
            self.add_error(error_msg)
            logging.error(error_msg)

    def process_estimate(self, row, estimate_index, origest_index) -> None:
        """Process and store computed estimate in origest field."""
        if estimate_index is None or origest_index is None:
            logging.debug(f"Skipping estimate processing - indices are None")
            return
        computed_estimate = self.compute_estimate(row, estimate_index, origest_index)
        if computed_estimate is not None and computed_estimate != "" and computed_estimate != "0":
            row[origest_index] = computed_estimate
        else:
            row[origest_index] = ""

    def compute_estimate(self, row, estimate_index, origest_index) -> str:
        """Convert time estimate string to Jira-compatible seconds.
        A week is 5 days, a day is 8 hours, an hour is 60 minutes, a minute is 60 seconds.
        Parses w (weeks), d (days), h (hours), m (minutes) format.
        Returns empty string if no valid time found.
        """
        # Get estimate value
        if estimate_index is None or origest_index is None:
            logging.debug(f"Skipping estimate computation - indices are None")
            return ""
        estimate_value = row[estimate_index]
        if estimate_value is None or not str(estimate_value).strip():
            return ""

        estimate_str = str(estimate_value).strip()

        # Parse time components: w (weeks), d (days), h (hours), m (minutes)
        # 1w = 5d, 1d = 8h, 1h = 60m, 1m = 60s
        def __get_value(unit) -> int:
            pattern = rf'(\d+)\s*{unit}'
            match = re.search(pattern, estimate_str)
            return int(match.group(1)) if match else 0

        weeks = __get_value('w')
        days = __get_value('d')
        hours = __get_value('h')
        minutes = __get_value('m')

        # Convert to seconds (equivalent to Excel formula)
        # Excel: w*144000 + d*28800 + h*3600 + m*60
        seconds = weeks * 144000 + days * 28800 + hours * 3600 + minutes * 60

        # If no time specified, return empty string
        if seconds == 0:
            return ""

        # Final conversion: multiply by 60 (because Jira uses divide all estimates by 60)
        final_estimate = seconds * 60

        return str(final_estimate)

    def check_fixversions(self, row, fixversion_index) -> None:
        """Validate fix versions against config-defined list."""
        if fixversion_index is None:
            logging.debug(f"Skipping fix version check - column not found in header")
            return
        fixversions = row[fixversion_index].split(',') if row[fixversion_index] else []
        fixversions_normalized = [fixversion.casefold() for fixversion in self.config_fixversions]
        for fixversion in fixversions:
            if fixversion.casefold() not in fixversions_normalized:
                error_msg = f"Invalid Fix Version value '{fixversion}' in row {self.current_row_index}."
                self.add_error(error_msg)
                logging.error(error_msg)

    def check_sprint(self, row, sprint_index) -> None:
        """Validate sprint number against minimum config value."""
        if sprint_index is None:
            logging.debug(f"Skipping sprint check - column not found in header")
            return
        sprint = row[sprint_index]
        if sprint is None or not sprint.strip():
            return
        try:
            sprint = int(sprint)
            if sprint < self.config_min_sprint_value:
                warning_msg = f"Sprint value '{sprint}' is less than the minimum sprint value in row {self.current_row_index}."
                self.add_warning(warning_msg)
                logging.warning(warning_msg)
        except ValueError:
            #self.add_error(f"Invalid Sprint value '{sprint}' in row {self.current_row_index}.")
            return

    def check_project_key(self, row, project_key_index) -> None:
        """Validate and auto-fix project key to config value."""
        if project_key_index is None:
            logging.debug(f"Skipping project key check - column not found in header")
            return
        project_key = row[project_key_index]
        if not isinstance(project_key, str):
            if project_key is None or not project_key.strip():
                warning_msg = f"Project Key value is empty in row {self.current_row_index}."
                self.add_warning(warning_msg)
                logging.warning(warning_msg)
                return
        if isinstance(project_key, int):
            if project_key != self.config_project_key:
                row[project_key_index] = self.config_project_key
                self.add_fix(f"Project Key value '{project_key}' in row {self.current_row_index} has been fixed.")
                return

    def problems_found(self) -> bool:
        """Check if validation found any problems."""
        return bool(self.problem_list)

    def show_report(self) -> None:
        """Display validation report using UI table and log to file."""
        if self.problems_found():
            rows = []
            if self.get_problem_list():
                for problem in self.get_problem_list():
                    # Add emoji for severity
                    severity_emoji = {"error": "❌", "warning": "⚠️", "fix": "🔧"}
                    rows.append([severity_emoji.get(problem[1], problem[1]), str(problem[2]), problem[0]])

            rows.append(["", "", ""])
            rows.append(["", "", f"⚠️ {self.get_warning_count()} ❌ {self.get_error_count()} 🔧 {self.get_fix_count()}"])
            ui.table(columns=["Severity", "Row", "Description"], rows=rows)

        # Always log to file for debugging purposes
        if self.problems_found():
            logging.info(f"Problem list: {self.get_problem_list()}")
