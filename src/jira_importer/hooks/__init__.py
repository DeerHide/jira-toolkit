"""PyInstaller hooks for jira_importer package.

This module contains custom PyInstaller hooks to ensure proper
bundling of dependencies, especially for macOS compatibility.

Hooks:
- hook-requests.py: Ensures all requests submodules are included
- hook-jira_importer.py: Ensures all jira_importer modules are included

Author:
    Julien (@tom4897)
"""
