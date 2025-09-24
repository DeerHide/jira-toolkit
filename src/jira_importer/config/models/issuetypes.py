"""Dataclass models for issue type configuration with backward compatibility."""

from dataclasses import dataclass, field

from ..constants import (
    DEFAULT_ISSUE_TYPES,
    EPIC_NAMES,
    INITIATIVE_NAMES,
    LEVEL_1_INITIATIVE,
    LEVEL_2_EPIC,
    LEVEL_3_STORY,
    LEVEL_4_SUBTASK,
    SUBTASK_NAMES,
)


@dataclass
class IssueType:
    """Individual issue type definition."""

    name: str
    level: int

    def __post_init__(self):
        """Normalize and validate the issue type."""
        # Normalize name
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("Issue type name cannot be empty")

        # Validate level
        if not LEVEL_1_INITIATIVE <= self.level <= LEVEL_4_SUBTASK:
            raise ValueError(
                f"Issue type level must be between {LEVEL_1_INITIATIVE} and {LEVEL_4_SUBTASK}, got {self.level}"
            )


@dataclass
class IssueTypesConfig:
    """Configuration for issue types and their hierarchy."""

    issuetypes: list[IssueType] = field(default_factory=list)

    def __post_init__(self):
        """Build lookup indexes from the issue types list."""
        # Check for duplicate names (case-insensitive)
        names_lower = [it.name.lower() for it in self.issuetypes]
        if len(names_lower) != len(set(names_lower)):
            raise ValueError("Duplicate issue type names are not allowed")

        # Build lookup maps
        self.name_to_level = {it.name.lower(): it.level for it in self.issuetypes}
        self.level_to_names = {}
        self.allowed_names = set()

        for it in self.issuetypes:
            self.level_to_names.setdefault(it.level, []).append(it.name)
            self.allowed_names.add(it.name)

        # Ensure at least one level 3 type exists (required for fallback)
        if not self.level_to_names.get(LEVEL_3_STORY):
            raise ValueError(f"At least one level {LEVEL_3_STORY} issue type must be defined")

    def level_of(self, name: str) -> int | None:
        """Get the level for an issue type name (case-insensitive)."""
        return self.name_to_level.get(str(name).strip().lower())

    def default_level3(self) -> str:
        """Get the first configured level 3 issue type (for fallback conversions)."""
        return self.level_to_names[LEVEL_3_STORY][0]

    def can_parent(self, parent_name: str, child_name: str) -> bool:
        """Check if parent_name can be a parent of child_name based on levels."""
        parent_level = self.level_of(parent_name)
        child_level = self.level_of(child_name)

        if parent_level is None or child_level is None:
            return False

        return parent_level < child_level

    def must_have_parent(self, name: str) -> bool:
        """Check if an issue type must have a parent (level 4)."""
        return self.level_of(name) == LEVEL_4_SUBTASK

    @classmethod
    def from_config(cls, config_get) -> "IssueTypesConfig":
        """Create IssueTypesConfig from config with backward compatibility.

        Supports both formats:
        - New: jira.issuetypes = [{"name": "Story", "level": 3}, ...]
        - Old: jira.validation.issue_types = ["Story", "Task", ...]
        """
        # Try new format first
        issuetypes_data = config_get("jira.issuetypes", None)

        if isinstance(issuetypes_data, list) and all(isinstance(it, dict) for it in issuetypes_data):
            # Parse the configured issue types
            issuetypes = []
            for it_data in issuetypes_data:
                if "name" in it_data and "level" in it_data:
                    issuetypes.append(IssueType(name=str(it_data["name"]), level=int(it_data["level"])))

            if issuetypes:
                return cls(issuetypes=issuetypes)

        # Fallback to old format
        old_issue_types = config_get("jira.validation.issue_types", None)
        if isinstance(old_issue_types, list):
            # Convert old flat list to new format with default levels
            issuetypes = []
            for name in old_issue_types:
                if isinstance(name, str) and name.strip():
                    # Map common names to appropriate levels
                    level = _get_default_level_for_name(name.strip())
                    issuetypes.append(IssueType(name=name.strip(), level=level))

            if issuetypes:
                return cls(issuetypes=issuetypes)

        # Final fallback to hardcoded defaults
        default_issuetypes = []
        for it in DEFAULT_ISSUE_TYPES:
            name = str(it["name"])
            level_value = it["level"]
            level = int(level_value) if isinstance(level_value, (int, str)) else LEVEL_3_STORY
            default_issuetypes.append(IssueType(name=name, level=level))
        return cls(issuetypes=default_issuetypes)


def _get_default_level_for_name(name: str) -> int:
    """Get default level for common issue type names."""
    name_lower = name.lower()

    # Level 1 (highest)
    if name_lower in INITIATIVE_NAMES:
        return LEVEL_1_INITIATIVE

    # Level 2 (epic level)
    if name_lower in EPIC_NAMES:
        return LEVEL_2_EPIC

    # Level 4 (sub-task level)
    if name_lower in SUBTASK_NAMES:
        return LEVEL_4_SUBTASK

    # Level 3 (default for story, task, bug, etc.)
    return LEVEL_3_STORY
