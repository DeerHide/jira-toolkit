"""Helper functions for working with issue type configuration using unified config_get pattern."""

from .models.issuetypes import IssueTypesConfig


def get_issuetypes_config(config_get) -> IssueTypesConfig:
    """Get issue types configuration from config using the existing access pattern.

    Args:
        config_get: Config accessor function (e.g., ctx.config.get or config.get_value)

    Returns:
        IssueTypesConfig instance with parsed issue types
    """
    return IssueTypesConfig.from_config(config_get)


def get_issue_type_level(config_get, name: str) -> int | None:
    """Get the level for an issue type name from config.

    Args:
        config_get: Config accessor function
        name: Issue type name to look up

    Returns:
        Level (1-4) if found, None otherwise
    """
    issuetypes_config = get_issuetypes_config(config_get)
    return issuetypes_config.level_of(name)


def get_allowed_issue_types(config_get) -> set[str]:
    """Get the set of allowed issue type names from config.

    Args:
        config_get: Config accessor function

    Returns:
        Set of allowed issue type names
    """
    issuetypes_config = get_issuetypes_config(config_get)
    return issuetypes_config.allowed_names


def get_default_level3_type(config_get) -> str:
    """Get the default level 3 issue type for fallback conversions.

    Args:
        config_get: Config accessor function

    Returns:
        Name of the first configured level 3 issue type
    """
    issuetypes_config = get_issuetypes_config(config_get)
    return issuetypes_config.default_level3()


def can_issue_type_parent(config_get, parent_name: str, child_name: str) -> bool:
    """Check if one issue type can be a parent of another based on levels.

    Args:
        config_get: Config accessor function
        parent_name: Potential parent issue type name
        child_name: Potential child issue type name

    Returns:
        True if parent_name can be a parent of child_name
    """
    issuetypes_config = get_issuetypes_config(config_get)
    return issuetypes_config.can_parent(parent_name, child_name)


def must_have_parent(config_get, name: str) -> bool:
    """Check if an issue type must have a parent (level 4).

    Args:
        config_get: Config accessor function
        name: Issue type name to check

    Returns:
        True if the issue type must have a parent
    """
    issuetypes_config = get_issuetypes_config(config_get)
    return issuetypes_config.must_have_parent(name)
