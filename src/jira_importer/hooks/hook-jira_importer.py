"""PyInstaller hook for jira_importer package."""

from PyInstaller.utils.hooks import collect_all  # type: ignore[import-untyped]

datas, binaries, hiddenimports = collect_all("jira_importer")

hiddenimports += [
    "jira_importer.import_pipeline.processor",
    "jira_importer.import_pipeline.reporting",
    "jira_importer.import_pipeline.validator",
    "jira_importer.import_pipeline.models",
    "jira_importer.import_pipeline.sinks.csv_sink",
    "jira_importer.import_pipeline.sinks.cloud_sink",
    "jira_importer.import_pipeline.sources.csv_source",
    "jira_importer.import_pipeline.sources.xlsx_source",
    "jira_importer.import_pipeline.cloud.client",
    "jira_importer.import_pipeline.cloud.auth",
    "jira_importer.import_pipeline.cloud.secrets",
    "jira_importer.import_pipeline.cloud.credential_manager",
    "jira_importer.import_pipeline.cloud.bulk",
    "jira_importer.import_pipeline.cloud.mappers",
    "jira_importer.import_pipeline.cloud.metadata",
    "jira_importer.excel.excel_io",
    "jira_importer.excel.excel_table_reader",
    "jira_importer.config.config_display",
    "jira_importer.config.config_view",
    "jira_importer.config.constants",
    "jira_importer.config.issuetypes",
    "jira_importer.config.json_config",
    "jira_importer.config.utils",
]
