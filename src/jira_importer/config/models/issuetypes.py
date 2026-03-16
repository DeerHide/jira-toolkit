"""Dataclass models for issue type configuration with backward compatibility."""

from dataclasses import dataclass, field

from ...errors import ValidationError
from ..constants import (
    DEFAULT_ISSUE_TYPES,
    LEVEL_1_INITIATIVE,
    LEVEL_2_EPIC,
    LEVEL_3_STORY,
    LEVEL_4_SUBTASK,
)
from ..utils import get_default_level_for_name


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
            raise ValidationError(
                "Issue type name cannot be empty",
                details={"field": "name", "value": self.name},
            )

        # Validate level
        if not LEVEL_1_INITIATIVE <= self.level <= LEVEL_4_SUBTASK:
            raise ValidationError(
                f"Issue type level must be between {LEVEL_1_INITIATIVE} and {LEVEL_4_SUBTASK}, got {self.level}",
                details={"field": "level", "value": self.level, "min": LEVEL_1_INITIATIVE, "max": LEVEL_4_SUBTASK},
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
            raise ValidationError(
                "Duplicate issue type names are not allowed",
                details={"issuetypes": [it.name for it in self.issuetypes]},
            )

        # Build lookup maps
        self.name_to_level = {it.name.lower(): it.level for it in self.issuetypes}
        self.level_to_names = {}
        self.allowed_names = set()

        for it in self.issuetypes:
            self.level_to_names.setdefault(it.level, []).append(it.name)
            self.allowed_names.add(it.name)

        # Ensure at least one level 3 type exists (required for fallback)
        if not self.level_to_names.get(LEVEL_3_STORY):
            raise ValidationError(
                f"At least one level {LEVEL_3_STORY} issue type must be defined",
                details={"required_level": LEVEL_3_STORY, "available_levels": list(self.level_to_names.keys())},
            )

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
        """Create IssueTypesConfig from config with unified structure support.

        Supports multiple formats in order of preference:
        - Primary: jira.issuetypes = [{"name": "Story", "level": 3}, ...]
        - Legacy: jira.validation.issue_types = ["Story", "Task", ...]
        """
        # Try jira-specific format (primary)
        issuetypes_data = config_get("jira.issuetypes", None)

        if isinstance(issuetypes_data, list) and all(isinstance(it, dict) for it in issuetypes_data):
            # Parse the configured issue types
            issuetypes = []
            for it_data in issuetypes_data:
                if "name" in it_data and "level" in it_data:
                    issuetypes.append(IssueType(name=str(it_data["name"]), level=int(it_data["level"])))

            if issuetypes:
                return cls(issuetypes=issuetypes)

        # Fallback to legacy format
        old_issue_types = config_get("jira.validation.issue_types", None)
        if isinstance(old_issue_types, list):
            # Convert old flat list to new format with default levels
            issuetypes = []
            for name in old_issue_types:
                if isinstance(name, str) and name.strip():
                    # Map common names to appropriate levels
                    level = get_default_level_for_name(name.strip())
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
