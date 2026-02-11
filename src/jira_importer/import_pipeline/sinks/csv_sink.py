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
from ..utils import split_multi_value_cell
from .sink_utils import times60_estimates_inplace

logger = logging.getLogger(__name__)

ui = ConsoleIO.get_ui()


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

    # Prepare rows for output (may be transformed if label columns are merged)
    rows = result.rows

    # Normalize labels into a single 'Labels' column if label indices are available
    if result.indices and (result.indices.label_columns or result.indices.labels is not None):
        label_indices = sorted(set(result.indices.label_columns or []))
        if result.indices.labels is not None and result.indices.labels not in label_indices:
            label_indices.append(result.indices.labels)
        label_indices = sorted(i for i in label_indices if 0 <= i < len(header))

        if label_indices:
            first_label_idx = label_indices[0]

            # Build new header with a single Labels column
            header_out: list[str] = []
            for idx, name in enumerate(header):
                if idx == first_label_idx:
                    header_out.append("Labels")
                elif idx in label_indices[1:]:
                    continue
                else:
                    header_out.append(name)

            # Build new rows with merged labels
            rows_out: list[list[object]] = []
            secondary_label_indices = set(label_indices[1:])

            for row in rows:
                labels_for_row: list[str] = []
                seen_labels: set[str] = set()

                # Collect labels from all label-related columns
                for li in label_indices:
                    if li >= len(row):
                        continue
                    cell = row[li]
                    if cell is None:
                        continue
                    parts = split_multi_value_cell(cell)
                    if not parts:
                        continue
                    for part in parts:
                        if part not in seen_labels:
                            seen_labels.add(part)
                            labels_for_row.append(part)

                merged_labels = " ".join(labels_for_row)

                # Build the transformed row
                new_row: list[object] = []
                for idx, value in enumerate(row):
                    if idx == first_label_idx:
                        new_row.append(merged_labels)
                    elif idx in secondary_label_indices:
                        continue
                    else:
                        new_row.append(value)

                rows_out.append(new_row)

            header = header_out
            rows = rows_out

    with out_path.open("w", encoding=encoding, newline=newline) as fh:
        w = csv.writer(fh)
        w.writerow(header)

        # Add progress tracking if UI is available
        if ui and hasattr(ui, "progress"):
            with ui.progress() as progress:
                task = progress.add_task("Writing CSV", total=len(result.rows))
                for row in rows:
                    w.writerow(row)
                    progress.advance(task)
        else:
            # Fallback without progress tracking
            for row in rows:
                w.writerow(row)

    return out_path
