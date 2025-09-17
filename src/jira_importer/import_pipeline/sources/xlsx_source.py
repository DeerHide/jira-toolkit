"""Description: This script contains the XLSX source reader using ExcelWorkbookManager to return HeaderSchema and rows.

Author:
    Julien (@tom4897)
"""

from __future__ import annotations

from typing import Any

from ...excel_io import ExcelWorkbookManager
from ..models import HeaderSchema


class XlsxSource:
    """XLSX source reader returning HeaderSchema and rows."""

    def __init__(self, manager: ExcelWorkbookManager, *, data_sheet: str = "Data") -> None:
        """Initialize the XlsxSource."""
        self.mgr = manager
        self.data_sheet = data_sheet

    def read(self) -> tuple[HeaderSchema, list[list[Any]]]:
        """Read the XLSX file and return the HeaderSchema and rows."""
        header, rows = self.mgr.read_dataset(sheet=self.data_sheet)
        schema = HeaderSchema(original=header, normalized=[c.strip() for c in header])
        return schema, rows
