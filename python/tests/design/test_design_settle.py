"""Parity coverage for in-process design step35 settle."""

from __future__ import annotations

from pathlib import Path

import pytest

from larch.design.design_settle import (
    ChildCapture,
    SettleRequest,
    SettleResult,
    SettleRunners,
    step35_settle_for,
    step35_settle_main,
)
from larch.review import plan_review
from test_support import make_design_tmpdir


def _request(
    design: Path,
    *,
    site: str = "gate-b",
    round_num: str | None = "1",
    force_dedup: bool = False,
) -> SettleRequest:
    return SettleRequest(
        site=site,  # type: ignore[arg-type]
        design_tmpdir=design,
        round_num=round_num,
        force_dedup=force_dedup,
        plugin_root="/tmp/plugin",
        issue_number="1",
    )


def _runners(
    *,
    dedup_rc: int = 0,
    dedup_out: str = "GATE_B_DEDUP_STATUS=ok\n",
    postplan_out: str = "POSTPLAN_RC=0\n",
    postplan_child_rc: int | None = None,
    dialectic_rc: int = 0,
    pause_rc: int = 0,
    pause_out: str = "",
    postplan_sites: list[str] | None = None,
) -> SettleRunners:
    seen_sites = postplan_sites if postplan_sites is not None else []

    def dedup(_design: Path) -> ChildCapture:
        return ChildCapture(rc=dedup_rc, stdout=dedup_out)

    def postplan(_request: SettleRequest, postplan_site: str) -> ChildCapture:
        seen_sites.append(postplan_site)
        child = postplan_child_rc if postplan_child_rc is not None else 0
        return ChildCapture(rc=child, stdout=postplan_out)

    def dialectic(_design: Path) -> int:
        return dialectic_rc

    def pause(_request: SettleRequest) -> ChildCapture:
        return ChildCapture(rc=pause_rc, stdout=pause_out)

    return SettleRunners(dedup=dedup, postplan=postplan, dialectic_clear=dialectic, pause_save=pause)


@pytest.mark.parametrize(
    ("site", "expected_postplan_site", "expected_action"),
    [
        ("gate-b", "gate-b", "gate-b-continue"),
        ("gate-a", "discussion-round2", "gate-a-return"),
        ("discussion-round2", "discussion-round2", "gate-a-return"),
        ("gate-c", "gate-c", "gate-c-return"),
    ],
)
def test_settle_clean_site_mapping(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    site: str,
    expected_postplan_site: str,
    expected_action: str,
) -> None:
    design = make_design_tmpdir(tmp_path)
    seen: list[str] = []
    result = step35_settle_for(
        request=_request(design, site=site, round_num="3"),
        runners=_runners(postplan_sites=seen),
    )
    assert result.exit_rc == 0
    assert result.next_action == expected_action
    assert seen == [expected_postplan_site]
    assert f"SETTLE_NEXT_ACTION={expected_action}" in capsys.readouterr().out
    if site == "gate-b":
        assert (design / ".gate-b-postapply-ready-3").read_text(encoding="utf-8") == "ready\n"
        assert (design / ".step3-round-3.phase").read_text(encoding="utf-8") == "awaiting-continuation\n"


def test_settle_invalid_site_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = make_design_tmpdir(tmp_path)
    monkeypatch.setenv("DESIGN_TMPDIR", str(design))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path / "plugin"))
    (tmp_path / "plugin").mkdir()
    rc = step35_settle_main(["--site", "nope", "--plugin-root", str(tmp_path / "plugin")])
    assert rc == 2


def test_settle_gate_b_missing_round(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    design = make_design_tmpdir(tmp_path)
    result = step35_settle_for(
        request=_request(design, site="gate-b", round_num=None),
        runners=_runners(),
    )
    assert result.exit_rc == 2
    assert "Gate B requires" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("postplan_out", "expected_action", "expected_rc", "phase"),
    [
        ("POSTPLAN_RC=10\n", "gate-b-validator-fail", 10, "awaiting-postplan-operator"),
        ("POSTPLAN_RC=12\n", "gate-b-hard-size", 12, "awaiting-post-apply"),
        ("POSTPLAN_RC=13\n", "gate-b-split", 13, "awaiting-postplan-operator"),
    ],
)
def test_settle_gate_b_postplan_actions(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    postplan_out: str,
    expected_action: str,
    expected_rc: int,
    phase: str,
) -> None:
    design = make_design_tmpdir(tmp_path)
    result = step35_settle_for(
        request=_request(design, round_num="7"),
        runners=_runners(postplan_out=postplan_out),
    )
    assert result.exit_rc == expected_rc
    assert result.next_action == expected_action
    assert f"SETTLE_NEXT_ACTION={expected_action}" in capsys.readouterr().out
    assert (design / ".step3-round-7.phase").read_text(encoding="utf-8") == f"{phase}\n"


