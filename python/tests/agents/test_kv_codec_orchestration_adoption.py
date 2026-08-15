"""Characterize shared-codec behavior at migrated orchestration call sites."""
# These tests deliberately pin private migration seams.
# pyright: reportPrivateUsage=false

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from larch.agents import _vendor
from larch.implement import (
    checks_lint_fix,
    dispatch_commit_route,
    dispatch_manifest,
    dispatch_ship,
    step_7a,
)


def test_vendor_cap_status_uses_first_whitespace_token() -> None:
    result = _vendor.check_token_budget_cap(
        cap="10",
        step="step",
        runner=lambda _argv: type("R", (), {"stdout": "OTHER=1 STATUS=cap_hit STATUS=under_cap\n"})(),
    )
    assert result.hit is True

    miss = _vendor.check_token_budget_cap(
        cap="10",
        step="step",
        runner=lambda _argv: type("R", (), {"stdout": "STATUS=under_cap TOTAL=1\n"})(),
    )
    assert miss.hit is False


def test_parse_launcher_exit_first_digit_or_none() -> None:
    assert checks_lint_fix._parse_launcher_exit("LAUNCHER_EXIT=0\nLAUNCHER_EXIT=1\n") == 0
    assert checks_lint_fix._parse_launcher_exit("LAUNCHER_EXIT=nope\nLAUNCHER_EXIT=1\n") is None
    assert checks_lint_fix._parse_launcher_exit("OTHER=1\n") is None


def test_whitespace_kv_first_wins_and_skips_trailing_prose() -> None:
    line = "STATUS=fail FAILURE_REASON=x STATUS=ok trailing prose bad=1"
    assert dispatch_commit_route._parse_whitespace_kv_line(line) == {
        "STATUS": "fail",
        "FAILURE_REASON": "x",
    }


def test_terminal_action_any_matching_next_action() -> None:
    assert dispatch_commit_route._terminal_action_in_output(
        "NEXT_ACTION=continue\nNEXT_ACTION=stall\n"
    )
    assert not dispatch_commit_route._terminal_action_in_output(
        "NEXT_ACTION=keep-going\nOTHER=1\n"
    )


def test_relay_commit_kvs_filters_allowed_keys(capsys: pytest.CaptureFixture[str]) -> None:
    dispatch_commit_route._relay_commit_kvs(
        "NEXT_ACTION=stall\nCOMMIT_OUTCOME=failed\nIGNORED=1\nNEXT_ACTION=again\n"
    )
    assert capsys.readouterr().out == (
        "NEXT_ACTION=stall\nCOMMIT_OUTCOME=failed\nNEXT_ACTION=again\n"
    )


def test_prelaunch_index_reader_uses_first_value(tmp_path: Path) -> None:
    flag = tmp_path / "prelaunch.env"
    _ = flag.write_text(
        "PRELAUNCH_INDEX_NONEMPTY=true\nPRELAUNCH_INDEX_NONEMPTY=false\n",
        encoding="utf-8",
    )
    st = SimpleNamespace(prelaunch_index_flag=flag)
    assert dispatch_manifest._read_prelaunch_index_nonempty(st) == "true"  # type: ignore[arg-type]  # stub state for private reader
    missing = SimpleNamespace(prelaunch_index_flag=tmp_path / "absent.env")
    assert dispatch_manifest._read_prelaunch_index_nonempty(missing) == "false"  # type: ignore[arg-type]  # stub state for private reader


def test_assessment_handoff_rejects_duplicate_keys(tmp_path: Path) -> None:
    handoff = tmp_path / ".ship-route-exit-handoff.env"
    _ = handoff.write_text("OUTCOME=ok\nDETAIL=x\nOUTCOME=bad\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate handoff key: OUTCOME"):
        _ = dispatch_ship._read_handoff_fields(handoff=handoff)

    clean = tmp_path / "clean.env"
    _ = clean.write_text("OUTCOME=ok\nDETAIL=x\nignored\n", encoding="utf-8")
    lines, fields = dispatch_ship._read_handoff_fields(handoff=clean)
    assert fields == {"OUTCOME": "ok", "DETAIL": "x"}
    assert "ignored" in lines


def test_step_7a_first_rc_last_wins(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sidecar = tmp_path / "code-flow-diagram.retried"
    _ = sidecar.write_text("FIRST_RC=1\nFIRST_RC=42\n", encoding="utf-8")
    issues: list[str] = []

    def fake_generate(
        implement_tmpdir: Path,
        *,
        base_remote: str,
        base_ref: str,
    ) -> object:
        _ = (implement_tmpdir, base_remote, base_ref)
        return SimpleNamespace(
            exit_code=0,
            status="skipped",
            diagram_file="",
            reason="",
        )

    def fake_append(**kwargs: object) -> None:
        issues.append(str(kwargs.get("entry", "")))

    monkeypatch.setattr(step_7a.pr_body, "generate_code_flow_diagram", fake_generate)
    monkeypatch.setattr(step_7a.run_log_batch, "append_execution_issue", fake_append)
    _ = step_7a._generate_code_flow_diagram(
        tmp_path,
        base_remote="origin",
        base_ref="main",
    )
    assert any("rc=42" in entry for entry in issues)
    assert not sidecar.exists()
