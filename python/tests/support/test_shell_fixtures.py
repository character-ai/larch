"""Focused self-tests for shared shell-subprocess fixtures."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping
from pathlib import Path

import pytest

from tests.support import shell_fixtures


def _run(tool: str, *argv: str, env: Mapping[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run([tool, *argv], env=env, text=True, capture_output=True, check=False)


@pytest.mark.parametrize("tool", ["gh", "codex", "cursor", "claude"])
def test_all_supported_tools_are_configurable_and_recorded(tmp_path: Path, tool: str) -> None:
    fake_bin = shell_fixtures.make_fake_bin_dir(tmp_path)
    fake_bin.configure(tool, shell_fixtures.FakeCommand(stdout=f"{tool} ok\\n"))  # pyright: ignore[reportArgumentType] - parametrized literals exercise the public runtime check.

    result = _run(tool, "status", env=shell_fixtures.make_subprocess_env(fake_bin))

    assert result.returncode == 0
    assert result.stdout == f"{tool} ok\\n"
    assert fake_bin.invocations() == [shell_fixtures.Invocation(tool=tool, argv=("status",))]  # pyright: ignore[reportArgumentType] - parametrized literals exercise the public runtime check.


def test_fake_commands_preserve_exact_argv_and_configured_result(tmp_path: Path) -> None:
    fake_bin = shell_fixtures.make_fake_bin_dir(tmp_path)
    fake_bin.configure(
        "gh",
        shell_fixtures.FakeCommand(stdout="café\\n", stderr="problem\\n", returncode=17),
    )
    argv = ("arg with spaces", "", "line one\\nline two", "☃")

    result = _run("gh", *argv, env=shell_fixtures.make_subprocess_env(fake_bin))

    assert result.returncode == 17
    assert result.stdout == "café\\n"
    assert result.stderr == "problem\\n"
    assert fake_bin.invocations() == [shell_fixtures.Invocation(tool="gh", argv=argv)]


def test_fake_commands_log_ordered_repeated_invocations(tmp_path: Path) -> None:
    fake_bin = shell_fixtures.make_fake_bin_dir(tmp_path)
    fake_bin.configure("gh")
    env = shell_fixtures.make_subprocess_env(fake_bin)

    _ = _run("gh", "issue", "view", env=env)
    _ = _run("gh", "pr", "view", env=env)

    assert fake_bin.invocations() == [
        shell_fixtures.Invocation(tool="gh", argv=("issue", "view")),
        shell_fixtures.Invocation(tool="gh", argv=("pr", "view")),
    ]


def test_fake_bin_dirs_keep_multiple_configured_tools_and_logs_isolated(tmp_path: Path) -> None:
    first = shell_fixtures.make_fake_bin_dir(tmp_path / "first")
    second = shell_fixtures.make_fake_bin_dir(tmp_path / "second")
    first.configure("gh")
    first.configure("codex")
    second.configure("cursor")

    first_env = shell_fixtures.make_subprocess_env(first)
    _ = _run("gh", "issue", env=first_env)
    _ = _run("codex", "review", env=first_env)
    _ = _run("cursor", "agent", env=shell_fixtures.make_subprocess_env(second))

    assert first.invocations() == [
        shell_fixtures.Invocation(tool="gh", argv=("issue",)),
        shell_fixtures.Invocation(tool="codex", argv=("review",)),
    ]
    assert second.invocations() == [shell_fixtures.Invocation(tool="cursor", argv=("agent",))]


@pytest.mark.parametrize("tool", ["gh", "codex", "cursor", "claude"])
def test_unconfigured_tools_fail_closed_before_ambient_path(tmp_path: Path, tool: str) -> None:
    ambient_bin = tmp_path / "ambient-bin"
    ambient_bin.mkdir()
    ambient_tool = ambient_bin / tool
    _ = ambient_tool.write_text("#!/usr/bin/env sh\nprintf live\\n\n", encoding="utf-8")
    ambient_tool.chmod(0o755)
    fake_bin = shell_fixtures.make_fake_bin_dir(tmp_path / "fixtures")
    env = shell_fixtures.make_subprocess_env(fake_bin, {"PATH": str(ambient_bin)})

    result = _run(tool, "version", env=env)

    assert result.returncode == 127
    assert result.stdout == ""
    assert "not configured" in result.stderr
    assert fake_bin.invocations() == [
        shell_fixtures.Invocation(tool=tool, argv=("version",))  # pyright: ignore[reportArgumentType] - parametrized literals exercise the public runtime check.
    ]


def test_subprocess_environment_is_fresh_and_does_not_mutate_parent(tmp_path: Path) -> None:
    fake_bin = shell_fixtures.make_fake_bin_dir(tmp_path)
    before = os.environ.copy()

    first = shell_fixtures.make_subprocess_env(fake_bin, {"FIXTURE_ONLY": "first"})
    second = shell_fixtures.make_subprocess_env(fake_bin, {"FIXTURE_ONLY": "second"})
    first["FIXTURE_ONLY"] = "changed"

    assert os.environ == before
    assert first["PATH"].split(os.pathsep)[0] == str(fake_bin.path)
    assert second["PATH"].split(os.pathsep)[0] == str(fake_bin.path)
    assert second["FIXTURE_ONLY"] == "second"


def test_subprocess_environment_keeps_system_commands_after_path_override(tmp_path: Path) -> None:
    fake_bin = shell_fixtures.make_fake_bin_dir(tmp_path)
    requested_path = str(tmp_path / "requested-bin")

    environment = shell_fixtures.make_subprocess_env(fake_bin, {"PATH": requested_path})

    assert environment["PATH"].split(os.pathsep)[0:2] == [str(fake_bin.path), requested_path]
    if before_path := os.environ.get("PATH"):
        assert environment["PATH"].endswith(before_path)


def test_fake_plugin_tree_is_checkout_anchored_and_uses_symlinks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    monkeypatch.chdir(unrelated)

    plugin_root = shell_fixtures.make_fake_plugin_tree(tmp_path, ["scripts/sleep-seconds.sh", "python"])

    script_link = plugin_root / "scripts" / "sleep-seconds.sh"
    python_link = plugin_root / "python"
    assert script_link.is_symlink()
    assert python_link.is_symlink()
    assert script_link.samefile(shell_fixtures.repo_root() / "scripts" / "sleep-seconds.sh")
    assert python_link.samefile(shell_fixtures.repo_root() / "python")
    assert not (plugin_root / "skills").exists()
    result = subprocess.run([str(script_link), "0"], text=True, capture_output=True, check=False)
    assert result.returncode == 0


@pytest.mark.parametrize("source", ["../outside", "/absolute/path"])
def test_fake_plugin_tree_rejects_unsafe_checkout_sources(tmp_path: Path, source: str) -> None:
    with pytest.raises(ValueError, match="checkout-relative"):
        _ = shell_fixtures.make_fake_plugin_tree(tmp_path, [source])


def test_fake_plugin_tree_rejects_missing_checkout_source(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="does not exist"):
        _ = shell_fixtures.make_fake_plugin_tree(tmp_path, ["scripts/not-present.sh"])


def test_conftest_factories_are_opt_in_and_function_scoped(
    fake_bin_dir: shell_fixtures.FakeBinDirFactory,
    fake_plugin_tree: shell_fixtures.PluginTreeFactory,
    subprocess_env: shell_fixtures.SubprocessEnvFactory,
) -> None:
    fake_bin = fake_bin_dir()
    fake_bin.configure("claude", shell_fixtures.FakeCommand(stdout="ok\\n"))
    env = subprocess_env(fake_bin, {"FIXTURE_NAME": "shell"})
    plugin_root = fake_plugin_tree(["scripts/sleep-seconds.sh"])

    result = _run("claude", "--version", env=env)

    assert result.stdout == "ok\\n"
    assert env["FIXTURE_NAME"] == "shell"
    assert (plugin_root / "scripts" / "sleep-seconds.sh").is_symlink()
