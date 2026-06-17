"""Tests for shared coder delta guard helpers."""

from __future__ import annotations

import coder_delta_guards


def test_head_changed_from_baseline_is_strict_equality() -> None:
    assert coder_delta_guards.head_changed_from_baseline("a", "b") is True
    assert coder_delta_guards.head_changed_from_baseline("a", "a") is False


def test_forbidden_path_prefix_matching() -> None:
    forbidden = (".gitmodules", "vendor/submodule")
    assert coder_delta_guards.path_matches_forbidden(".gitmodules", forbidden)
    assert coder_delta_guards.path_matches_forbidden("vendor/submodule/file.txt", forbidden)
    assert not coder_delta_guards.path_matches_forbidden("vendor/submodule-other/file.txt", forbidden)
