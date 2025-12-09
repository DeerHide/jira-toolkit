"""Description: This script contains the custom field validation rule for the Jira Importer.

Author:
    Julien (@tom4897)
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from ...config.config_models import CustomFieldConfig
from ..models import ColumnIndices, IRowRule, Problem, ProblemSeverity, ValidationContext, ValidationResult


@dataclass(slots=True)
class CustomFieldValidationRule(IRowRule):
    """Validates custom field values against their type requirements.

    This rule validates custom field values based on their configured type:
    - Text: No validation (any string is valid)
    - Number: Must be parseable as int or float
    - Date: Must be parseable as date (string formats or datetime objects)
    - Select: No validation against allowed values (MVP limitation)
    - Any: No validation (any value is accepted)

    Severity: error
    """

    def apply(self, row: Sequence[Any], indices: ColumnIndices, ctx: ValidationContext) -> ValidationResult:
        """Apply the rule to the row.

        Args:
            row: Row data as sequence of values.
            indices: Column indices including custom_fields mapping.
            ctx: Validation context with custom field configs.

        Returns:
            ValidationResult with problems if any validation fails.
        """
        problems: list[Problem] = []

        # Early return if no custom fields in this row
        if not indices.custom_fields:
            return ValidationResult.empty()

        # Access custom field configs from context (follows existing pattern)
        custom_configs_by_id = getattr(ctx, "custom_field_configs", None)
        if not custom_configs_by_id:
            return ValidationResult.empty()

        # Validate each custom field
        for field_id, col_idx in indices.custom_fields.items():
            cfg = custom_configs_by_id.get(field_id)
            if cfg is None:
                # Config missing - handled elsewhere (e.g., during config loading)
                continue

            # Skip if column index is invalid
            if col_idx is None or col_idx < 0 or col_idx >= len(row):
                continue

            raw = row[col_idx]

            # Validate based on type
            problem = self._validate_value(raw, cfg, ctx.row_index)
            if problem:
                problems.append(problem)

        if problems:
            return ValidationResult(problems=tuple(problems))
        return ValidationResult.empty()

    def _validate_value(self, raw: Any, cfg: CustomFieldConfig, row_index: int) -> Problem | None:
        """Validate a custom field value based on its type.

        Args:
            raw: Raw value from Excel cell.
            cfg: CustomFieldConfig with type and format information.
            row_index: 1-based row index for error reporting.

        Returns:
            Problem if validation fails, None otherwise.
        """
        # Treat None and empty/whitespace-only strings as "no value" (valid)
        if raw is None:
            return None
        raw_str = str(raw).strip()
        if not raw_str:
            return None

        if cfg.type == "any":
            # Any fields accept any value without validation
            return None

        if cfg.type == "text":
            # Text fields accept any string value
            return None

        if cfg.type == "number":
            try:
                # Try int first, then float
                if "." in raw_str or "e" in raw_str.lower():
                    float(raw_str)
                else:
                    int(raw_str)
                return None
            except ValueError:
                return Problem(
                    code="customfield.number.invalid",
                    message=f"Invalid number value for custom field '{cfg.name}' (id: {cfg.id}): '{raw}'",
                    severity=ProblemSeverity.ERROR,
                    row_index=row_index,
                    col_key=cfg.name,
                )

        if cfg.type == "date":
            # 1) If raw is a datetime object (from openpyxl or similar)
            if isinstance(raw, datetime):
                return None  # Valid

            if isinstance(raw, date):
                return None  # Valid

            # 2) If raw is a number (int/float) - REJECT for MVP
            if isinstance(raw, (int, float)):
                return Problem(
                    code="customfield.date.numeric_not_supported",
                    message=(
                        f"Numeric Excel date values are not supported for custom fields yet. "
                        f"Please format cells as text or proper dates. "
                        f"Field: '{cfg.name}' (id: {cfg.id}), value: {raw}"
                    ),
                    severity=ProblemSeverity.ERROR,
                    row_index=row_index,
                    col_key=cfg.name,
                )

            # 3) If raw is a string - apply string-based parsing
            if isinstance(raw, str):
                raw_str = raw.strip()
                default_formats = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"]
                for fmt in default_formats:
                    try:
                        datetime.strptime(raw_str, fmt)
                        return None  # Valid
                    except ValueError:
                        continue

                # All formats failed
                return Problem(
                    code="customfield.date.invalid",
                    message=(
                        f"Invalid date value for custom field '{cfg.name}' (id: {cfg.id}): '{raw}'. "
                        f"Expected format: YYYY-MM-DD, MM/DD/YYYY, or DD/MM/YYYY"
                    ),
                    severity=ProblemSeverity.ERROR,
                    row_index=row_index,
                    col_key=cfg.name,
                )

            # 4) Any other type - unsupported
            return Problem(
                code="customfield.date.unsupported_type",
                message=(
                    f"Unsupported value type for date custom field '{cfg.name}' (id: {cfg.id}): "
                    f"{type(raw).__name__}. Expected: datetime, date, or string."
                ),
                severity=ProblemSeverity.ERROR,
                row_index=row_index,
                col_key=cfg.name,
            )

        if cfg.type == "select":
            # MVP: No validation against Jira allowedValues
            # Just accept any non-empty string
            return None

        # Unsupported field type (shouldn't happen if config is valid)
        return Problem(
            code="customfield.type.unsupported",
            message=f"Unsupported custom field type '{cfg.type}' for field '{cfg.name}' (id: {cfg.id})",
            severity=ProblemSeverity.ERROR,
            row_index=row_index,
            col_key=cfg.name,
        )
