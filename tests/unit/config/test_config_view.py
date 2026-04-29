"""Unit tests for ConfigView dotted-key lookup behavior."""

from __future__ import annotations

from jira_importer.config.config_view import ConfigView  # type: ignore[import-untyped]


class LegacyGetterConfig:
    """Config object with a legacy get() signature (no default arg)."""

    def __init__(self, flat: dict[str, object] | None = None, nested: dict[str, object] | None = None) -> None:
        self._flat = flat or {}
        self.a = nested or {}

    def get(self, key: str) -> object | None:
        return self._flat.get(key)


class DefaultAwareGetValueConfig:
    """Config object exposing get_value(key, default=...)."""

    def __init__(self, flat: dict[str, object] | None = None) -> None:
        self._flat = flat or {}

    def get_value(self, key: str, default: object | None = None) -> object | None:
        return self._flat.get(key, default)


def test_prefers_literal_dotted_root_key_when_both_exist() -> None:
    cfg = {"jira.custom_fields": "literal", "jira": {"custom_fields": "nested"}}
    view = ConfigView(cfg)
    assert view.get("jira.custom_fields") == "literal"


def test_returns_nested_value_when_only_nested_path_exists() -> None:
    view = ConfigView({"jira": {"custom_fields": ["a", "b"]}})
    assert view.get("jira.custom_fields") == ["a", "b"]


def test_returns_literal_dotted_value_when_only_literal_key_exists() -> None:
    view = ConfigView({"jira.custom_fields": ["x"]})
    assert view.get("jira.custom_fields") == ["x"]


def test_returns_default_for_missing_path() -> None:
    view = ConfigView({"jira": {}})
    assert view.get("jira.custom_fields", default=["fallback"]) == ["fallback"]


def test_preserves_none_and_other_falsy_values_for_existing_keys() -> None:
    view = ConfigView({"a": {"none": None, "zero": 0, "false": False, "empty": ""}})
    assert view.get("a.none", default="fallback") is None
    assert view.get("a.zero", default=1) == 0
    assert view.get("a.false", default=True) is False
    assert view.get("a.empty", default="fallback") == ""


def test_legacy_getter_none_falls_through_to_nested_lookup() -> None:
    cfg = LegacyGetterConfig(flat={}, nested={"b": "nested"})
    view = ConfigView(cfg)
    assert view.get("a.b", default="fallback") == "nested"


def test_get_value_default_aware_lookup_uses_literal_value_when_present() -> None:
    cfg = DefaultAwareGetValueConfig(flat={"jira.custom_fields": "flat"})
    view = ConfigView(cfg)
    assert view.get("jira.custom_fields", default="fallback") == "flat"
