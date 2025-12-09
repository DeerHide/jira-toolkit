"""Description: This script contains the CSV source reader returning HeaderSchema and rows.

Author:
    Julien (@tom4897)
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from ...console import ConsoleIO
from ...errors import FileReadError
from ..models import HeaderSchema

ui = ConsoleIO.getUI()


class CsvSource:
    """CSV source reader returning HeaderSchema and rows."""

    def __init__(self, path: str | Path, *, encoding: str = "utf-8", newline: str = "") -> None:
        """Initialize the CsvSource."""
        self.path = Path(path)
        self.encoding = encoding
        self.newline = newline

    def read(self) -> tuple[HeaderSchema, list[list[Any]]]:
        """Read the CSV file and return the HeaderSchema and rows."""
        if not self.path.exists():
            raise FileReadError(
                f"CSV file not found: {self.path}",
                details={"file_path": str(self.path)},
            )

        with self.path.open("r", encoding=self.encoding, newline=self.newline) as fh:
            reader = csv.reader(fh)
            header_raw: list[str] = []
            rows: list[list[Any]] = []

            # First pass to count rows for progress tracking
            all_rows = list(reader)
            total_rows = len(all_rows)

            # Add progress tracking if UI is available
            if ui and hasattr(ui, "progress"):
                with ui.progress() as progress:
                    task = progress.add_task("Reading CSV data", total=total_rows)

                    for i, row in enumerate(all_rows):
                        if i == 0:
                            header_raw = [str(c).strip() for c in row]
                        else:
                            rows.append([c for c in row])
                        progress.advance(task)
            else:
                # Fallback without progress tracking
                for i, row in enumerate(all_rows):
                    if i == 0:
                        header_raw = [str(c).strip() for c in row]
                    else:
                        rows.append([c for c in row])

        # Keep normalization conservative (trim only). Your ColumnIndices resolver handles names.
        # Handle Excel-style numbered suffixes (duplicates only) that might be present in CSV files
        import re  # pylint: disable=import-outside-toplevel

        normalized_headers = []
        seen_base_names: set[str] = set()
        for header in header_raw:
            normalized_name = header.strip()

            # Check if this looks like Excel duplicate suffix: <base><digits>
            # Only strip if the base name was already seen
            match = re.match(r"^(.*?)(\d+)$", normalized_name)
            if match:
                base = match.group(1).strip()
                if base and base in seen_base_names:
                    # This is Excel's duplicate suffix - use base name
                    normalized_name = base
                # else: legitimate digits in name (e.g., "CF 123"), preserve them

            seen_base_names.add(normalized_name)
            normalized_headers.append(normalized_name)

        schema = HeaderSchema(original=header_raw, normalized=normalized_headers)
        return schema, rows
