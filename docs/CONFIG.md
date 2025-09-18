# Jira Importer Configuration

This guide shows simple ways to configure the importer. You can keep settings in your Excel file, or in a JSON file. Pick what’s easiest for you.

## Two ways to configure

### Option A: Configure inside your Excel file (easiest)

- Use the `Config` sheet in your Excel file
- Start from our template: `resources/templates/ImportTemplate_with_config.xlsx`
- Put your settings as two columns: Key | Value (first row can be headers)

Tip: You can also add helpful lookup tables (assignees, sprints, components, etc.) on the same `Config` sheet. The tool reads these automatically if present.

How to run:

```bash
jira_importer.exe your-data.xlsx -ce
```

`-ce` tells the tool to use the Excel `Config` sheet as the configuration source.

### Option B: Configure with a JSON file

- Copy `resources/templates/config_importer.json` next to your Excel file
- Fill in your Jira details (site address, API token, project key and id)

How to run:

```bash
jira_importer.exe your-data.xlsx -ci
```

`-ci` tells the tool to look for `config_importer.json` next to your Excel file.
You can also point to a specific file with `-c path/to/config.json`.

## What to put in your config

The most important settings are:

- Jira connection:

```json
{
  "jira": {
    "connection": {
      "site_address": "https://yourcompany.atlassian.net",
      "api_token": "YOUR_API_TOKEN"
    },
    "project": {
      "key": "PROJ",
      "id": 12345
    }
  }
}
```

- Row skipping (optional):

```json
{
  "validation": {
    "skip_rowtype": true,
    "skip_issuetypes": ["comment", "note", "skip"]
  }
}
```

With these settings:

- Rows with `RowType = SKIP` are ignored
- Rows with Issue Type in the list (e.g., "comment") are ignored

## Choosing the config source (flags)

- `-ce, --config-excel`: Use the Excel file itself (its `Config` sheet)
- `-ci, --config-input`: Use `config_importer.json` next to your Excel file
- `-cd, --config-default`: Use the config that ships with the app
- `-c, --config <file>`: Use a specific JSON file

If you’re not sure, use `-ce` (Excel) or place `config_importer.json` next to your Excel and use `-ci`.

## Logging (optional)

- File logging can be turned on/off with `app.logging.write_to_file` (on by default)
- Logs are saved next to the app in `jira_importer_logs/`
- To see more details, run with `-d` (debug mode)

Example logging section (JSON):

```json
{
  "app": {
    "logging": {
      "write_to_file": true,
      "log_level": "INFO",
      "max_log_size_mb": 10,
      "max_log_files": 5
    }
  }
}
```

## Tips for lists (components, priorities, issue types)

If you keep lists in JSON, make sure they match Jira exactly. Example:

```json
{
  "jira": {
    "components": ["Design", "Development"],
    "priorities": ["Lowest", "Low", "Medium", "High", "Highest"],
    "issue_types": ["Epic", "Story", "Task", "Sub-task", "Bug"]
  }
}
```

If you prefer Excel, put these in tables on the `Config` sheet. The importer will read them automatically when present.

## Security

- Never share or commit your API token
- Store configuration files in a safe place

## Troubleshooting

- Authentication errors: check your site address and API token
- Values rejected: make sure your lists (components, priorities, issue types) match your Jira project exactly
- Need more details: run with `-d` to get debug logs in `jira_importer_logs/`

## Full examples

- Excel template with a `Config` sheet: `resources/templates/ImportTemplate_with_config.xlsx`
- JSON template: `resources/templates/config_importer.json`
