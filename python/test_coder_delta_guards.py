"""Tests for shared coder delta guard helpers."""

from __future__ import annotations

import coder_delta_guards
import config


def test_head_changed_from_baseline_is_strict_equality() -> None:
    assert coder_delta_guards.head_changed_from_baseline("a", "b") is True
    assert coder_delta_guards.head_changed_from_baseline("a", "a") is False


def test_forbidden_path_prefix_matching() -> None:
    forbidden = (".gitmodules", "vendor/submodule")
    assert coder_delta_guards.path_matches_forbidden(".gitmodules", forbidden)
    assert coder_delta_guards.path_matches_forbidden("vendor/submodule/file.txt", forbidden)
    assert not coder_delta_guards.path_matches_forbidden("vendor/submodule-other/file.txt", forbidden)


def test_coder_forbidden_paths_include_plugin_json() -> None:
    class _Runner:
        def run(self, *_args: object, **_kwargs: object) -> object:
            return type("R", (), {"returncode": 0, "stdout": ""})()

    forbidden = coder_delta_guards.coder_forbidden_paths(_Runner())  # type: ignore[arg-type]
    assert config.PLUGIN_JSON_PATH in forbidden
    assert ".gitmodules" in forbidden
