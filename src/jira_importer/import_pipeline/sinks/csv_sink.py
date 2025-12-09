"""description: CSV sink: write Jira-ready CSV output.

author:
    Julien (@tom4897)
"""

from __future__ import annotations

# NOTE, Jira CLoud: Some Jira Cloud users are affected by the historical "divide by 60" behavior. The fix (*60) will be implemented in this sink.
#   if config.get("jira.cloud.estimate.multiply_by_60", False):
#       row[estimate_index] = str(int(row[estimate_index]) * 60)
import csv
import logging
from pathlib import Path

from ...config.config_view import ConfigView
from ...console import ConsoleIO
from ..models import ProcessorResult
from .sink_utils import times60_estimates_inplace

logger = logging.getLogger(__name__)

ui = ConsoleIO.getUI()


def write_csv(
    result: ProcessorResult,
    out_path: str | Path,
    config: object | None = None,
    *,
    encoding: str = "utf-8",
    newline: str = "",
) -> Path:
    """Write the processed rows as a CSV with the given header.

    Notes:
      - Estimates are written in canonical SECONDS as produced by the pipeline.
      - If your target (e.g., Jira Cloud CSV import) needs the historical 'x60' quirk,
        make it config-driven here (NOT in rules/fixes):

            if cfg.get("jira.cloud.estimate.multiply_by_60", False):
                times60_estimates_inplace(result)

    """
    out_path = Path(out_path)
    # out_path.parent.mkdir(parents=True, exist_ok=True)

    cfg = ConfigView(config) if config is not None else None

    # Optional: apply Jira Cloud quirk here, not in rules/fixes.
    if cfg and cfg.get("jira.cloud.estimate.multiply_by_60", False):
        times60_estimates_inplace(result)

    # Transform header: replace custom field names with field IDs for Jira CSV import
    header = list(result.header)  # Create mutable copy
    if result.indices and result.indices.custom_fields:
        # Build mapping from column_index -> field_id
        column_to_field_id: dict[int, str] = {
            col_idx: field_id for field_id, col_idx in result.indices.custom_fields.items()
        }
        # Replace header names with field IDs for custom fields
        for col_idx, field_id in column_to_field_id.items():
            if 0 <= col_idx < len(header):
                header[col_idx] = field_id

    with out_path.open("w", encoding=encoding, newline=newline) as fh:
        w = csv.writer(fh)
        w.writerow(header)

        # Add progress tracking if UI is available
        if ui and hasattr(ui, "progress"):
            with ui.progress() as progress:
                task = progress.add_task("Writing CSV", total=len(result.rows))
                for row in result.rows:
                    w.writerow(row)
                    progress.advance(task)
        else:
            # Fallback without progress tracking
            for row in result.rows:
                w.writerow(row)

    return out_path
