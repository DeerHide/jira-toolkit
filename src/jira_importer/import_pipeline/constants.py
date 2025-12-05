"""Constants for import pipeline processing."""

from typing import Final

# Row type values
ROW_TYPE_SKIP: Final[str] = "SKIP"

# Row indexing
HEADER_ROW_INDEX: Final[int] = 1
FIRST_DATA_ROW_INDEX: Final[int] = 2

# Configuration keys
CFG_VALIDATION_SKIP_ROWTYPE: Final[str] = "validation.skip_rowtype"
CFG_VALIDATION_SKIP_ISSUETYPES: Final[str] = "validation.skip_issuetypes"
CFG_APP_WRITE_PROCESSING_META: Final[str] = "app.write_processing_meta"
CFG_APP_WRITE_REPORT_TABLE: Final[str] = "app.write_report_table"

# Default configuration values
DEFAULT_SKIP_ROWTYPE_ENABLED: Final[bool] = True
DEFAULT_WRITE_PROCESSING_META: Final[bool] = False
DEFAULT_WRITE_REPORT_TABLE: Final[bool] = False
