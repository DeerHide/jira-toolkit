"""Description: This script contains the CSV source reader returning HeaderSchema and rows.

Author:
    ulien (@tom4897)
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from ...console import ConsoleIO
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
            raise FileNotFoundError(self.path)

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
        schema = HeaderSchema(original=header_raw, normalized=[c.strip() for c in header_raw])
        return schema, rows
