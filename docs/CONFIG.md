# Jira Importer Configuration Documentation

## Overview

The Jira Importer uses a JSON configuration file to define application behavior, Jira connection settings, and validation rules. This configuration file allows you to customize the import process without modifying the source code.

## Configuration File Structure

The configuration file is organized into several main sections:

- **app**: Application behavior and import settings
- **jira**: Jira connection and project-specific settings
- **metadata**: Configuration file information
- **documentation**: Usage notes and field descriptions

## Configuration Sections

### App Section

Controls the overall application behavior during import operations.

#### Sheet Configuration
```json
"sheet_name": "dataset"
```
- **Description**: Specifies the Excel worksheet name containing the data to import
- **Default**: "dataset"
- **Required**: Yes

#### Artifacts Settings
```json
"artifacts": {
  "delete_enabled": false
}
```
- **delete_enabled**: When `true`, allows deletion of existing artifacts before import
- **Default**: false
- **Warning**: Use with caution as this will permanently delete existing data

#### Import Settings
```json
"import": {
  "auto_open_page": false
}
```
- **auto_open_page**: When `true`, automatically opens the Jira page after successful import
- **Default**: false

#### Validation Settings
```json
"validation": {
  "skip_all": false,
  "skip_checks": {
    "description": false,
    "fixversion": false,
    "component": false,
    "child_issue_id": false,
    "story_for_parent_link": false,
    "sprint": false,
    "assignee": false
  }
}
```

**Global Validation Control:**
- **skip_all**: When `true`, bypasses all validation checks
- **Default**: false

**Individual Validation Checks:**
- **description**: Validate issue descriptions
- **fixversion**: Validate fix version values
- **component**: Validate component names
- **child_issue_id**: Validate child issue relationships
- **story_for_parent_link**: Validate story-parent link relationships
- **sprint**: Validate sprint assignments
- **assignee**: Validate assignee usernames

#### Reporting Settings
```json
"reporting": {
  "skip_report": false
}
```
- **skip_report**: When `true`, skips generation of import reports
- **Default**: false

#### Logging Settings
```json
"logging": {
  "write_to_file": false
}
```
- **write_to_file**: When `true`, writes detailed logs to a file
- **Default**: false

### Jira Section

Contains Jira-specific connection and project settings.

#### Connection Settings
```json
"connection": {
  "site_address": "https://xyz.atlassian.net",
  "api_token": ""
}
```
- **site_address**: Your Jira instance URL (e.g., https://yourcompany.atlassian.net)
- **Required**: Yes
- **api_token**: Your Jira API token for authentication
- **Required**: Yes
- **Security Note**: Store this securely and never commit to version control

#### Project Settings
```json
"project": {
  "key": "JITTP2",
  "id": 0
}
```
- **key**: Your Jira project key (e.g., "PROJ", "TEST")
- **Required**: Yes
- **id**: Your Jira project ID (numeric)
- **Required**: Yes
- **Note**: The ID can be found in your Jira project settings

#### Validation Rules

Defines valid values for various Jira fields to ensure data integrity during import.

**Components:**
```json
"components": [
  "design",
  "development",
  "production",
  "quality assurance",
  "quality control",
  "devops",
  "sysops"
]
```
- **Description**: List of valid component names in your Jira project
- **Required**: Yes
- **Note**: Only components listed here will be accepted during import

**Priorities:**
```json
"priorities": [
  "medium",
  "higest",
  "hight",
  "low",
  "lowest"
]
```
- **Description**: List of valid priority levels
- **Required**: Yes
- **Note**: Check your Jira project's priority scheme for exact values

**Issue Types:**
```json
"issue_types": [
  "epic",
  "story",
  "task",
  "sub-task",
  "bug"
]
```
- **Description**: List of valid issue types in your project
- **Required**: Yes
- **Note**: These must match exactly with your Jira project's issue types

**Statuses:**
```json
"statuses": [
  "Backlog",
  "In Progress",
  "Done",
  "To Do"
]
```
- **Description**: List of valid workflow statuses
- **Required**: Yes
- **Note**: These must match your Jira workflow status names exactly

**Fix Versions:**
```json
"fix_versions": [
  "JITTP Version 1",
  "JITTP Version 2"
]
```
- **Description**: List of valid release versions
- **Required**: Yes
- **Note**: These must match existing versions in your Jira project

**Sprint Settings:**
```json
"min_sprint_value": 1
```
- **Description**: Minimum valid sprint number
- **Default**: 1
- **Required**: Yes

### Metadata Section

Contains information about the configuration file itself.

```json
"metadata": {
  "version": 5,
  "description": "Jira Importer Configuration",
  "last_updated": "2025-08-15"
}
```
- **version**: Configuration file version number
- **description**: Brief description of the configuration
- **last_updated**: Date when the configuration was last modified

## Usage Instructions

### Creating a Configuration File

1. Copy the template file `rsc/templates/config_importer.json` to your project directory
2. Update the required fields:
   - `jira.connection.site_address`
   - `jira.connection.api_token`
   - `jira.project.key`
   - `jira.project.id`

### Running with the default configuration

Use the `-ci` flag to use the config_importer.json that is in the same folder as the excel file

```bash
jira-importer.exe data.xlsx -ci config.json
```

### Running with Custom Configuration

Use the `-c` flag to specify a custom configuration file:

```bash
jira-importer.exe data.xlsx -c config.json
```

### Debug Mode

Run the importer in debug mode for detailed logging:

```bash
jira-importer.exe data.xlsx -c config.json -d
```

## Security Considerations

1. **API Token**: Never commit your API token to version control
2. **Configuration Files**: Consider using environment variables for sensitive data
3. **File Permissions**: Ensure configuration files have appropriate read permissions

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Verify your API token and site address
2. **Validation Failures**: Check that your validation lists match your Jira project settings
3. **Import Failures**: Enable debug mode (`-d` flag) for detailed error information

### Validation Best Practices

1. **Test with Small Datasets**: Start with a few records to verify configuration
2. **Check Field Values**: Ensure all validation lists match your Jira project exactly
3. **Review Logs**: Enable file logging for detailed import analysis

## Example Configuration

See `rsc/templates/config_importer.json` for a complete example configuration file with all available options and their default values.
