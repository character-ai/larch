"""Tests for cli.py dispatcher."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from larch import cli
import importlib
import importlib.util


CLI_PATH = Path(__file__).resolve().parents[1] / "cli.py"


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
    with patch.dict("sys.modules", {"larch.implement.ship": MagicMock(main=mock_main)}):
        rc = cli.main(["ship", "pr", "--dry-run"])
    mock_main.assert_called_once_with(["--dry-run"])
    assert rc == 0


def test_dispatch_ship_pre_driver_calls_implement_dispatch() -> None:
    mock_main = MagicMock(return_value=0)
    with patch.dict("sys.modules", {"larch.implement.implement_dispatch": MagicMock(ship_pre_driver_main=mock_main)}):
        rc = cli.main(["ship", "pre-driver"])
    mock_main.assert_called_once_with([])
    assert rc == 0


def test_dispatch_ship_pre_fix_rebase_calls_implement_dispatch() -> None:
    mock_main = MagicMock(return_value=0)
    with patch.dict("sys.modules", {"larch.implement.implement_dispatch": MagicMock(ship_pre_fix_rebase_main=mock_main)}):
        rc = cli.main(["ship", "pre-fix-rebase", "--implement-tmpdir", "/tmp/x"])
    mock_main.assert_called_once_with(["--implement-tmpdir", "/tmp/x"])
    assert rc == 0


@pytest.mark.parametrize(
    "argv",
    [
        ["ship", "design-log"],
        ["ship", "design-log-sweep"],
        ["gc-run-logs", "run"],
        ["run-log", "commit"],
    ],
)
def test_git_backed_run_log_commands_are_retired(argv: list[str]) -> None:
    assert cli.main(argv) == 2


def test_retired_gc_run_logs_module_is_not_importable() -> None:
    assert importlib.util.find_spec("larch.report.gc_run_logs") is None


def test_dispatch_report_tokens_analyze() -> None:
    mock_main = MagicMock(return_value=0)
    with patch.dict("sys.modules", {"larch.report.report_tokens_cli": MagicMock(main=mock_main)}):
        rc = cli.main(["report-tokens", "analyze", "--skill", "implement"])
    mock_main.assert_called_once_with(["--skill", "implement"])
    assert rc == 0


def test_architectural_assessment_sanitizer_dispatches_as_machine_stdout() -> None:
    mock_main = MagicMock(return_value=0)
    module = MagicMock(sanitize_detail_main=mock_main)
    with patch.dict("sys.modules", {"larch.implement.architectural_assessment": module}):
        rc = cli.main(["architectural-assessment", "sanitize-detail", "--implement-tmpdir", "/tmp/x"])

    assert rc == 0
    mock_main.assert_called_once_with(["--implement-tmpdir", "/tmp/x"])
    assert ("architectural-assessment", "sanitize-detail") in cli._MACHINE_STDOUT_KEYS  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize(
    "extra_args",
    [[], ["--implement-tmpdir", "/path/that/does/not/exist"]],
    ids=["missing-argument", "invalid-tmpdir"],
)
def test_architectural_assessment_sanitizer_fails_without_echoing_stdin(extra_args: list[str]) -> None:
    token = "ghp_" + "x" * 30

    completed = subprocess.run(
        [sys.executable, str(CLI_PATH), "architectural-assessment", "sanitize-detail", *extra_args],
        input=token,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 2
    assert token not in completed.stdout
    assert token not in completed.stderr


def test_run_log_validate_run_id_entrypoint_is_retired() -> None:
    assert ("run-log", "validate-run-id") not in cli._REGISTRY  # pyright: ignore[reportPrivateUsage]
    assert ("run-log", "validate-run-id") not in cli._MACHINE_STDOUT_KEYS  # pyright: ignore[reportPrivateUsage]
    assert cli.main(["run-log", "validate-run-id", "--run-id=-abc123"]) == 2


def test_run_log_storage_preflight_entrypoint_is_retired() -> None:
    assert ("run-log", "storage-preflight") not in cli._REGISTRY  # pyright: ignore[reportPrivateUsage]
    assert ("run-log", "storage-preflight") not in cli._MACHINE_STDOUT_KEYS  # pyright: ignore[reportPrivateUsage]
    assert cli.main(["run-log", "storage-preflight", "--repo-root", "/tmp"]) == 2


@pytest.mark.parametrize("verb", ["publish", "sync"])
def test_run_log_publication_entrypoints_are_retired(verb: str) -> None:
    assert ("run-log", verb) not in cli._REGISTRY  # pyright: ignore[reportPrivateUsage]
    assert ("run-log", verb) not in cli._MACHINE_STDOUT_KEYS  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize(
    "verb",
    [
        "lifecycle-start",
        "lifecycle-finalize",
        "lifecycle-failure",
        "lifecycle-cancel",
        "lifecycle-early-return",
    ],
)
def test_run_lifecycle_entrypoints_are_retired(verb: str) -> None:
    assert ("run-log", verb) not in cli._REGISTRY  # pyright: ignore[reportPrivateUsage]
    assert ("run-log", verb) not in cli._MACHINE_STDOUT_KEYS  # pyright: ignore[reportPrivateUsage]


def test_dispatch_oos_serialize() -> None:
    mock_main = MagicMock(return_value=0)
    with patch.dict("sys.modules", {"larch.issue.oos": MagicMock(oos_serialize_main=mock_main)}):
        rc = cli.main(["oos", "serialize", "--findings-file", "f", "--output-file", "o"])
    mock_main.assert_called_once_with(["--findings-file", "f", "--output-file", "o"])
    assert rc == 0


def test_dispatch_oos_normalize_header() -> None:
    mock_main = MagicMock(return_value=0)
    with patch.dict("sys.modules", {"larch.issue.oos": MagicMock(oos_normalize_header_main=mock_main)}):
        rc = cli.main(["oos", "normalize-header", "--seq", "1"])
    mock_main.assert_called_once_with(["--seq", "1"])
    assert rc == 0


def test_exit_passthrough_from_delegated_main() -> None:
    mock_main = MagicMock(return_value=42)
    with patch.dict("sys.modules", {"larch.implement.ship": MagicMock(main=mock_main)}):
        rc = cli.main(["ship", "pr"])
    assert rc == 42


def test_systemexit_propagates_unchanged() -> None:
    def _raise(*_: object) -> int:
        raise SystemExit(3)

    with patch.dict("sys.modules", {"larch.implement.ship": MagicMock(main=_raise)}):
        with pytest.raises(SystemExit) as exc_info:
            _ = cli.main(["ship", "pr"])
    assert exc_info.value.code == 3


def test_lazy_import_top_level_only_argparse_importlib_sys() -> None:
    # cli.py is now a thin shim; the real dispatcher with the lazy-import contract
    # lives in larch/cli.py.  Verify the shim itself only imports sys + larch.cli.
    source = CLI_PATH.read_text(encoding="utf-8")
    lines = [ln.strip() for ln in source.splitlines() if ln.startswith(("import ", "from "))]
    top_imports = [ln for ln in lines if not ln.startswith("#") and not ln.startswith("from __future__")]
    allowed = {"import sys", "import larch.cli as _cli"}
    for imp in top_imports:
        assert imp in allowed, f"Unexpected top-level import in cli.py shim: {imp!r}"
    # The real dispatcher (larch/cli.py) must only top-level-import lightweight modules.
    dispatcher_source = CLI_PATH.parent / "larch" / "cli.py"
    dsrc = dispatcher_source.read_text(encoding="utf-8")
    dlines = [ln.strip() for ln in dsrc.splitlines() if ln.startswith(("import ", "from "))]
    dtop = [ln for ln in dlines if not ln.startswith("#") and not ln.startswith("from __future__")]
    dispatcher_allowed = {"import argparse", "import importlib", "import os", "import sys"}
    for imp in dtop:
        assert imp in dispatcher_allowed, f"Unexpected top-level import in larch/cli.py: {imp!r}"


def test_affected_registry_targets_resolve_to_domain_modules() -> None:
    affected = {"larch.git.git", "larch.git.push", "larch.git.pr", "larch.git.merge", "larch.git.gh", "larch.implement.ci"}
    retired = {"git_cli", "push_cli", "pr_cli", "merge_cli", "gh_cli", "ci_cli", "git", "push", "pr", "merge", "gh"}
    checked = 0
    for module_name, func_name, _machine_stdout in cli._REGISTRY.values():  # pyright: ignore[reportPrivateUsage]
        assert module_name not in retired
        if module_name in affected:
            module = importlib.import_module(module_name)
            assert getattr(module, func_name) is not None
            checked += 1
    assert checked == 14


def test_all_registry_targets_resolve_to_callable_mains() -> None:
    for (domain, verb), (module_name, func_name, _machine_stdout) in cli._REGISTRY.items():  # pyright: ignore[reportPrivateUsage]
        module = importlib.import_module(module_name)
        target = getattr(module, func_name, None)
        assert callable(target), f"{domain} {verb} -> {module_name}.{func_name}"


def test_machine_stdout_keys_derived_from_registry() -> None:
    derived = frozenset(
        key for key, (_module, _func, machine_stdout) in cli._REGISTRY.items() if machine_stdout  # pyright: ignore[reportPrivateUsage]
    )
    assert derived == cli._MACHINE_STDOUT_KEYS  # pyright: ignore[reportPrivateUsage]


def test_repointed_design_commands_retain_machine_stdout_and_defining_modules() -> None:
    design_samples = {
        ("design", "step0-session"): ("larch.design.design_step0", "step0_session_entry_main"),
        ("design", "step5c"): ("larch.design.design_step5c", "step5c_main"),
        ("design", "step2b-drafter"): ("larch.design.design_step2b", "step2b_drafter_main"),
        ("design", "settle-next-action"): ("larch.design.design_session", "settle_next_action_main"),
        ("design", "stage-terminal-state"): ("larch.design.design_terminal", "stage_terminal_state_main"),
    }
    for key, (module_name, func_name) in design_samples.items():
        registered = cli._REGISTRY[key]  # pyright: ignore[reportPrivateUsage]
        assert registered == (module_name, func_name, True)
        assert key in cli._MACHINE_STDOUT_KEYS  # pyright: ignore[reportPrivateUsage]
    for module_name, _func_name, _machine_stdout in cli._REGISTRY.values():  # pyright: ignore[reportPrivateUsage]
        assert module_name != "larch.design.design_lifecycle"


def test_human_facing_registry_rows_keep_machine_stdout_false() -> None:
    assert cli._REGISTRY[("ship", "pr")][2] is False  # pyright: ignore[reportPrivateUsage]
    assert ("ship", "pr") not in cli._MACHINE_STDOUT_KEYS  # pyright: ignore[reportPrivateUsage]


def test_design_kv_entrypoint_disables_inherited_quiet(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_QUIET_ACTIVE", "1")
    monkeypatch.setenv("LARCH_QUIET_PID", "999999")
    mock_main = MagicMock(return_value=0)
    with patch.dict("sys.modules", {"larch.design.design_argv": MagicMock(parse_flags_main=mock_main)}):
        rc = cli.main(["design", "parse-flags", "--help"])
    assert rc == 0
    assert os.environ["LARCH_QUIET_DISABLE"] == "1"


def test_machine_stdout_entrypoints_disable_inherited_quiet(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_QUIET_ACTIVE", "1")
    monkeypatch.setenv("LARCH_QUIET_PID", "999999")
    cases = [
        (["checks", "repair-loop", "--help"], "larch.implement.checks", "checks_repair_loop_main"),
        (["ship", "pre-driver"], "larch.implement.implement_dispatch", "ship_pre_driver_main"),
        (
            ["ship", "pre-fix-rebase", "--implement-tmpdir", "/tmp/x"],
            "larch.implement.implement_dispatch",
            "ship_pre_fix_rebase_main",
        ),
        (["ship", "route-exit"], "larch.implement.implement_dispatch", "ship_route_exit_main"),
        (
            ["architectural-assessment", "materialize", "--kind", "guidelines"],
            "larch.implement.architectural_assessment",
            "materialize_main",
        ),
        (
            ["architectural-assessment", "submit", "--kind", "guidelines", "--state", "clean", "--note-file", "/tmp/x"],
            "larch.implement.architectural_assessment",
            "submit_main",
        ),
        (["ship", "reconcile-manual-merge"], "larch.implement.ship_recovery", "reconcile_manual_merge_main"),
        (["implement", "commit-route"], "larch.implement.implement_dispatch", "commit_route_main"),
        (["implement", "step-6-entry"], "larch.implement.implement_dispatch", "step6_entry_main"),
        (["implement", "step-8-oos-checkpoint"], "larch.implement.implement_dispatch", "step8_oos_checkpoint_main"),
        (
            ["implement", "step-18-gate-logs-flush"],
            "larch.implement.implement_dispatch",
            "step_18_gate_logs_flush_main",
        ),
        (["implement", "step-18"], "larch.implement.implement_dispatch", "step_18_main"),
        (["implement", "step-19"], "larch.implement.implement_dispatch", "step_19_main"),
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
    with patch.dict("sys.modules", {"larch.review.review_core_body": MagicMock(review_core_main=mock_main)}):
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
    """larch/cli.py (canonical dispatcher) has the version guard."""
    dispatcher_path = CLI_PATH.parent / "larch" / "cli.py"
    source = dispatcher_path.read_text(encoding="utf-8")
    assert "Python 3.11 or newer" in source


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
