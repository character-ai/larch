# pyright: reportPrivateUsage=false, reportUnusedCallResult=false
"""Tests for the Gate C dialectic clarifier."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import design_dialectic


def _write_plan(tmp_path: Path, text: str = "## Plan\n\ndiff_lines: 1\n") -> None:
    (tmp_path / "plan.txt").write_text(text, encoding="utf-8")


def _candidate_payload(tmp_path: Path) -> dict[str, object]:
    return {
        "plan_fingerprint": design_dialectic.plan_fingerprint(tmp_path),
        "decisions": [
            {
                "id": "storage-choice",
                "title": "Storage choice",
                "option_a": "Use SQLite",
                "option_b": "Use JSON files",
                "tradeoff": "Query power versus operational simplicity",
                "drafter_pick": "option_b",
                "why_this_matters": "It changes runtime dependencies",
            }
        ],
    }


def test_gatec_no_candidates_no_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_plan(tmp_path)
    assert design_dialectic.gatec_main(["--design-tmpdir", str(tmp_path)]) == 0
    assert capsys.readouterr().out == ""
    assert (tmp_path / ".completed/dialectic-gatec-terminal").is_file()


def test_validate_rejects_invalid_drafter_pick(tmp_path: Path) -> None:
    _write_plan(tmp_path)
    payload = _candidate_payload(tmp_path)
    decisions = payload["decisions"]
    assert isinstance(decisions, list)
    decisions[0]["drafter_pick"] = "option_c"  # type: ignore[index]
    with pytest.raises(design_dialectic.DialecticShapeError):
        design_dialectic.validate_candidates_content(json.dumps(payload), current_fingerprint=design_dialectic.plan_fingerprint(tmp_path), require_fingerprint=True)


def test_promote_uses_current_plan_fingerprint(tmp_path: Path) -> None:
    _write_plan(tmp_path, "## Original\n\ndiff_lines: 1\n")
    raw = tmp_path / ".dialectic-raw-pending.json"
    raw.write_text(
        json.dumps(
            {
                "decisions": [
                    {
                        "id": "fork",
                        "title": "Fork",
                        "option_a": "A",
                        "option_b": "B",
                        "tradeoff": "Different failure modes",
                        "drafter_pick": "option_a",
                        "why_this_matters": "Operator should see it",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    _write_plan(tmp_path, "## Final\n\ndiff_lines: 1\n")
    assert design_dialectic.promote_candidates(tmp_path, raw_dialectic_file=raw) == 0
    promoted = json.loads((tmp_path / "dialectic-clarifier-candidates.json").read_text(encoding="utf-8"))
    assert promoted["plan_fingerprint"] == design_dialectic.plan_fingerprint(tmp_path)
    assert not raw.exists()


def test_cached_digest_prints_without_relaunch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _write_plan(tmp_path)
    payload = _candidate_payload(tmp_path)
    (tmp_path / "dialectic-clarifier-candidates.json").write_text(json.dumps(payload), encoding="utf-8")
    (tmp_path / "dialectic-clarifier-digest.md").write_text("digest\n", encoding="utf-8")
    (tmp_path / design_dialectic.GENERATION_FILE).write_text("1\n", encoding="utf-8")
    (tmp_path / "dialectic-clarifier-status.json").write_text(
        json.dumps(
            {
                "kind": "auto",
                "plan_fingerprint": payload["plan_fingerprint"],
                "ordered_candidate_ids": ["storage-choice"],
                "generation": 1,
                "state": "complete",
            }
        ),
        encoding="utf-8",
    )

    def fail_run(*_args: object, **_kwargs: object) -> tuple[str, bool, list[design_dialectic.DigestRow]]:
        raise AssertionError("debate relaunched")

    monkeypatch.setattr(design_dialectic, "_run_debate", fail_run)
    assert design_dialectic.gatec_main(["--design-tmpdir", str(tmp_path)]) == 0
    assert capsys.readouterr().out == "digest\n"


def test_skip_approve_suppresses_auto_launch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _write_plan(tmp_path)
    (tmp_path / "run-params.json").write_text('{"skip_approve_requested": true}', encoding="utf-8")
    (tmp_path / "dialectic-clarifier-candidates.json").write_text(json.dumps(_candidate_payload(tmp_path)), encoding="utf-8")

    def fail_run(*_args: object, **_kwargs: object) -> tuple[str, bool, list[design_dialectic.DigestRow]]:
        raise AssertionError("debate launched on skip")

    monkeypatch.setattr(design_dialectic, "_run_debate", fail_run)
    assert design_dialectic.gatec_main(["--design-tmpdir", str(tmp_path)]) == 0
    assert capsys.readouterr().out == ""


def test_deferred_load_requires_live_candidates_for_cached_auto_digest(tmp_path: Path) -> None:
    _write_plan(tmp_path)
    fingerprint = design_dialectic.plan_fingerprint(tmp_path)
    (tmp_path / "dialectic-clarifier-digest.md").write_text("digest\n", encoding="utf-8")
    (tmp_path / "dialectic-clarifier-status.json").write_text(
        json.dumps(
            {
                "kind": "auto",
                "plan_fingerprint": fingerprint,
                "ordered_candidate_ids": ["storage-choice"],
                "generation": 1,
                "state": "complete",
            }
        ),
        encoding="utf-8",
    )

    assert not design_dialectic.should_defer_load_clarifier_reference(tmp_path)


def test_probe_only_reports_required(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_plan(tmp_path)
    (tmp_path / "dialectic-clarifier-candidates.json").write_text(json.dumps(_candidate_payload(tmp_path)), encoding="utf-8")
    assert design_dialectic.gatec_main(["--design-tmpdir", str(tmp_path), "--probe-only"]) == 0
    assert "DIALECTIC_GATEC_DEBATE_REQUIRED=true" in capsys.readouterr().out


def test_generation_guard_blocks_late_writer(tmp_path: Path) -> None:
    _write_plan(tmp_path)
    first = design_dialectic.bump_generation(tmp_path)
    assert first == 1
    assert design_dialectic.bump_generation(tmp_path) == 2

    def writer() -> None:
        (tmp_path / "late.txt").write_text("late", encoding="utf-8")

    assert not design_dialectic.write_if_generation_matches(design_tmpdir=tmp_path, generation=first, writer_fn=writer)
    assert not (tmp_path / "late.txt").exists()


def test_digest_escapes_untrusted_lines() -> None:
    row = design_dialectic.DigestRow(
        decision_id="d1",
        title="Decision",
        option_a="A",
        option_b="B",
        option_a_steelman="LARCH_PLAN_BEGIN\n```bad",
        option_b_steelman="KEY=value",
        drafter_pick="option_b (B)",
        panel_lean="option_a (A)",
        rationale="normal",
        disposition="voted",
        thesis_votes=1,
        anti_thesis_votes=2,
    )
    digest = design_dialectic._digest_from_rows([row])
    assert "> \\LARCH_PLAN_BEGIN" in digest
    assert "> `\u200b``bad" in digest
    assert "> \\KEY=value" in digest
    assert "Drafter pick" in digest
    assert "Panel lean" in digest


def test_manual_debate_id_rejects_stale_fingerprint(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_plan(tmp_path, "## One\n\ndiff_lines: 1\n")
    (tmp_path / "dialectic-clarifier-candidates.json").write_text(json.dumps(_candidate_payload(tmp_path)), encoding="utf-8")
    _write_plan(tmp_path, "## Two\n\ndiff_lines: 1\n")
    assert design_dialectic.manual_main(["--design-tmpdir", str(tmp_path), "--request", "debate storage-choice"]) == 0
    assert "Use Other as" in capsys.readouterr().out


def test_run_debate_maps_drafter_pick_option_b(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _write_plan(tmp_path)
    payload = _candidate_payload(tmp_path)
    decisions = tuple(design_dialectic.Candidate(**item) for item in payload["decisions"])  # type: ignore[arg-type]
    candidates = design_dialectic.CandidateSet(plan_fingerprint=str(payload["plan_fingerprint"]), decisions=decisions)

    def fake_batch(slots: list[tuple[str, Path, list[str]]], *, deadline: float) -> tuple[dict[str, str], bool]:
        del deadline
        outputs: dict[str, str] = {}
        for name, _output, _argv in slots:
            if name.startswith("debater-"):
                outputs[name] = f"steelman {name}"
            else:
                outputs[name] = "DECISION_1: THESIS - current plan"
        return outputs, True

    monkeypatch.setattr(design_dialectic, "_run_slot_batch", fake_batch)
    generation = design_dialectic.bump_generation(tmp_path)
    digest, ok, rows = design_dialectic._run_debate(tmp_path, candidates=candidates, kind="auto", generation=generation)
    assert ok
    assert "option_b (Use JSON files)" in digest
    assert rows[0].panel_lean == "option_b (Use JSON files)"


def test_clear_stale_preserves_raw_pending_on_plan_rewrite(tmp_path: Path) -> None:
    # RAW_PENDING is a pre-promotion sidecar; a postplan plan-rewrite clear-stale
    # must not drop it before step2b_drafter_main can promote against final bytes.
    _write_plan(tmp_path, "## Original\n\ndiff_lines: 1\n")
    raw = tmp_path / design_dialectic.RAW_PENDING
    raw.write_text('{"decisions": []}', encoding="utf-8")
    _write_plan(tmp_path, "## Rewritten\n\ndiff_lines: 1\n")
    assert design_dialectic.clear_stale(tmp_path, reason="plan-rewrite") == 0
    assert raw.exists()


def test_manual_freeform_infers_drafter_pick_from_auto_candidates(tmp_path: Path) -> None:
    _write_plan(tmp_path)
    (tmp_path / "dialectic-clarifier-candidates.json").write_text(json.dumps(_candidate_payload(tmp_path)), encoding="utf-8")
    candidates = design_dialectic._manual_candidates_from_request(
        design=tmp_path,
        request="debate Storage choice: Use SQLite vs Use JSON files",
    )
    assert candidates.decisions[0].drafter_pick == "option_b"


def test_gatec_reuses_manual_digest_without_auto_relaunch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _write_plan(tmp_path)
    payload = _candidate_payload(tmp_path)
    (tmp_path / "dialectic-clarifier-candidates.json").write_text(json.dumps(payload), encoding="utf-8")
    decisions = payload["decisions"]
    assert isinstance(decisions, list)
    manual_payload: dict[str, object] = {
        "plan_fingerprint": payload["plan_fingerprint"],
        "decisions": [decisions[0]],
    }
    (tmp_path / "dialectic-manual-candidates.json").write_text(json.dumps(manual_payload), encoding="utf-8")
    (tmp_path / "dialectic-clarifier-digest.md").write_text("manual-digest\n", encoding="utf-8")
    (tmp_path / design_dialectic.GENERATION_FILE).write_text("2\n", encoding="utf-8")
    (tmp_path / "dialectic-clarifier-status.json").write_text(
        json.dumps(
            {
                "kind": "manual",
                "plan_fingerprint": payload["plan_fingerprint"],
                "ordered_candidate_ids": ["storage-choice"],
                "generation": 2,
                "state": "complete",
            }
        ),
        encoding="utf-8",
    )

    def fail_run(*_args: object, **_kwargs: object) -> tuple[str, bool, list[design_dialectic.DigestRow]]:
        raise AssertionError("auto debate relaunched")

    monkeypatch.setattr(design_dialectic, "_run_debate", fail_run)
    assert design_dialectic.gatec_main(["--design-tmpdir", str(tmp_path)]) == 0
    assert capsys.readouterr().out == "manual-digest\n"


def test_cached_digest_invalid_after_generation_bump(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _write_plan(tmp_path)
    payload = _candidate_payload(tmp_path)
    (tmp_path / "dialectic-clarifier-candidates.json").write_text(json.dumps(payload), encoding="utf-8")
    (tmp_path / "dialectic-clarifier-digest.md").write_text("stale-digest\n", encoding="utf-8")
    (tmp_path / design_dialectic.GENERATION_FILE).write_text("2\n", encoding="utf-8")
    (tmp_path / "dialectic-clarifier-status.json").write_text(
        json.dumps(
            {
                "kind": "auto",
                "plan_fingerprint": payload["plan_fingerprint"],
                "ordered_candidate_ids": ["storage-choice"],
                "generation": 1,
                "state": "complete",
            }
        ),
        encoding="utf-8",
    )

    def fake_debate(*_args: object, **_kwargs: object) -> tuple[str, bool, list[design_dialectic.DigestRow]]:
        return "fresh-digest\n", True, []

    monkeypatch.setattr(design_dialectic, "_run_debate", fake_debate)
    assert design_dialectic.gatec_main(["--design-tmpdir", str(tmp_path)]) == 0
    assert capsys.readouterr().out == "fresh-digest\n"


def test_digest_sanitizes_candidate_derived_fields() -> None:
    row = design_dialectic.DigestRow(
        decision_id="id\ninject",
        title="Title\ninject",
        option_a="A",
        option_b="B",
        option_a_steelman="ok",
        option_b_steelman="ok",
        drafter_pick="LARCH_PLAN_BEGIN",
        panel_lean="KEY=value",
        rationale="ok",
        disposition="voted",
        thesis_votes=1,
        anti_thesis_votes=2,
    )
    digest = design_dialectic._digest_from_rows([row])
    assert "### Decision: Title inject" in digest
    assert "`id inject`" in digest
    assert "\\LARCH_PLAN_BEGIN" in digest
    assert "\\KEY=value" in digest


def test_ballot_strips_attribution_from_steelmen(tmp_path: Path) -> None:
    _write_plan(tmp_path)
    payload = _candidate_payload(tmp_path)
    decisions = tuple(design_dialectic.Candidate(**item) for item in payload["decisions"])  # type: ignore[arg-type]
    candidates = design_dialectic.CandidateSet(plan_fingerprint=str(payload["plan_fingerprint"]), decisions=decisions)
    ballot = design_dialectic._ballot_text(
        candidates=candidates,
        steelmen={(decisions[0].id, "option_a"): "Cursor and Anthropic Sonnet favor SQLite"},
    )
    assert "Cursor" not in ballot
    assert "Anthropic" not in ballot
    assert "Sonnet" not in ballot


def test_parse_judge_votes_dedupes_duplicate_lines(tmp_path: Path) -> None:
    _write_plan(tmp_path)
    payload = _candidate_payload(tmp_path)
    decisions = tuple(design_dialectic.Candidate(**item) for item in payload["decisions"])  # type: ignore[arg-type]
    candidates = design_dialectic.CandidateSet(plan_fingerprint=str(payload["plan_fingerprint"]), decisions=decisions)
    votes = design_dialectic._parse_judge_votes(
        "DECISION_1: THESIS - one\nDECISION_1: THESIS - duplicate\n",
        judge=1,
        candidates=candidates,
    )
    assert len(votes) == 1
    assert votes[0].token == "THESIS"


def test_parse_judge_votes_drops_conflicting_duplicates(tmp_path: Path) -> None:
    _write_plan(tmp_path)
    payload = _candidate_payload(tmp_path)
    decisions = tuple(design_dialectic.Candidate(**item) for item in payload["decisions"])  # type: ignore[arg-type]
    candidates = design_dialectic.CandidateSet(plan_fingerprint=str(payload["plan_fingerprint"]), decisions=decisions)
    votes = design_dialectic._parse_judge_votes(
        "DECISION_1: THESIS - one\nDECISION_1: ANTI_THESIS - conflict\n",
        judge=1,
        candidates=candidates,
    )
    assert votes == []


def test_promote_succeeds_after_postplan_rewrite_clear_stale(tmp_path: Path) -> None:
    # Simulated postplan rewrite + clear-stale must leave RAW_PENDING intact so the
    # subsequent promotion re-keys candidates to the final plan fingerprint.
    _write_plan(tmp_path, "## Original\n\ndiff_lines: 1\n")
    raw = tmp_path / design_dialectic.RAW_PENDING
    raw.write_text(
        json.dumps(
            {
                "decisions": [
                    {
                        "id": "fork",
                        "title": "Fork",
                        "option_a": "A",
                        "option_b": "B",
                        "tradeoff": "Different failure modes",
                        "drafter_pick": "option_a",
                        "why_this_matters": "Operator should see it",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    _write_plan(tmp_path, "## Final\n\ndiff_lines: 1\n")
    design_dialectic.clear_stale(tmp_path, reason="plan-rewrite")
    assert raw.exists()
    assert design_dialectic.promote_candidates(tmp_path) == 0
    promoted = json.loads((tmp_path / design_dialectic.AUTO_CANDIDATES).read_text(encoding="utf-8"))
    assert promoted["plan_fingerprint"] == design_dialectic.plan_fingerprint(tmp_path)
    assert not raw.exists()


def test_manual_freeform_ambiguous_pick_fails_with_shape_help(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # Both option strings appear in the plan, so the current-plan side is ambiguous;
    # the request must fail closed with shape help rather than defaulting to option_a.
    _write_plan(tmp_path, "## Plan\n\nUse SQLite and also Use JSON files here.\n\ndiff_lines: 1\n")
    assert (
        design_dialectic.manual_main(
            ["--design-tmpdir", str(tmp_path), "--request", "debate Storage: Use SQLite vs Use JSON files"]
        )
        == 0
    )
    assert "Use Other as" in capsys.readouterr().out
    assert not (tmp_path / design_dialectic.MANUAL_CANDIDATES).exists()


def test_duplicate_candidate_ids_are_deduped(tmp_path: Path) -> None:
    _write_plan(tmp_path)
    payload = {
        "plan_fingerprint": design_dialectic.plan_fingerprint(tmp_path),
        "decisions": [
            {"id": "storage", "title": "First", "option_a": "A1", "option_b": "B1", "tradeoff": "t1", "drafter_pick": "option_a", "why_this_matters": "w1"},
            {"id": "storage", "title": "Second", "option_a": "A2", "option_b": "B2", "tradeoff": "t2", "drafter_pick": "option_b", "why_this_matters": "w2"},
        ],
    }
    normalized = design_dialectic.validate_candidates_content(
        json.dumps(payload), current_fingerprint=design_dialectic.plan_fingerprint(tmp_path), require_fingerprint=True
    )
    decisions = normalized["decisions"]
    assert isinstance(decisions, list)
    ids = [item["id"] for item in decisions]  # type: ignore[reportUnknownVariableType]
    assert ids[0] == "storage"
    assert len(ids) == len(set(ids)) == 2  # type: ignore[reportUnknownArgumentType]


def test_gatec_prints_manual_digest_when_no_auto_candidates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _write_plan(tmp_path)
    fingerprint = design_dialectic.plan_fingerprint(tmp_path)
    decision = _candidate_payload(tmp_path)["decisions"]
    assert isinstance(decision, list)
    (tmp_path / "dialectic-manual-candidates.json").write_text(
        json.dumps({"plan_fingerprint": fingerprint, "decisions": decision}), encoding="utf-8"
    )
    (tmp_path / "dialectic-clarifier-digest.md").write_text("manual-only-digest\n", encoding="utf-8")
    (tmp_path / design_dialectic.GENERATION_FILE).write_text("3\n", encoding="utf-8")
    (tmp_path / "dialectic-clarifier-status.json").write_text(
        json.dumps(
            {"kind": "manual", "plan_fingerprint": fingerprint, "ordered_candidate_ids": ["storage-choice"], "generation": 3, "state": "complete"}
        ),
        encoding="utf-8",
    )

    def fail_run(*_args: object, **_kwargs: object) -> tuple[str, bool, list[design_dialectic.DigestRow]]:
        raise AssertionError("debate relaunched on manual-only re-entry")

    monkeypatch.setattr(design_dialectic, "_run_debate", fail_run)
    assert design_dialectic.gatec_main(["--design-tmpdir", str(tmp_path)]) == 0
    assert capsys.readouterr().out == "manual-only-digest\n"


def test_manual_cache_does_not_short_circuit_uncovered_auto(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _write_plan(tmp_path)
    fingerprint = design_dialectic.plan_fingerprint(tmp_path)
    auto_payload: dict[str, object] = {
        "plan_fingerprint": fingerprint,
        "decisions": [
            {"id": "storage-choice", "title": "Storage", "option_a": "Use SQLite", "option_b": "Use JSON files", "tradeoff": "t", "drafter_pick": "option_b", "why_this_matters": "w"},
            {"id": "transport-choice", "title": "Transport", "option_a": "Use gRPC", "option_b": "Use REST", "tradeoff": "t2", "drafter_pick": "option_a", "why_this_matters": "w2"},
        ],
    }
    (tmp_path / "dialectic-clarifier-candidates.json").write_text(json.dumps(auto_payload), encoding="utf-8")
    auto_decisions = auto_payload["decisions"]
    assert isinstance(auto_decisions, list)
    # Manual debate only covered one of the two live auto forks.
    (tmp_path / "dialectic-manual-candidates.json").write_text(
        json.dumps({"plan_fingerprint": fingerprint, "decisions": [auto_decisions[0]]}), encoding="utf-8"
    )
    (tmp_path / "dialectic-clarifier-digest.md").write_text("manual-partial\n", encoding="utf-8")
    (tmp_path / design_dialectic.GENERATION_FILE).write_text("4\n", encoding="utf-8")
    (tmp_path / "dialectic-clarifier-status.json").write_text(
        json.dumps(
            {"kind": "manual", "plan_fingerprint": fingerprint, "ordered_candidate_ids": ["storage-choice"], "generation": 4, "state": "complete"}
        ),
        encoding="utf-8",
    )

    def fake_debate(*_args: object, **_kwargs: object) -> tuple[str, bool, list[design_dialectic.DigestRow]]:
        return "auto-fresh-digest\n", True, []

    monkeypatch.setattr(design_dialectic, "_run_debate", fake_debate)
    assert design_dialectic.gatec_main(["--design-tmpdir", str(tmp_path)]) == 0
    assert capsys.readouterr().out == "auto-fresh-digest\n"


def test_fail_open_debate_records_fallback_status(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _write_plan(tmp_path)
    (tmp_path / "dialectic-clarifier-candidates.json").write_text(json.dumps(_candidate_payload(tmp_path)), encoding="utf-8")

    def fail_batch(slots: list[tuple[str, Path, list[str]]], *, deadline: float) -> tuple[dict[str, str], bool]:
        del slots, deadline
        return {}, False

    monkeypatch.setattr(design_dialectic, "_run_slot_batch", fail_batch)
    assert design_dialectic.gatec_main(["--design-tmpdir", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "skipped" in out.lower()
    status = json.loads((tmp_path / design_dialectic.STATUS_FILE).read_text(encoding="utf-8"))
    assert status["state"] == "fallback"
    assert status["generation"] == design_dialectic.read_generation(tmp_path)
    assert not (tmp_path / design_dialectic.DIGEST_FILE).exists()
