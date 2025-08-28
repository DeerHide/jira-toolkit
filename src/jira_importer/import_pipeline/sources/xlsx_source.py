"""
Script Name: xlsx_source.py
Description: This script contains the XLSX source reader using ExcelWorkbookManager to return HeaderSchema and rows.
Author: Julien (@tom4897)
License: MIT
Date: 2025
"""

from __future__ import annotations

from typing import Any

from ..models import HeaderSchema
from ...excel_io import ExcelWorkbookManager


class XlsxSource:
    def __init__(self, manager: ExcelWorkbookManager, *, data_sheet: str = "Data") -> None:
        self.mgr = manager
        self.data_sheet = data_sheet

    def read(self) -> tuple[HeaderSchema, list[list[Any]]]:
        header, rows = self.mgr.read_dataset(sheet=self.data_sheet)
        schema = HeaderSchema(original=header, normalized=[c.strip() for c in header])
        return schema, rows