@pytest.mark.parametrize(
    ("site", "postplan_out", "expected_action", "expected_rc"),
    [
        ("gate-a", "POSTPLAN_RC=10\n", "gate-a-validator-fail", 10),
        ("gate-a", "POSTPLAN_RC=12\n", "gate-a-hard-size", 12),
        ("gate-a", "POSTPLAN_RC=13\n", "gate-a-split", 13),
        ("discussion-round2", "POSTPLAN_RC=10\n", "gate-a-validator-fail", 10),
        ("gate-c", "POSTPLAN_RC=10\n", "gate-c-validator-fail", 10),
        ("gate-c", "POSTPLAN_RC=12\n", "gate-c-hard-size", 12),
        ("gate-c", "POSTPLAN_RC=13\n", "gate-c-split", 13),
        ("gate-c", "POSTPLAN_RC=0\n", "gate-c-return", 0),
    ],
)
def test_settle_non_gate_b_actions(
    tmp_path: Path,
    site: str,
    postplan_out: str,
    expected_action: str,
    expected_rc: int,
) -> None:
    design = make_design_tmpdir(tmp_path)
    result = step35_settle_for(
        request=_request(design, site=site, round_num=None),
        runners=_runners(postplan_out=postplan_out),
    )
    assert result.exit_rc == expected_rc
    assert result.next_action == expected_action


