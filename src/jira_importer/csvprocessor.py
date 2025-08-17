#!/usr/bin/env python
# -*- coding: utf-8 -*-
#lint:disable=unused-variable
#agent:disable=unused-variable
#agent:disable=unreachable-code

from typing import Dict, List, Optional, Any

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
from tqdm import tqdm
from app import App

unique_key_column = 'summary'

class CSVProcessor:
    header = []
    data = []
    current_row_index = 1
    warning_list = []
    error_list = []
    fix_list = []
    complex_child_issues = []
    complex_child_issues_len = []
    issue_id_list = []


    def __init__(self, path, config):
        self.config = config
        self.load_config_values(config)
        self.path = path
        self.read()
        self.header = self.format_header()
        self.column_indices = self.extract_column_indices()
        self.data = self.format_data()

    def load_config_values(self, config):
        # Load validation lists
        self.config_components = config.get_value('jira.validation.components')
        self.config_priorities = config.get_value('jira.validation.priorities')
        self.config_issuetypes = config.get_value('jira.validation.issue_types')
        self.config_fixversions = config.get_value('jira.validation.fix_versions')
        self.config_min_sprint_value = config.get_value('jira.validation.min_sprint_value') or 0
        self.config_project_key = config.get_value('jira.project.key') or 0
        
        # Load validation control settings
        self.skip_all_validation = config.get_value('app.validation.skip_all') or False
        self.skip_checks = config.get_value('app.validation.skip_checks') or {}
        
        # Load statuses (currently unused but available)
        self.config_statuses = config.get_value('jira.validation.statuses')
        
        # Set validation flags based on skip_checks
        self.skip_description_check = self.skip_checks.get('description', False)
        self.skip_fixversion_check = self.skip_checks.get('fixversion', False)
        self.skip_component_check = self.skip_checks.get('component', False)
        self.skip_child_issue_id_check = self.skip_checks.get('child_issue_id', False)
        self.skip_story_parent_link_check = self.skip_checks.get('story_for_parent_link', False)
        self.skip_sprint_check = self.skip_checks.get('sprint', False)
        self.skip_assignee_check = self.skip_checks.get('assignee', False)

    def get_assignees_from_config(self):
        logging.debug("Loading assignees from configuration.")
        if hasattr(self, 'config') and self.config:
            assignees = self.config.get_value('jira.validation.assignees')
            if assignees:
                return assignees
        return []    

    def read(self):
        with open(self.path, mode='r', newline='', encoding='utf-8', errors='ignore') as infile:
            csv_reader = csv.reader(infile)
            try:
                self.header = next(csv_reader)
            except StopIteration:
                logging.error(f"The file '{self.path}' is empty.")
                App.event_fatal()
            self.data = [row for row in csv_reader]

    def format_header(self):
        logging.debug(f"Original header: {self.header}")
        formatted_header = [re.sub(r'\d+', '', column).strip().lower() for column in self.header]
        logging.debug(f"Formatted header: {formatted_header}")
        return formatted_header

    def format_data(self):
        formatted_rows = []
        
        # Use configurable skip keywords (could be moved to config later)
        skip_keywords = ['skip', 'comment', 'note', 'WorkItem']
        
        for self.current_row_index, row in enumerate(tqdm(self.data, desc="Processing data", unit="row"), start=2):
            if not any(row):  # Skip empty rows
                self.warning_list.append(f"Row skipped due to empty row: {row}")
                continue
            
            if row[self.header.index('rowtype')].strip().lower() in skip_keywords:  # Skip rows where the first value matches any keyword
                logging.debug(f"Row skipped ({row[self.header.index('rowtype')].strip().lower()}): {row[2]}")
                continue
            if len(row) != len(self.header):  # Skip rows with incorrect number of columns
                self.error_list.append(f"Row skipped due to incorrect number of columns: {row}")
                continue
            if self.config_components and self.config_priorities and self.config_issuetypes:
                self.row_validator(row)
                    
            formatted_rows.append(row)
            
        return formatted_rows
 
    def extract_column_indices(self) -> Dict[str, Optional[int]]:
        """
        Extract column indices from the CSV header for required and optional columns.
        
        Returns:
            Dict[str, Optional[int]]: Dictionary containing column indices with descriptive keys.
                 Returns None if required columns are missing.
        
        Raises:
            ValueError: If required columns are missing from the header.
        """
        # Define required and optional columns with fallback to config if available
        required_columns = {
            'summary': self.config.get_value('jira.field.mappings.summary.csv_field') or 'summary',
            'priority': self.config.get_value('jira.field.mappings.priority.csv_field') or 'priority', 
            'issuetype': self.config.get_value('jira.field.mappings.issuetype.csv_field') or 'issuetype',
            'component': self.config.get_value('jira.field.mappings.component.csv_field') or 'component',
            'fixversion': self.config.get_value('jira.field.mappings.fixversion.csv_field') or 'fixversion',
            'estimate': self.config.get_value('jira.field.mappings.estimate.csv_field') or 'estimate',
            'origest': self.config.get_value('jira.field.mappings.origest.csv_field') or 'origest',
            'sprint': self.config.get_value('jira.field.mappings.sprint.csv_field') or 'sprint',
            'issue_id': 'issue id',  # Keep hardcoded as it's not in field mappings
            'project_key': 'project key'  # Keep hardcoded as it's not in field mappings
        }
        
        optional_columns = {
            'assignee': self.config.get_value('jira.field.mappings.assignee.csv_field') or 'assignee',
            'rowtype': 'rowtype'  # Keep hardcoded as it's not in field mappings
        }
        
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
        return column_indices
    
    def _validate_column_indices(self, column_indices: Dict[str, Optional[int]]) -> None:
        """
        Validate that all column indices are within valid bounds.
        
        Args:
            column_indices: Dictionary of column indices to validate
        """
        header_length = len(self.header)
        for key, index in column_indices.items():
            # Skip validation for special cases like child_issue_indices which is a list
            if key == 'child_issue_indices':
                continue
                
            if index is not None and (index < 0 or index >= header_length):
                logging.warning(f"Column index for '{key}' ({index}) is out of bounds (0-{header_length-1})")
    
    def get_column_value(self, row: List[str], column_key: str, default: str = "") -> str:
        """
        Safely get a column value from a row using the column key.
        
        Args:
            row: The row data
            column_key: The key for the column index
            default: Default value if column not found or index invalid
            
        Returns:
            The column value or default
        """
        if not hasattr(self, 'column_indices') or self.column_indices is None:
            return default
            
        index = self.column_indices.get(column_key)
        if index is None or index < 0 or index >= len(row):
            return default
            
        return row[index].strip() if row[index] else default

    def row_validator(self, row):
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
        
        self.check_summary(row, summary_index)
        self.check_issue_type(row, issuetype_index)
        self.check_priority_value(row, priority_index)
        self.process_estimate(row, estimate_index, origest_index)
        
        # Only run checks if not skipped
        if not self.skip_component_check:
            self.check_components(row, component_index)
        
        if not self.skip_description_check:
            self.check_description(row)
        
        self.check_for_duplicate_issue_id(row, issue_id_index)
        self.issue_id_list.append(row[issue_id_index])
        self.check_issue_id(row, issue_id_index)
        
        if not self.skip_story_parent_link_check:
            self.check_story_for_parent_link(row, issuetype_index)
        
        if not self.skip_fixversion_check:
            self.check_fixversions(row, fixversion_index)
        
        if not self.skip_sprint_check:
            self.check_sprint(row, sprint_index)
        
        self.check_project_key(row, project_key_index)
        
        if not self.skip_assignee_check:
            self.check_assignee(row, assignee_index)
        
        if not self.skip_child_issue_id_check:
            for child_issue_id_index in child_issue_id_indices:
                self.check_child_issue_id(row, child_issue_id_index)
        
        return row
    
    def check_assignee(self, row, assignee_index):
        if assignee_index is None:
            logging.debug(f"Skipping assignee check - column not found in header")
            return
            
        assignee = row[assignee_index].strip() if assignee_index < len(row) else ""
        logging.debug(f"Checking assignee: '{assignee}' in row {self.current_row_index}")
        
        # Basic assignee validation - could be enhanced with config later
        if assignee:
            # Check for common assignee ID lengths (24, 43 characters)
            if len(assignee) not in [24, 43]:
                warning_msg = (
                    f"Row {self.current_row_index}: Assignee '{assignee}' length is {len(assignee)} "
                    f"(expected 24 or 43 characters)."
                )
                self.warning_list.append(warning_msg)
                logging.warning(warning_msg)
        
        # Check against assignee list if available (currently disabled)
        # assignees = self.get_assignees_from_config()
        # if assignee and assignees and assignee not in assignees:
        #     warning_msg = (
        #     f"Row {self.current_row_index}: Assignee '{assignee}' is not in the list of known assignees from config."
        #     )
        #     self.warning_list.append(warning_msg)
        #     logging.warning(warning_msg)

    def check_for_duplicate_issue_id(self, row, issue_id_index):
        issue_id = row[issue_id_index]
        if issue_id in self.issue_id_list:
            logging.debug(f"Duplicated Issue ID: {issue_id} in row {self.current_row_index}")
            self.error_list.append(f"Duplicated Issue ID {issue_id} in row {self.current_row_index}.")


    def check_issue_id(self, row, column_index):
        issue_id = row[column_index]
        if isinstance(issue_id, str) and re.match(r'^-?\d+(\.\d+)?$', issue_id):
            row[column_index] = (issue_id.split('.')[0])
        elif isinstance(issue_id, float):
            row[column_index] = int(issue_id)
        else:
            self.error_list.append(f"Invalid Issue ID value '{issue_id}' in row {self.current_row_index}.")

    def check_child_issue_id(self, row, column_index):
        issue_id = row[column_index]

        is_complex = False

        if issue_id is None or issue_id.strip() == '':
            return is_complex

        if isinstance(issue_id, str) and row[column_index].strip() == '0':
            # If the value is '0', we consider it as empty
            row[column_index]=""
            return is_complex
        
        if isinstance(issue_id, str) and re.match(r'^-?\d+(\.\d+)?$', issue_id):
            # Valid integer or float, convert to integer
            row[column_index] = (issue_id.split('.')[0])
        elif isinstance(issue_id, str) and re.match(r'^VN-\d+$', issue_id):
            # Valid VN-12345, VN-1, etc. 
            # Returned empty as it would need to update the issue ID in Jira which is not possible without admin rights
            row[column_index]=""
        elif isinstance(issue_id, str) and re.match(r'^\d+-\d+$', issue_id):
            # Accept values like '0-99', '1-4', etc.
            issue_ids = issue_id.split('-')
            issue_id_start = issue_ids[0]
            issue_id_end = issue_ids[1]
            row[column_index] = ""
            self.complex_child_issues.append({
                'row_index': self.current_row_index,
                'start': issue_id_start,
                'end': issue_id_end
            })
            is_complex = True
            logging.warning(f"Unsupported feature: Complex Child Issue ID '{issue_id}' detected in row {self.current_row_index}.")
        else:
            logging.debug(f"Invalid Child Issue ID value '{issue_id}' in row {self.current_row_index}.")
            self.error_list.append(f"Invalid Child Issue ID value '{issue_id}' in row {self.current_row_index}.")
        return is_complex

    def check_story_for_parent_link(self, row, issuetype_index):
        if row[issuetype_index].lower() == 'story':
            # The column is often named 'parent' but sometimes named 'epic link'
            if 'parent' in self.header:
                parent_link_index = self.header.index('parent')
            elif 'epic link' in self.header:
                parent_link_index = self.header.index('epic link')
            else:
                self.warning_list.append(f"Could not find a 'parent' or an 'epic link' column for Story in row {self.current_row_index}.")
                return
            if not row[parent_link_index]:
                self.warning_list.append(f"Story does not have a parent Link in row {self.current_row_index}.")

    def check_description(self, row):
        description_index = self.header.index('description')
        return
        if row[description_index] is None or row[description_index].strip() == '' or len(row[description_index]) < 1:
            self.warning_list.append(f"Description value is empty {self.current_row_index}.")

    def check_summary(self, row, summary_index):
        if row[summary_index] and len(row[summary_index]) > 255:
            self.warning_list.append(f"Summary value exceeds 255 characters in row {self.current_row_index}.")
        if not row[summary_index] or len(row[summary_index]) < 5:
            self.warning_list.append(f"Summary value is less than 5 characters in row {self.current_row_index}.")

    def check_components(self, row, component_index):
        components = row[component_index].split(',')
        components_lower = [component.casefold() for component in components]
        for component in components:
            if component.casefold() not in components_lower:
                self.error_list.append(f"Invalid Component value '{component}' in row {self.current_row_index}.")

    def check_issue_type(self, row, issuetype_index):
        issuetypes_lower = [issuetype.casefold() for issuetype in self.config_issuetypes]
        if row[issuetype_index].casefold() not in issuetypes_lower:
            self.error_list.append(f"Invalid Issue Type value '{row[issuetype_index]}' in row {self.current_row_index}.")

    def check_priority_value(self, row, priority_index):
        priorities_lower = [priority.casefold() for priority in self.config_priorities]
        if row[priority_index].isdigit():
            if (int(row[priority_index]) < 1) or (int(row[priority_index]) > 3):
                self.error_list.append(f"Invalid Priority value '{row[priority_index]}' in row {self.current_row_index}.")
            else:
                if row[priority_index] == '1' or row[priority_index] == '2' or row[priority_index] == '3':
                    old_priority = row[priority_index]
                    row[priority_index] = f"0{row[priority_index]}"
                    self.fix_list.append(f"Priority value '{row[priority_index]}' in row {self.current_row_index} has been fixed. (Original value: {old_priority})")
        elif row[priority_index].casefold() not in priorities_lower:
            self.error_list.append(f"Invalid Priority value '{row[priority_index]}' in row {self.current_row_index}.")

    def process_estimate(self, row, estimate_index, origest_index):
        computed_estimate = self.compute_estimate(row, estimate_index, origest_index)
        if computed_estimate is not None and computed_estimate != "" and computed_estimate != "0":
            row[origest_index] = computed_estimate
        else:
            row[origest_index] = "" 

    def compute_estimate(self, row, estimate_index, origest_index) -> str:
        """
        Compute the original estimate from the estimate field.
        - Parse estimate string for w (weeks), d (days), h (hours), m (minutes)
        - Convert to seconds, then multiply by 60 for final estimate (because Jira)
        - Ensure the origest column is empty if the estimate is empty to not trigger the feature in Jira
        """
        # Get estimate value
        estimate_value = row[estimate_index]
        if estimate_value is None or str(estimate_value).strip() == '':
            return ""
        
        estimate_str = str(estimate_value).strip()
        
        # Parse time components: w (weeks), d (days), h (hours), m (minutes)
        # 1w = 5d, 1d = 8h, 1h = 60m, 1m = 60s
        def get_value(unit):
            pattern = rf'(\d+)\s*{unit}'
            match = re.search(pattern, estimate_str)
            return int(match.group(1)) if match else 0
        
        weeks = get_value('w')
        days = get_value('d')
        hours = get_value('h')
        minutes = get_value('m')
        
        # Convert to seconds (equivalent to Excel formula)
        # Excel: w*144000 + d*28800 + h*3600 + m*60
        seconds = weeks * 144000 + days * 28800 + hours * 3600 + minutes * 60
        
        # If no time specified, return empty string
        if seconds == 0:
            return ""
        
        # Final conversion: multiply by 60 (because Jira uses divide all estimates by 60)
        final_estimate = seconds * 60
        
        return str(final_estimate)

    def check_fixversions(self, row, fixversion_index):
        fixversions = row[fixversion_index].split(',')
        fixversions_lower = [fixversion.casefold() for fixversion in fixversions]
        for fixversion in fixversions:
            if fixversion.casefold() not in fixversions_lower:
                self.error_list.append(f"Invalid Fix Version value '{fixversion}' in row {self.current_row_index}.")

    def check_sprint(self, row, sprint_index):
        sprint = row[sprint_index]
        if sprint is None or sprint.strip() == '':
            return
        try:
            sprint = int(sprint)
            if sprint < self.config_min_sprint_value:
                self.warning_list.append(f"Sprint value '{sprint}' is less than the minimum sprint value in row {self.current_row_index}.")
        except ValueError:
            #self.error_list.append(f"Invalid Sprint value '{sprint}' in row {self.current_row_index}.")
            return

    def check_project_key(self, row, project_key_index):
        project_key = row[project_key_index]
        if type(project_key) is not str:
            if project_key is None or project_key.strip() == '':
                logging.warning(f"Project Key value is empty in row {self.current_row_index}.")
                return
        if type(project_key) is int:
            if project_key != self.config_project_key:
                row[project_key_index] = self.config_project_key
                self.fix_list.append(f"Project Key value '{project_key}' in row {self.current_row_index} has been fixed.")
                return

    def has_errors_or_warnings(self):
        return bool(self.error_list or self.warning_list)

    def show_report(self):
        if self.has_errors_or_warnings():
            for warning in self.warning_list:
                logging.warning(warning)
            for error in self.error_list:
                logging.error(error)
            for fix in self.fix_list:
                logging.info(fix)

