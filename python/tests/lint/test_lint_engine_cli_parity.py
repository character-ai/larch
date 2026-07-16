"""CLI argument-contract coverage for lint commands routed through the engine."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from larch.lint import (
    lint_agent_tool_contract,
    lint_complexity_debt,
    lint_doc_pointer_paths,
    lint_gh_argv_literal,
    lint_git_push_refspec,
    lint_guidelines_note_wrapper_bypass,
    lint_prefix_case_variant,
    lint_readability_preamble,
    lint_run_log_run_id,
    lint_run_log_walkers,
    lint_shared_convention_regex,
    lint_skill_md_flag_signature,
    lint_tier1a,
)

LintMain = Callable[[list[str] | None], int]
REPO_ROOT = Path(__file__).resolve().parents[3]
ROOT_ONLY_COMMANDS: tuple[tuple[str, LintMain, int], ...] = (
    ("agent-tool-contract", lint_agent_tool_contract.main, 2),
    ("doc-pointer-paths", lint_doc_pointer_paths.main, 2),
    ("gh-argv-literal", lint_gh_argv_literal.main, 2),
    ("git-push-refspec", lint_git_push_refspec.main, 2),
    ("guidelines-note-wrapper-bypass", lint_guidelines_note_wrapper_bypass.main, 2),
    ("prefix-case-variant", lint_prefix_case_variant.main, 2),
    ("readability-preamble", lint_readability_preamble.main, 2),
    ("run-log-run-id", lint_run_log_run_id.main, 2),
    ("run-log-walkers", lint_run_log_walkers.main, 2),
    ("shared-convention-regex", lint_shared_convention_regex.main, 2),
    ("skill-md-flag-signature", lint_skill_md_flag_signature.main, 0),
    ("tier1a-size", lint_tier1a.main, 2),
)


@pytest.mark.parametrize(("name", "main", "missing_root_exit"), ROOT_ONLY_COMMANDS)
def test_engine_root_cli_argument_contract(
    name: str,
    main: LintMain,
    missing_root_exit: int,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Keep root-only legacy commands behaviorally aligned with engine parsing."""
    assert main([]) == 0, name
    _ = capsys.readouterr()
    assert main(["--root", str(REPO_ROOT)]) == 0, name
    _ = capsys.readouterr()
    assert main(["--unknown"]) == 2, name
    assert "usage:" in capsys.readouterr().err
    assert main(["--root"]) == 2, name
    assert "argument --root: expected one argument" in capsys.readouterr().err
    assert main(["--root", str(tmp_path / "missing")]) == missing_root_exit, name
    _ = capsys.readouterr()
    with pytest.raises(SystemExit) as raised:
        _ = main(["--help"])
    assert raised.value.code == 0
    _ = capsys.readouterr()


def test_complexity_debt_cli_argument_contract(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Keep the established ``--report`` branch on the shared engine parser."""
    assert lint_complexity_debt.main(["--report"]) == 0
    _ = capsys.readouterr()
    assert lint_complexity_debt.main(["--root", str(REPO_ROOT), "--report"]) == 0
    _ = capsys.readouterr()
    assert lint_complexity_debt.main([]) == 2
    assert "--report is required" in capsys.readouterr().err
    assert lint_complexity_debt.main(["--unknown", "--report"]) == 2
    assert "usage:" in capsys.readouterr().err
    assert lint_complexity_debt.main(["--root"]) == 2
    assert "argument --root: expected one argument" in capsys.readouterr().err
    with pytest.raises(SystemExit) as raised:
        _ = lint_complexity_debt.main(["--help"])
    assert raised.value.code == 0
    _ = capsys.readouterr()
    assert lint_complexity_debt.main(["--root", str(tmp_path / "missing"), "--report"]) == 2
