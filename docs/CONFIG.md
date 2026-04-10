# Jira Importer Configuration

This guide shows simple ways to configure the importer. You can keep settings in your Excel file, or in a JSON file. Pick what’s easiest for you.

**Where templates live:** **`ImportTemplate.xlsx`** is in the repository under **`resources/templates/`** (same layout as **[GitHub Releases](https://github.com/DeerHide/jira-toolkit/releases)** bundles). **`ImportTemplate_with_config.xlsx`** (when published) and standalone executables are on **Releases** — not always in git. JSON examples are under **`resources/templates/`**.

## Two ways to configure

### Option A: Configure inside your Excel file (easiest)

- Use the `Config` sheet in your Excel file
- Start from **`ImportTemplate.xlsx`** (`resources/templates/` or **Releases**), or **`ImportTemplate_with_config.xlsx`** from **[Releases](https://github.com/DeerHide/jira-toolkit/releases)** when available (sample `Config` layout)
- Put your settings as two columns: Key | Value (first row can be headers)

Tip: You can also add helpful lookup tables (assignees, sprints, components, etc.) on the same `Config` sheet. The tool reads these automatically if present.

How to run:

```bash
jira-importer.exe your-data.xlsx -ce
```

`-ce` tells the tool to use the Excel `Config` sheet as the configuration source.

### Option B: Configure with a JSON file

- Copy `resources/templates/config_importer.json` from the repository next to your Excel file (or use the file from your release bundle)
- Fill in your Jira details (site address, API token, project key and id)

How to run:

```bash
jira-importer.exe your-data.xlsx -ci
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
      "auth": {
        "email": "your-email@company.com",
        "api_token": "YOUR_API_TOKEN"
      }
    },
    "project": {
      "key": "PROJ",
      "id": 12345
    }
  }
}
```

- Row skipping (optional) — use a **top-level** `validation` object in JSON (sibling of `app` and `jira`), as in [`resources/templates/config_importer.json`](../resources/templates/config_importer.json). Do not nest these under `app.validation`; that block is used for other options (for example `skip_checks` on individual validations).

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

### Issue Types Configuration

You can now configure issue types with their hierarchical levels:

```json
{
  "jira": {
    "issuetypes": [
      {"name": "Initiative", "level": 1},
      {"name": "Epic", "level": 2},
      {"name": "Story", "level": 3},
      {"name": "Task", "level": 3},
      {"name": "Bug", "level": 3},
      {"name": "Sub-Task", "level": 4}
    ]
  }
}
```

**Issue Type Levels:**

- **Level 1 (Initiative)**: Highest level, can be parent of 2, 3, 4
- **Level 2 (Epic)**: Can be parent of 3, 4
- **Level 3 (Story/Task/Bug)**: Can be parent of 4
- **Level 4 (Sub-Task)**: Cannot be parent, must have a parent

### Other Lists

For components, priorities, and other lists, make sure they match Jira exactly:

```json
{
  "jira": {
    "components": ["Design", "Development"],
    "priorities": ["Lowest", "Low", "Medium", "High", "Highest"]
  }
}
```

### Components source (Compass)

When your Jira Software space uses **Compass components** instead of classic Jira project components, you can set `jira.components_source` to `"compass"` for clarity. The pipeline is identical—same columns (Components, Components1, ...), same payload, same validation—so this is optional and purely informational.

**JSON:**

```json
{
  "jira": {
    "components": ["Backend Service", "Frontend App"],
    "components_source": "compass"
  }
}
```

**Excel (Key/Value on Config sheet):**

| Key | Value |
| --- | --- |
| jira.components_source | compass |

Values: `"jira"` (default) or `"compass"`. Validation still uses CfgComponents / jira.components—ensure the list contains the correct names for the catalog you are targeting.

### Custom Fields Configuration

The importer supports custom Jira fields with automatic validation based on field type. You can configure custom fields in JSON or Excel.

#### JSON Configuration

Add a `custom_fields` array to your JSON config:

```json
{
  "jira": {
    "custom_fields": [
      {
        "name": "Custom Text Field",
        "id": "customfield_10125",
        "type": "text"
      },
      {
        "name": "Story Points",
        "id": "customfield_10002",
        "type": "number"
      },
      {
        "name": "Due Date",
        "id": "customfield_10130",
        "type": "date"
      },
      {
        "name": "Priority Level",
        "id": "customfield_10140",
        "type": "select"
      },
      {
        "name": "Custom Any Field",
        "id": "customfield_10150",
        "type": "any"
      }
    ]
  }
}
```

**Field Configuration Properties:**

- **`name`** (required): The column header name in your Excel file (must match exactly, case-insensitive)
- **`id`** (required): The Jira custom field ID (format: `customfield_XXXXX`)
- **`type`** (required): Field type - one of `"text"`, `"number"`, `"date"`, `"select"`, or `"any"`

#### Excel Table Configuration

Create a table named `CfgCustomFields` in your `Config` sheet with three columns:

| Name | Id | Type |
|------|----|----|
| Custom Text Field | customfield_10125 | text |
| Story Points | customfield_10002 | number |
| Due Date | customfield_10130 | date |
| Priority Level | customfield_10140 | select |
| Custom Any Field | customfield_10150 | any |

**Excel Table Requirements:**

- Table name must be exactly `CfgCustomFields`
- Column headers: `Name`, `Id`, `Type` (case-insensitive)
- The `Name` column must match your Excel data column header exactly

#### Team mapping (JSON)

When using a JSON config file, you can define team name-to-ID mapping with `jira.teams`. This mirrors the Excel `CfgTeams` table and is used for team resolution during validation and auto-fix.

```json
{
  "jira": {
    "teams": [
      { "name": "Backend", "id": "12345" },
      { "name": "Frontend", "id": "67890" }
    ]
  }
}
```

- **`name`** (required): Human-friendly team name (e.g. used in your Excel Team column).
- **`id`** (required): Jira Cloud Team id (as used by the Advanced Roadmaps Team field).

Each entry must have both `name` and `id`. Duplicate IDs or duplicate names (case-insensitive) are not allowed. When using Excel config, use the `CfgTeams` table on the Config sheet instead.

#### Supported Field Types

| Type | Description | Validation | Example Values |
|------|-------------|------------|----------------|
| **text** | Text field | No validation (any string accepted) | "Important", "Urgent" |
| **number** | Numeric field | Must be parseable as integer or float | `5`, `8.5`, `100` |
| **date** | Date field | Must match: YYYY-MM-DD, MM/DD/YYYY, or DD/MM/YYYY | `2024-12-31`, `12/31/2024` |
| **select** | Select field | Currently accepts any value (validation against allowed values coming soon) | "High", "Medium", "Low" |
| **any** | Any field type | No validation or transformation (value passed through as-is) | Any value type |

#### Finding Custom Field IDs

To find your custom field IDs in Jira:

1. Go to your Jira project settings
2. Navigate to **Fields** or **Custom Fields**
3. Click on a custom field to view its details
4. The field ID appears in the URL or field details (format: `customfield_XXXXX`)

Alternatively, you can:

- Use the Jira REST API: `GET /rest/api/3/field` to list all fields
- Check the browser developer tools when viewing a field in Jira

#### Using Custom Fields in Excel

Once configured, add columns to your data sheet matching the custom field names:

```csv
Summary,Priority,Issue Type,Custom Text Field,Story Points,Due Date
Fix bug,High,Bug,Important,5,2024-12-31
Add feature,Medium,Story,Urgent,8,2024-11-15
```

**Important Notes:**

- Column names must match the `name` in your configuration (case-insensitive)
- Empty cells are treated as "no value" and are valid
- Date fields support multiple formats but must be consistent
- Number fields accept both integers and decimals

#### Validation Errors

The importer validates custom field values and reports errors:

- **Number fields**: Reports invalid number format errors
- **Date fields**: Reports invalid date format errors with expected formats
- **Text/Select fields**: Currently no validation (validation coming soon for select fields)

Example error message:

```text
Invalid number value for custom field 'Story Points' (id: customfield_10002): 'abc'
Row 5, Column: Story Points
```

### Backward Compatibility

The old format is still supported:

```json
{
  "jira": {
    "validation": {
      "issue_types": ["Epic", "Story", "Task", "Sub-task", "Bug"]
    }
  }
}
```

If you prefer Excel, put these in tables on the `Config` sheet. The importer will read them automatically when present.

## Security

- Never share or commit your API token
- Store configuration files in a safe place

## Troubleshooting

### Authentication Issues

The importer now provides clear, actionable error messages for authentication problems:

#### Common Authentication Errors

| **Error Message** | **What It Means** | **How to Fix** |
|-------------------|-------------------|----------------|
| `Authentication successful - connected as: [User Name]` | ✅ Everything is working correctly | No action needed |
| `Jira authentication failed (HTTP 401) - your API token may have expired` | Your API token has expired | Refresh your token at: `https://yourcompany.atlassian.net/secure/ViewProfile.jspa` |
| `Jira authentication failed (HTTP 403) - your API token may be invalid or you lack permissions` | Token is invalid or you don't have the right permissions | Check your token and ensure you have project access |
| `Jira instance not found at [URL] (HTTP 404)` | Wrong site address | Check your `site_address` in the configuration |
| `Jira API rate limit exceeded (HTTP 429)` | Too many requests to Jira | Wait a moment and try again |
| `Jira server error (HTTP 5xx)` | Jira server is having issues | Try again later or contact your Jira administrator |
| `Network connection failed to [URL]` | Internet or network problem | Check your internet connection and try again |

#### Configuration Loading Issues

If you're getting "Missing jira.connection.site_address" errors:

1. **Check your command line**: Make sure you're using the right config flag

   ```bash
   # Use specific config file
   jira-importer.exe your-data.xlsx -c path/to/config.json

   # Use Excel config sheet
   jira-importer.exe your-data.xlsx -ce

   # Use config next to Excel file
   jira-importer.exe your-data.xlsx -ci
   ```

2. **Verify your config file**: Make sure it contains the required fields:

   ```json
   {
     "jira": {
       "connection": {
         "site_address": "https://yourcompany.atlassian.net",
         "auth": {
           "email": "your-email@company.com",
           "api_token": "YOUR_API_TOKEN"
         }
       }
     }
   }
   ```

### Other Common Issues

- **Values rejected**: Make sure your lists (components, priorities, issue types) match your Jira project exactly
- **Need more details**: Run with `-d` to get debug logs in `jira_importer_logs/`
- **File not found**: Check that your Excel file and config file paths are correct

## Full examples

- Excel template with expected columns: **`ImportTemplate.xlsx`** from **`resources/templates/`** in git or **[Releases](https://github.com/DeerHide/jira-toolkit/releases)**; optional config-heavy variant when published there
- JSON template in git: **`resources/templates/config_importer.json`** (also **`config_importer_full.json`** for a fuller skeleton)

:_GeneratedFile_