def test_settle_dedup_revise_restores_snapshot(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    design = make_design_tmpdir(tmp_path)
    snapshot = design / "plan-pre-apply-round-9.txt"
    _ = snapshot.write_text("# snapshot\n", encoding="utf-8")
    _ = (design / "plan.txt").write_text("# mutated\n", encoding="utf-8")
    result = step35_settle_for(
        request=_request(design, round_num="9"),
        runners=_runners(dedup_rc=1, dedup_out="GATE_B_DEDUP_STATUS=trailer-key-drift\n"),
    )
    assert result.exit_rc == 1
    assert result.next_action == "dedup-revise"
    assert (design / "plan.txt").read_text(encoding="utf-8") == "# snapshot\n"
    assert not (design / ".gate-b-postapply-ready-9").exists()
    assert "SETTLE_NEXT_ACTION=dedup-revise" in capsys.readouterr().out


def test_settle_dedup_hard_fail(tmp_path: Path) -> None:
    design = make_design_tmpdir(tmp_path)
    result = step35_settle_for(
        request=_request(design, site="gate-c", round_num=None),
        runners=_runners(dedup_rc=3),
    )
    assert result.exit_rc == 3


def test_settle_missing_and_duplicate_postplan_rc(tmp_path: Path) -> None:
    design = make_design_tmpdir(tmp_path)
    missing = step35_settle_for(
        request=_request(design, site="gate-a", round_num=None),
        runners=_runners(postplan_out="EMIT_PLAN_STATUS=ok\n"),
    )
    assert missing.exit_rc == 3
    dup = step35_settle_for(
        request=_request(design, site="gate-a", round_num=None),
        runners=_runners(postplan_out="POSTPLAN_RC=0\nPOSTPLAN_RC=0\n"),
    )
    assert dup.exit_rc == 3


def test_settle_child_rc_mismatch_on_clean(tmp_path: Path) -> None:
    design = make_design_tmpdir(tmp_path)
    result = step35_settle_for(
        request=_request(design, site="gate-a", round_num=None),
        runners=_runners(postplan_out="POSTPLAN_RC=0\n", postplan_child_rc=1),
    )
    assert result.exit_rc == 3


def test_settle_unexpected_postplan_rc(tmp_path: Path) -> None:
    design = make_design_tmpdir(tmp_path)
    result = step35_settle_for(
        request=_request(design, site="gate-a", round_num=None),
        runners=_runners(postplan_out="POSTPLAN_RC=99\n"),
    )
    assert result.exit_rc == 3


def test_settle_dialectic_warning_fail_open(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    design = make_design_tmpdir(tmp_path)
    result = step35_settle_for(
        request=_request(design, site="gate-c", round_num=None),
        runners=_runners(dialectic_rc=2),
    )
    assert result.exit_rc == 0
    err = capsys.readouterr().err
    assert "dialectic-clear-stale failed after dedup" in err
    assert "dialectic-clear-stale failed after postplan" in err


def test_settle_pause_requested(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    design = make_design_tmpdir(tmp_path)
    _ = (design / ".pause-requested").write_text("", encoding="utf-8")
    result = step35_settle_for(
        request=_request(design, site="gate-a", round_num=None),
        runners=_runners(pause_out="PAUSE_OK=true\n"),
    )
    assert result.exit_rc == 11
    assert result.next_action == "pause"
    assert "SETTLE_NEXT_ACTION=pause" in capsys.readouterr().out


def test_settle_postplan_pause_signal(tmp_path: Path) -> None:
    design = make_design_tmpdir(tmp_path)
    result = step35_settle_for(
        request=_request(design, site="gate-b", round_num="2"),
        runners=_runners(postplan_out="PAUSE_OK=true\n"),
    )
    assert result.exit_rc == 11
    assert result.next_action == "pause"
    assert (design / ".step3-round-2.phase").read_text(encoding="utf-8") == "awaiting-post-apply\n"


def test_settle_skips_dedup_on_ready_marker_resume(tmp_path: Path) -> None:
    design = make_design_tmpdir(tmp_path)
    _ = (design / ".gate-b-postapply-ready-4").write_text("ready\n", encoding="utf-8")
    _ = (design / ".step3-round-4.phase").write_text("awaiting-continuation\n", encoding="utf-8")
    dedup_calls: list[int] = []

    def dedup(_design: Path) -> ChildCapture:
        dedup_calls.append(1)
        return ChildCapture(rc=0, stdout="should-not-run\n")

    runners = _runners()
    runners = SettleRunners(
        dedup=dedup,
        postplan=runners.postplan,
        dialectic_clear=runners.dialectic_clear,
        pause_save=runners.pause_save,
    )
    result = step35_settle_for(request=_request(design, round_num="4"), runners=runners)
    assert result.exit_rc == 0
    assert dedup_calls == []


def test_settle_force_dedup_overrides_marker(tmp_path: Path) -> None:
    design = make_design_tmpdir(tmp_path)
    _ = (design / ".gate-b-postapply-ready-5").write_text("ready\n", encoding="utf-8")
    dedup_calls: list[int] = []

    def dedup(_design: Path) -> ChildCapture:
        dedup_calls.append(1)
        return ChildCapture(rc=0, stdout="GATE_B_DEDUP_STATUS=ok\n")

    base = _runners()
    runners = SettleRunners(
        dedup=dedup,
        postplan=base.postplan,
        dialectic_clear=base.dialectic_clear,
        pause_save=base.pause_save,
    )
    result = step35_settle_for(
        request=_request(design, round_num="5", force_dedup=True),
        runners=runners,
    )
    assert result.exit_rc == 0
    assert dedup_calls == [1]


def test_settle_reruns_dedup_when_awaiting_postplan_operator(tmp_path: Path) -> None:
    design = make_design_tmpdir(tmp_path)
    _ = (design / ".gate-b-postapply-ready-6").write_text("ready\n", encoding="utf-8")
    _ = (design / ".step3-round-6.phase").write_text("awaiting-postplan-operator\n", encoding="utf-8")
    dedup_calls: list[int] = []

    def dedup(_design: Path) -> ChildCapture:
        dedup_calls.append(1)
        return ChildCapture(rc=0, stdout="GATE_B_DEDUP_STATUS=ok\n")

    base = _runners()
    runners = SettleRunners(
        dedup=dedup,
        postplan=base.postplan,
        dialectic_clear=base.dialectic_clear,
        pause_save=base.pause_save,
    )
    result = step35_settle_for(request=_request(design, round_num="6"), runners=runners)
    assert result.exit_rc == 0
    assert dedup_calls == [1]


def test_plan_review_step35_settle_delegates_in_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    design = make_design_tmpdir(tmp_path)
    monkeypatch.setenv("DESIGN_TMPDIR", str(design))
    plugin = tmp_path / "plugin"
    plugin.mkdir()
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(plugin))

    def fake_for(*, request: SettleRequest, runners: SettleRunners | None = None) -> SettleResult:
        _ = runners
        assert request.site == "gate-c"
        return SettleResult(exit_rc=0, next_action="gate-c-return")

    monkeypatch.setattr("larch.design.design_settle.step35_settle_for", fake_for)
    rc = plan_review.step35_settle(["--site", "gate-c", "--plugin-root", str(plugin)])
    assert rc == 0
