"""Characterize shared-codec behavior at migrated orchestration call sites."""
# These tests deliberately pin private migration seams.
# pyright: reportPrivateUsage=false

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from larch.agents import _vendor
from larch.core import config
from larch.implement import (
    checks_lint_fix,
    dispatch_commit_route,
    dispatch_manifest,
    dispatch_ship,
    step_7a,
)
from larch.review import (
    plan_review_loop,
    plan_review_normalize,
    review_pipeline_shared,
    voting,
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


def test_collector_records_last_wins_within_block_and_ignores_preamble() -> None:
    text = (
        "DIAG=noise\n"
        "REVIEWER_FILE=a.md\n"
        "STATUS=old\r\n"
        "STATUS=new\n"
        "\n"
        "REVIEWER_FILE=b.md\n"
        "STATUS=only\n"
    )
    assert review_pipeline_shared.parse_collector_records(text) == [
        {"REVIEWER_FILE": "a.md", "STATUS": "new"},
        {"REVIEWER_FILE": "b.md", "STATUS": "only"},
    ]


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


def test_resolve_findings_file_uses_last_value(tmp_path: Path) -> None:
    findings = tmp_path / "custom-findings.md"
    _ = findings.write_text("ok\n", encoding="utf-8")
    approval = tmp_path / ".gate-b-per-round-approval-round-1.env"
    _ = approval.write_text(
        f"FINDINGS_FILE={tmp_path / 'other.md'}\nFINDINGS_FILE={findings}\n",
        encoding="utf-8",
    )
    assert plan_review_loop._resolve_findings_file(tmpdir=tmp_path, round_num=1) == findings.resolve()


def test_step3_overlay_allowlist_last_wins_and_prints_warn(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    stdout = tmp_path / "stdout.env"
    _ = stdout.write_text(
        "NEXT_ACTION=old\nNEXT_ACTION=new\nDROP=1\nWARN=one\nWARN=two\n",
        encoding="utf-8",
    )
    values: dict[str, str] = {}
    plan_review_normalize._step3_overlay_stdout_env(
        values=values,
        stdout_file=stdout,
        primary_regular=True,
        selected_source=tmp_path / "other.env",
    )
    assert values["NEXT_ACTION"] == "new"
    assert "DROP" not in values
    assert capsys.readouterr().out == "WARN=one\nWARN=two\n"


def test_step3_read_result_env_allowlist_last_wins(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result_env = tmp_path / "bgjob" / "design-step3-review.result.env"
    result_env.parent.mkdir(parents=True)
    _ = result_env.write_text(
        f"{config.BGJOB_RC_KEY}=0\nNEXT_ACTION=keep\nNEXT_ACTION=final-summary:done\n"
        "LOOP_STATUS=complete\nIGNORED=1\n",
        encoding="utf-8",
    )
    rc = plan_review_normalize._step3_normalize_read_result_env(tmp_path)
    assert rc == 0
    out = capsys.readouterr().out
    assert "NEXT_ACTION=final-summary:done" in out
    assert "IGNORED=" not in out
    assert "READ_RESULT_ENV_STATUS=ok" in out


def test_pipeline_collector_records_blank_line_separated(tmp_path: Path) -> None:
    path = tmp_path / "collector.env"
    _ = path.write_text(
        "A=1\nA=2\n\nB=3\n",
        encoding="utf-8",
    )
    assert review_pipeline_shared._collector_records(path) == [
        {"A": "2"},
        {"B": "3"},
    ]


def test_voting_write_tally_relays_kv_and_prose(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))

    def fake_run(argv: list[str]) -> voting.proc.CommandResult:
        _ = argv
        return voting.proc.CommandResult(
            tuple(argv),
            0,
            "LOG_WRITTEN=true\nSTATUS=ok\nSTATUS=dup\nplain prose\n",
            "",
            0.0,
        )

    monkeypatch.setattr(voting.proc, "run", fake_run)
    rc = voting.write_tally_main(
        [
            "--log-root",
            str(tmp_path / "larch-logs"),
            "--skill",
            "implement",
            "--run-id",
            "run-codec",
            "--phase",
            "code-review",
            "--mode",
            "simple",
            "--accepted",
            "1",
            "--rejected",
            "0",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "LOG_WRITTEN=true\n" in out
    assert "STATUS=ok\n" in out
    assert "STATUS=dup\n" in out
    assert "plain prose\n" in out
