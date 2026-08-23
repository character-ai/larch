"""Tests for cli.py dispatcher."""

from __future__ import annotations

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


def test_retired_report_tokens_modules_are_not_importable() -> None:
    for module in (
        "larch.report.report_tokens_cli",
        "larch.report.report_tokens_render",
        "larch.report.report_tokens_plot",
        "larch.report.report_tokens_issue",
    ):
        assert importlib.util.find_spec(module) is None


def test_report_tokens_analyze_is_not_a_python_command() -> None:
    assert cli.main(["report-tokens", "analyze", "--skill", "implement"]) == 2


def test_forked_repo_entrypoint_is_retired() -> None:
    assert ("forked-repo", "setup") not in cli._REGISTRY  # pyright: ignore[reportPrivateUsage]
    assert ("forked-repo", "setup") not in cli._MACHINE_STDOUT_KEYS  # pyright: ignore[reportPrivateUsage]
    assert importlib.util.find_spec("larch.core.forked_repo") is None


def test_architectural_assessment_entrypoint_is_retired() -> None:
    assert ("architectural-assessment", "materialize") not in cli._REGISTRY  # pyright: ignore[reportPrivateUsage]
    assert ("architectural-assessment", "submit") not in cli._REGISTRY  # pyright: ignore[reportPrivateUsage]
    assert ("architectural-assessment", "sanitize-detail") not in cli._REGISTRY  # pyright: ignore[reportPrivateUsage]
    assert ("architectural-assessment", "final-report-sections") not in cli._REGISTRY  # pyright: ignore[reportPrivateUsage]
    assert (
        "architectural-assessment",
        "sanitize-detail",
    ) not in cli._MACHINE_STDOUT_KEYS  # pyright: ignore[reportPrivateUsage]
    assert (
        cli.main(
            [
                "architectural-assessment",
                "sanitize-detail",
                "--implement-tmpdir",
                "/tmp/x",
            ]
        )
        == 2
    )


@pytest.mark.parametrize(
    ("domain", "verb"),
    [
        (domain, verb)
        for domain in ("architectural-guidelines", "architectural-invariants")
        for verb in ("read", "present-note", "persist-design-assessment")
    ],
)
def test_architectural_design_entrypoints_are_retired(domain: str, verb: str) -> None:
    assert (domain, verb) not in cli._REGISTRY  # pyright: ignore[reportPrivateUsage]
    assert (domain, verb) not in cli._MACHINE_STDOUT_KEYS  # pyright: ignore[reportPrivateUsage]
    assert cli.main([domain, verb]) == 2


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
    ["cleanup-implement-logs", "migrate-layout", "retro-fix-cursor", "retro-v3-sweep"],
)
def test_run_log_historical_maintenance_entrypoints_are_retired(verb: str) -> None:
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


def test_retired_git_registry_targets_are_absent() -> None:
    affected = {"larch.git.git", "larch.git.push", "larch.git.pr", "larch.git.gh"}
    retired = {"git_cli", "push_cli", "pr_cli", "merge_cli", "gh_cli", "ci_cli", "git", "push", "pr", "merge", "gh"}
    for module_name, _func_name, _machine_stdout in cli._REGISTRY.values():  # pyright: ignore[reportPrivateUsage]
        assert module_name not in retired
        assert module_name not in affected


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


def test_rust_owned_design_commands_are_absent_from_python_registry() -> None:
    for key in (
        ("design", "prelude"),
        ("design", "step3-continuation-entry"),
        ("design", "dialectic-gatec"),
        ("design", "dialectic-manual"),
    ):
        assert key not in cli._REGISTRY  # pyright: ignore[reportPrivateUsage]
        assert key not in cli._MACHINE_STDOUT_KEYS  # pyright: ignore[reportPrivateUsage]
    for module_name, _func_name, _machine_stdout in cli._REGISTRY.values():  # pyright: ignore[reportPrivateUsage]
        assert module_name != "larch.design.design_lifecycle"


def test_rust_owned_ship_commands_are_absent_from_python_registry() -> None:
    assert ("ship", "pr") not in cli._REGISTRY  # pyright: ignore[reportPrivateUsage]
    assert ("ship", "reconcile-manual-merge") not in cli._REGISTRY  # pyright: ignore[reportPrivateUsage]


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
    assert "ship pr" not in result.stdout


def test_subprocess_unknown_domain_exits_2() -> None:
    result = subprocess.run(
        [sys.executable, str(CLI_PATH), "no-such-domain", "verb"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "unknown subcommand" in result.stderr


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
