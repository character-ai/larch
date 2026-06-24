"""Tests for cli.py dispatcher."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import cli
import importlib


CLI_PATH = Path(__file__).with_name("cli.py")


# ---------------------------------------------------------------------------
# Unit tests (in-process)
# ---------------------------------------------------------------------------


def test_unknown_domain_exits_2() -> None:
    rc = cli.main(["no-such-domain", "verb"])
    assert rc == 2


def test_unknown_verb_exits_2() -> None:
    rc = cli.main(["ship", "no-such-verb"])
    assert rc == 2


def test_missing_verb_exits_2() -> None:
    rc = cli.main(["ship"])
    assert rc == 2


def test_help_exits_0() -> None:
    rc = cli.main(["--help"])
    assert rc == 0


def test_no_args_exits_0() -> None:
    rc = cli.main([])
    assert rc == 0


def test_dispatch_ship_pr_calls_ship_main() -> None:
    mock_main = MagicMock(return_value=0)
    with patch.dict("sys.modules", {"ship": MagicMock(main=mock_main)}):
        rc = cli.main(["ship", "pr", "--dry-run"])
    mock_main.assert_called_once_with(["--dry-run"])
    assert rc == 0


def test_dispatch_ship_pre_driver_calls_implement_dispatch() -> None:
    mock_main = MagicMock(return_value=0)
    with patch.dict("sys.modules", {"implement_dispatch": MagicMock(ship_pre_driver_main=mock_main)}):
        rc = cli.main(["ship", "pre-driver"])
    mock_main.assert_called_once_with([])
    assert rc == 0


def test_dispatch_ship_design_log_calls_design_log_main() -> None:
    mock_main = MagicMock(return_value=0)
    with patch.dict("sys.modules", {"design_log_ship": MagicMock(main=mock_main)}):
        rc = cli.main(["ship", "design-log", "--pr-number", "1"])
    mock_main.assert_called_once_with(["--pr-number", "1"])
    assert rc == 0


def test_dispatch_report_tokens_analyze() -> None:
    mock_main = MagicMock(return_value=0)
    with patch.dict("sys.modules", {"report_tokens_cli": MagicMock(main=mock_main)}):
        rc = cli.main(["report-tokens", "analyze", "--skill", "implement"])
    mock_main.assert_called_once_with(["--skill", "implement"])
    assert rc == 0


def test_dispatch_session_kill_background_processes() -> None:
    mock_main = MagicMock(return_value=0)
    with patch.dict("sys.modules", {"finalize": MagicMock(kill_background_processes_main=mock_main)}):
        rc = cli.main(["session", "kill-background-processes", "--design-tmpdir", "/tmp/claude-design-test"])
    mock_main.assert_called_once_with(["--design-tmpdir", "/tmp/claude-design-test"])
    assert rc == 0


def test_dispatch_session_resolve_implement_tmpdir() -> None:
    mock_main = MagicMock(return_value=0)
    with patch.dict("sys.modules", {"session_env": MagicMock(resolve_implement_tmpdir_main=mock_main)}):
        rc = cli.main(["session", "resolve-implement-tmpdir", "--cwd", "/tmp/repo"])
    mock_main.assert_called_once_with(["--cwd", "/tmp/repo"])
    assert rc == 0


def test_dispatch_lint_retired_scripts() -> None:
    mock_main = MagicMock(return_value=0)
    with patch.dict("sys.modules", {"migration_lint": MagicMock(main=mock_main)}):
        rc = cli.main(["lint", "retired-scripts"])
    mock_main.assert_called_once_with([])
    assert rc == 0


def test_dispatch_lint_duplicate_code() -> None:
    mock_main = MagicMock(return_value=0)
    with patch.dict("sys.modules", {"duplicate_code": MagicMock(duplicate_code_main=mock_main)}):
        rc = cli.main(["lint", "duplicate-code", "--root", "python"])
    mock_main.assert_called_once_with(["--root", "python"])
    assert rc == 0


def test_dispatch_oos_serialize() -> None:
    mock_main = MagicMock(return_value=0)
    with patch.dict("sys.modules", {"oos": MagicMock(oos_serialize_main=mock_main)}):
        rc = cli.main(["oos", "serialize", "--findings-file", "f", "--output-file", "o"])
    mock_main.assert_called_once_with(["--findings-file", "f", "--output-file", "o"])
    assert rc == 0


def test_dispatch_oos_normalize_header() -> None:
    mock_main = MagicMock(return_value=0)
    with patch.dict("sys.modules", {"oos": MagicMock(oos_normalize_header_main=mock_main)}):
        rc = cli.main(["oos", "normalize-header", "--seq", "1"])
    mock_main.assert_called_once_with(["--seq", "1"])
    assert rc == 0


def test_exit_passthrough_from_delegated_main() -> None:
    mock_main = MagicMock(return_value=42)
    with patch.dict("sys.modules", {"ship": MagicMock(main=mock_main)}):
        rc = cli.main(["ship", "pr"])
    assert rc == 42


def test_systemexit_propagates_unchanged() -> None:
    def _raise(*_: object) -> int:
        raise SystemExit(3)

    with patch.dict("sys.modules", {"ship": MagicMock(main=_raise)}):
        with pytest.raises(SystemExit) as exc_info:
            _ = cli.main(["ship", "pr"])
    assert exc_info.value.code == 3


def test_lazy_import_top_level_only_argparse_importlib_sys() -> None:
    # Verify cli.py top-level imports only lightweight dispatcher modules.
    source = CLI_PATH.read_text(encoding="utf-8")
    lines = [ln.strip() for ln in source.splitlines() if ln.startswith(("import ", "from "))]
    top_imports = [ln for ln in lines if not ln.startswith("#") and not ln.startswith("from __future__")]
    allowed = {"import argparse", "import importlib", "import os", "import sys"}
    for imp in top_imports:
        assert imp in allowed, f"Unexpected top-level import in cli.py: {imp!r}"


def test_affected_registry_targets_resolve_to_domain_modules() -> None:
    affected = {"git", "push", "pr", "merge", "gh", "ci"}
    retired = {"git_cli", "push_cli", "pr_cli", "merge_cli", "gh_cli", "ci_cli"}
    checked = 0
    for module_name, func_name in cli._REGISTRY.values():  # pyright: ignore[reportPrivateUsage]
        assert module_name not in retired
        if module_name in affected:
            module = importlib.import_module(module_name)
            assert getattr(module, func_name) is not None
            checked += 1
    assert checked == 39


def test_all_registry_targets_resolve_to_callable_mains() -> None:
    for (domain, verb), (module_name, func_name) in cli._REGISTRY.items():  # pyright: ignore[reportPrivateUsage]
        module = importlib.import_module(module_name)
        target = getattr(module, func_name, None)
        assert callable(target), f"{domain} {verb} -> {module_name}.{func_name}"


def test_design_lifecycle_registry_entries_are_machine_stdout() -> None:
    expected = cli._DESIGN_LIFECYCLE_STDOUT_KEYS  # pyright: ignore[reportPrivateUsage]
    assert expected <= set(cli._REGISTRY)  # pyright: ignore[reportPrivateUsage]
    assert expected <= cli._MACHINE_STDOUT_KEYS  # pyright: ignore[reportPrivateUsage]
    assert cli._REGISTRY[("design", "step5c")] == ("design_lifecycle", "step5c_main")  # pyright: ignore[reportPrivateUsage]
    assert ("design", "step5c") in expected


def test_design_kv_entrypoint_disables_inherited_quiet(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_QUIET_ACTIVE", "1")
    monkeypatch.setenv("LARCH_QUIET_PID", "999999")
    mock_main = MagicMock(return_value=0)
    with patch.dict("sys.modules", {"design_argv": MagicMock(parse_argv_main=mock_main)}):
        rc = cli.main(["design", "parse-argv", "--help"])
    assert rc == 0
    assert os.environ["LARCH_QUIET_DISABLE"] == "1"


def test_machine_stdout_entrypoints_disable_inherited_quiet(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_QUIET_ACTIVE", "1")
    monkeypatch.setenv("LARCH_QUIET_PID", "999999")
    cases = [
        (["dirty-tree", "checkpoint"], "dirty_tree", "checkpoint_main"),
        (["checks", "repair-loop", "--help"], "checks", "checks_repair_loop_main"),
        (["session", "resolve-implement-tmpdir", "--cwd", "/tmp/repo"], "session_env", "resolve_implement_tmpdir_main"),
        (["ship", "pre-driver"], "implement_dispatch", "ship_pre_driver_main"),
        (["ship", "route-exit"], "implement_dispatch", "ship_route_exit_main"),
        (["implement", "step-8-oos-checkpoint"], "implement_dispatch", "step8_oos_checkpoint_main"),
    ]
    for argv, module_name, func_name in cases:
        monkeypatch.delenv("LARCH_QUIET_DISABLE", raising=False)
        mock_main = MagicMock(return_value=0)
        with patch.dict("sys.modules", {module_name: MagicMock(**{func_name: mock_main})}):
            rc = cli.main(argv)
        assert rc == 0
        assert os.environ["LARCH_QUIET_DISABLE"] == "1"


def test_ship_pre_driver_pre_version_gate_emits_machine_action(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def unsupported_version(_version_info: object) -> bool:
        return False

    monkeypatch.setattr(cli, "_version_supported", unsupported_version)

    rc = cli.main(["ship", "pre-driver"])

    captured = capsys.readouterr()
    assert rc == 4
    assert captured.out == "NEXT_ACTION=stall\n"
    assert "Python ship driver requires Python 3.11 or newer" in captured.err
    assert '"outcome":"STALLED"' in captured.err


def test_review_core_entrypoint_disables_inherited_quiet(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_QUIET_ACTIVE", "1")
    monkeypatch.setenv("LARCH_QUIET_PID", "999999")
    mock_main = MagicMock(return_value=0)
    with patch.dict("sys.modules", {"review_pipeline": MagicMock(review_core_main=mock_main)}):
        rc = cli.main(["review", "core", "--help"])
    assert rc == 0
    assert os.environ["LARCH_QUIET_DISABLE"] == "1"


# ---------------------------------------------------------------------------
# Subprocess cases (integration)
# ---------------------------------------------------------------------------


def test_subprocess_help() -> None:
    result = subprocess.run(
        [sys.executable, str(CLI_PATH), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "ship pr" in result.stdout


def test_subprocess_unknown_domain_exits_2() -> None:
    result = subprocess.run(
        [sys.executable, str(CLI_PATH), "no-such-domain", "verb"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "unknown subcommand" in result.stderr


def test_subprocess_ship_pr_help() -> None:
    result = subprocess.run(
        [sys.executable, str(CLI_PATH), "ship", "pr", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    # ship's parser handles --help; just verify no Python error.
    assert "Traceback" not in result.stderr


def test_subprocess_version_guard() -> None:
    """cli.py emits an error on Python < 3.11."""
    source = CLI_PATH.read_text(encoding="utf-8")
    assert "Python 3.11 or newer" in source


def test_subprocess_lint_clean_manifest(tmp_path: Path) -> None:
    """Lint retired-scripts exits 0 on an empty manifest."""
    manifest = tmp_path / "manifest.tsv"
    _ = manifest.write_text("# empty\n", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(CLI_PATH),
            "lint",
            "retired-scripts",
            "--manifest",
            str(manifest),
            "--root",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "LINT_STATUS=ok" in result.stdout


def test_subprocess_report_tokens_analyze_no_issue(tmp_path: Path) -> None:
    """report-tokens analyze --skill implement --no-issue --no-plot runs without crashing."""
    result = subprocess.run(
        [
            sys.executable,
            str(CLI_PATH),
            "report-tokens",
            "analyze",
            "--skill",
            "implement",
            "--no-issue",
            "--no-plot",
        ],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        check=False,
    )
    # May exit non-zero (no larch-logs present), but no Python traceback.
    assert "Traceback" not in result.stderr


def test_subprocess_report_tokens_bogus_skill() -> None:
    """report-tokens analyze with bogus --skill exits non-zero."""
    result = subprocess.run(
        [
            sys.executable,
            str(CLI_PATH),
            "report-tokens",
            "analyze",
            "--skill",
            "bogus-skill-name",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0


def test_subprocess_report_tokens_bogus_plot_from() -> None:
    """--plot-from flag is suppressed (accepted but ignored); no crash."""
    result = subprocess.run(
        [
            sys.executable,
            str(CLI_PATH),
            "report-tokens",
            "analyze",
            "--skill",
            "implement",
            "--plot-from",
            "/nonexistent",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert "Traceback" not in result.stderr
