"""Tests for shared coder delta guard helpers."""

from __future__ import annotations

import coder_delta_guards
import config


def test_head_changed_from_baseline_is_strict_equality() -> None:
    assert coder_delta_guards.head_changed_from_baseline(baseline_head="a", current_head="b") is True
    assert coder_delta_guards.head_changed_from_baseline(baseline_head="a", current_head="a") is False


def test_forbidden_path_prefix_matching() -> None:
    forbidden = (".gitmodules", "vendor/submodule")
    assert coder_delta_guards.path_matches_forbidden(path=".gitmodules", forbidden=forbidden)
    assert coder_delta_guards.path_matches_forbidden(path="vendor/submodule/file.txt", forbidden=forbidden)
    assert not coder_delta_guards.path_matches_forbidden(path="vendor/submodule-other/file.txt", forbidden=forbidden)


def test_revert_forbidden_paths_clears_staged_and_worktree() -> None:
    calls: list[tuple[str, ...]] = []

    class _Runner:
        def run(self, argv: object, **_kwargs: object) -> object:
            key: tuple[str, ...] = tuple(argv)  # type: ignore[arg-type]
            calls.append(key)
            if key[:3] == ("git", "diff", "--name-only") and "--cached" not in key:
                return type("R", (), {"returncode": 0, "stdout": ""})()
            if key[:3] == ("git", "diff", "--name-only") and "--cached" in key:
                return type("R", (), {"returncode": 0, "stdout": f"{config.PLUGIN_JSON_PATH}\n"})()
            if key[:2] == ("git", "ls-files"):
                return type("R", (), {"returncode": 0, "stdout": ""})()
            return type("R", (), {"returncode": 0, "stdout": ""})()

    count = coder_delta_guards.revert_forbidden_paths(
        _Runner(),  # type: ignore[arg-type]
        cwd=None,
        forbidden=(config.PLUGIN_JSON_PATH,),
    )
    assert count == 1
    assert ("git", "restore", "--staged", "--", config.PLUGIN_JSON_PATH) in calls
    assert ("git", "checkout", "--", config.PLUGIN_JSON_PATH) in calls


def test_coder_forbidden_paths_include_plugin_json() -> None:
    class _Runner:
        def run(self, *_args: object, **_kwargs: object) -> object:
            return type("R", (), {"returncode": 0, "stdout": ""})()

    forbidden = coder_delta_guards.coder_forbidden_paths(_Runner())  # type: ignore[arg-type]
    assert config.PLUGIN_JSON_PATH in forbidden
    assert ".gitmodules" in forbidden
