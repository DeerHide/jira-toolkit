"""Constants for configuration modules."""

# Issue type hierarchy levels
LEVEL_1_INITIATIVE = 1  # Highest level - can parent all others
LEVEL_2_EPIC = 2  # Epic level - can parent levels 3 and 4
LEVEL_3_STORY = 3  # Story/Task/Bug level - can parent level 4
LEVEL_4_SUBTASK = 4  # Sub-task level - must have parent

# Issue type names that map to specific levels
INITIATIVE_NAMES = ["initiative", "initiative item"]
EPIC_NAMES = ["epic", "feature", "theme"]
SUBTASK_NAMES = ["sub-task", "subtask", "sub-bug", "sub bug"]

# Default issue types for backward compatibility
DEFAULT_ISSUE_TYPES = [
    {"name": "Story", "level": LEVEL_3_STORY},
    {"name": "Task", "level": LEVEL_3_STORY},
    {"name": "Bug", "level": LEVEL_3_STORY},
    {"name": "Epic", "level": LEVEL_2_EPIC},
    {"name": "Sub-Task", "level": LEVEL_4_SUBTASK},
]

# Constants for readability
MAX_DISPLAY_ITEMS = 20
