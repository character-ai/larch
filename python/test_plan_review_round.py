r"""Coverage for python/plan_review_round.py finding collection and classification.

Regression guard for issue #4790: ``collect_results`` emits ``KEY=VALUE`` blocks,
but ``_compose_findings_from_collector`` parsed ``\x1f``-delimited records, so every
reviewer finding was silently dropped and a real zero-collector round was reported
as a clean ``complete``.
"""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import collect_results
import plan_review_round

if TYPE_CHECKING:
    import pytest


def _collector_text(records: list[collect_results.CollectorRecord]) -> str:
    """Mirror ``collect_results._emit_records``: KEY=VALUE per line, blank line between records."""
    blocks = ["\n".join(rec.fields()) for rec in records]
    return "\n\n".join(blocks) + "\n"


def _write_sidecar(path: Path, rows: list[dict[str, str]]) -> None:
    cols = ["scope", "severity", "focus_area", "location", "what", "scenario_or_breakage", "suggested_fix"]
    lines = ["\t".join(cols)]
    lines.extend("\t".join(row.get(col, "") for col in cols) for row in rows)
    _ = path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_compose_findings_parses_keyvalue_collector(tmp_path: Path) -> None:
    """A KEY=VALUE collector with OK reviewers yields parsed findings (issue #4790)."""
    design = tmp_path
    # Sidecar path differs from the ``{reviewer_file}.tsv`` fallback so the test also
    # proves STRUCTURED_SIDECAR is read by key (its emit order differs from the old
    # positional \x1f unpack, which placed FAILURE_REASON before STRUCTURED_SIDECAR).
    sidecar_in = design / "codex-plan-arch.sidecar.tsv"
    _write_sidecar(
        sidecar_in,
        [
            {
                "scope": "in_scope",
                "severity": "high",
                "focus_area": "correctness",
                "location": "python/x.py:10",
                "what": "Off-by-one in loop bound",
                "scenario_or_breakage": "iterates one element past the end",
                "suggested_fix": "use < instead of <=",
            }
        ],
    )
    sidecar_oos = design / "cursor-plan-pragmatic.sidecar.tsv"
    _write_sidecar(
        sidecar_oos,
        [
            {
                "scope": "out_of_scope",
                "severity": "nit",
                "focus_area": "style",
                "location": "python/y.py:5",
                "what": "Rename ambiguous variable",
                "scenario_or_breakage": "n/a",
                "suggested_fix": "rename tmp to record",
            }
        ],
    )
    records = [
        collect_results.CollectorRecord(
            reviewer_file=str(design / "codex-plan-arch-output.txt"),
            tool="codex",
            status="OK",
            exit_code="0",
            structured_sidecar=str(sidecar_in),
        ),
        collect_results.CollectorRecord(
            reviewer_file=str(design / "cursor-plan-pragmatic-output.txt"),
            tool="cursor",
            status="OK",
            exit_code="0",
            structured_sidecar=str(sidecar_oos),
        ),
    ]
    collect_text = _collector_text(records)
    manifest = design / "plan-review-slots.ndjson"  # absent: slot labels fall back to basename

    in_scope, oos_md, ok_count, fail_count = plan_review_round._compose_findings_from_collector(design, collect_text, manifest)

    assert ok_count == 2
    assert fail_count == 0
    assert "### FINDING_1:" in in_scope
    assert "Off-by-one in loop bound" in in_scope
    assert "### OOS_1:" in oos_md
    assert "Rename ambiguous variable" in oos_md


def test_compose_findings_empty_collector_text(tmp_path: Path) -> None:
    """Empty collector output yields zero OK records and no findings."""
    in_scope, oos_md, ok_count, fail_count = plan_review_round._compose_findings_from_collector(
        tmp_path, "", tmp_path / "plan-review-slots.ndjson"
    )
    assert ok_count == 0
    assert fail_count == 0
    assert in_scope == ""
    assert oos_md == ""


def test_compose_findings_counts_failures_without_dropping_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A non-OK reviewer is counted as a failure while OK reviewers still parse (issue #4790)."""
    # Failure records trigger collector-failure-log composition via _run_cli; stub it so
    # the unit test does not spawn the CLI subprocess.
    monkeypatch.setattr(plan_review_round, "_run_cli", lambda *_a, **_k: None)  # type: ignore[arg-type]
    design = tmp_path
    sidecar_ok = design / "codex-plan-arch.sidecar.tsv"
    _write_sidecar(
        sidecar_ok,
        [
            {
                "scope": "in_scope",
                "severity": "med",
                "focus_area": "correctness",
                "location": "python/z.py:1",
                "what": "Missing nil guard",
                "scenario_or_breakage": "crashes on empty input",
                "suggested_fix": "add guard",
            }
        ],
    )
    records = [
        collect_results.CollectorRecord(
            reviewer_file=str(design / "codex-plan-arch-output.txt"),
            tool="codex",
            status="OK",
            exit_code="0",
            structured_sidecar=str(sidecar_ok),
        ),
        collect_results.CollectorRecord(
            reviewer_file=str(design / "cursor-plan-arch-output.txt"),
            tool="cursor",
            status="TIMEOUT",
            exit_code="124",
            failure_reason="timed out",
        ),
    ]

    in_scope, _oos, ok_count, fail_count = plan_review_round._compose_findings_from_collector(
        design, _collector_text(records), design / "plan-review-slots.ndjson"
    )

    assert ok_count == 1
    assert fail_count == 1
    assert "Missing nil guard" in in_scope


def test_load_manifest_slots_ignores_non_dict_rows(tmp_path: Path) -> None:
    manifest = tmp_path / "plan-review-slots.ndjson"
    _ = manifest.write_text(
        '"scalar"\n{"slot":"cursor-plan-arch","output":"out.txt"}\n["array"]\n',
        encoding="utf-8",
    )

    assert plan_review_round._load_manifest_slots(manifest) == ["cursor-plan-arch"]


def test_compose_findings_tolerates_non_dict_manifest_rows(tmp_path: Path) -> None:
    sidecar = tmp_path / "cursor-plan-arch.sidecar.tsv"
    _write_sidecar(
        sidecar,
        [
            {
                "scope": "in_scope",
                "severity": "high",
                "focus_area": "correctness",
                "location": "python/x.py:10",
                "what": "Preserve mixed manifests",
                "scenario_or_breakage": "non-dict rows used to crash",
                "suggested_fix": "skip non-dict rows",
            }
        ],
    )
    reviewer_file = tmp_path / "cursor-plan-arch-output.txt"
    manifest = tmp_path / "plan-review-slots.ndjson"
    _ = manifest.write_text(
        "\n".join(
            [
                '"scalar"',
                f'{{"slot":"cursor-plan-arch","output":"{reviewer_file}"}}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    records = [
        collect_results.CollectorRecord(
            reviewer_file=str(reviewer_file),
            tool="cursor",
            status="OK",
            exit_code="0",
            structured_sidecar=str(sidecar),
        )
    ]

    in_scope, _oos, ok_count, fail_count = plan_review_round._compose_findings_from_collector(
        tmp_path, _collector_text(records), manifest
    )

    assert ok_count == 1
    assert fail_count == 0
    assert "Preserve mixed manifests" in in_scope


def test_execute_round_propagates_degraded_warning_with_mixed_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design = tmp_path
    plan = design / "plan.txt"
    feature = design / "feature-description.txt"
    _ = plan.write_text("plan\n", encoding="utf-8")
    _ = feature.write_text("feature\n", encoding="utf-8")
    paths = design / "panel-paths.txt"
    reviewer_file = design / "cursor-plan-arch-output.txt"
    sidecar = design / "cursor-plan-arch.sidecar.tsv"
    _write_sidecar(
        sidecar,
        [
            {
                "scope": "in_scope",
                "severity": "nit",
                "focus_area": "correctness",
                "location": "python/x.py:1",
                "what": "Carry degraded warning",
                "scenario_or_breakage": "warning dropped before collection",
                "suggested_fix": "copy panel warning into values",
            }
        ],
    )

    def fake_run_cli(argv: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        _ = env
        if argv[:2] == ["plan-review", "panel-dispatch"]:
            _ = paths.write_text(str(reviewer_file) + "\n", encoding="utf-8")
            _ = (design / "plan-review-slots.ndjson").write_text(
                "\n".join(
                    [
                        '"scalar"',
                        f'{{"slot":"cursor-plan-arch","output":"{reviewer_file}"}}',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(
                argv,
                0,
                f"PANEL_PRUNED_EMPTY=false\nPANEL_PATHS_FILE={paths}\nINVALID_SLOT_PANEL_WARNING=panel degraded\n",
                "",
            )
        if argv[:2] == ["agent", "collect-results"]:
            record = collect_results.CollectorRecord(
                reviewer_file=str(reviewer_file),
                tool="cursor",
                status="OK",
                exit_code="0",
                structured_sidecar=str(sidecar),
            )
            return subprocess.CompletedProcess(argv, 0, _collector_text([record]), "")
        if argv[:2] == ["review", "aggregate-findings"]:
            _ = (design / "ballot.txt").write_text("### FINDING_1:\n", encoding="utf-8")
            return subprocess.CompletedProcess(argv, 0, "REASON=ok\nAGGREGATED=true\n", "")
        if argv[:2] == ["plan-review", "voter-dispatch"]:
            return subprocess.CompletedProcess(
                argv,
                0,
                f"DISPATCH_OK=true\nVOTER_1_PATH={design / 'vote.txt'}\nVOTER_1_TOOL=claude\nVOTER_1_STATUS=launched\n",
                "",
            )
        if argv[:2] == ["plan-review", "tally"]:
            _ = (design / "accepted-plan-findings.md").write_text("", encoding="utf-8")
            return subprocess.CompletedProcess(argv, 0, "TALLY_PLAN_REVIEW_STATUS=ok\n", "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(plan_review_round, "_run_cli", fake_run_cli)

    rc, values = plan_review_round.execute_round(
        design,
        round_num=1,
        prune_round_num=1,
        codex_present="true",
        cursor_present="true",
        plan_file=plan,
        feature_file=feature,
    )

    assert rc == 0
    assert values["INVALID_SLOT_PANEL_WARNING"] == "panel degraded"


def test_parse_collector_records_keyvalue_anchored() -> None:
    """parse_collector_records reads KEY=VALUE blocks by key and ignores leading diagnostics."""
    rec_a = collect_results.CollectorRecord(
        reviewer_file="/d/a-output.txt",
        tool="codex",
        status="OK",
        exit_code="0",
        structured_sidecar="/d/a.tsv",
    )
    rec_b = collect_results.CollectorRecord(
        reviewer_file="/d/b-output.txt",
        tool="cursor",
        status="TIMEOUT",
        exit_code="124",
        failure_reason="timed out",
    )
    body = "\n\n".join("\n".join(rec.fields()) for rec in (rec_a, rec_b)) + "\n"
    # A diagnostic line before the first REVIEWER_FILE anchor must not become a record.
    text = "collect-results: warning: dropping something basename=x.txt\n" + body

    parsed = collect_results.parse_collector_records(text)

    assert len(parsed) == 2
    assert parsed[0]["REVIEWER_FILE"] == "/d/a-output.txt"
    assert parsed[0]["STATUS"] == "OK"
    # Read by key: STRUCTURED_SIDECAR is emitted after EXIT_CODE, the opposite order
    # from the old positional \x1f unpack, so position-based parsing would mis-map it.
    assert parsed[0]["STRUCTURED_SIDECAR"] == "/d/a.tsv"
    assert parsed[1]["TOOL"] == "cursor"
    assert parsed[1]["FAILURE_REASON"] == "timed out"


def test_classify_zero_ok_collector_is_degraded_not_complete() -> None:
    """Secondary defect (issue #4790): a zero-OK round must never report ``complete``.

    Even when the voter panel dispatched fine (``degraded=False``), zero parsed
    collector records means no finding reached the ballot.
    """
    assert (
        plan_review_round._classify_round_loop_status(
            accepted=0, ok_count=0, degraded=False, panel_pruned_empty=False, tally_status="ok"
        )
        == "degraded-empty-collector"
    )


def test_classify_zero_ok_degraded_voter_is_degraded_empty() -> None:
    assert (
        plan_review_round._classify_round_loop_status(
            accepted=0, ok_count=0, degraded=True, panel_pruned_empty=False, tally_status="ok"
        )
        == "degraded-empty-collector"
    )


def test_classify_pruned_empty_panel_is_not_degraded_empty() -> None:
    """An intentionally pruned-empty panel is not the degraded-empty-collector failure."""
    assert (
        plan_review_round._classify_round_loop_status(
            accepted=0, ok_count=0, degraded=False, panel_pruned_empty=True, tally_status="ok"
        )
        == "complete"
    )


def test_classify_complete_when_findings_accepted() -> None:
    assert (
        plan_review_round._classify_round_loop_status(
            accepted=2, ok_count=3, degraded=False, panel_pruned_empty=False, tally_status="ok"
        )
        == "complete"
    )


def test_classify_zero_accepted_with_findings_is_zero_findings_degraded() -> None:
    """Reviewers ran (ok_count>0) but nothing was accepted and the panel degraded."""
    assert (
        plan_review_round._classify_round_loop_status(
            accepted=0, ok_count=4, degraded=True, panel_pruned_empty=False, tally_status="ok"
        )
        == "zero-findings-degraded-panel"
    )


def _install_execute_round_fake(
    monkeypatch: pytest.MonkeyPatch,
    design: Path,
    *,
    tally_status: str = "ok",
    panel_pruned_empty: bool = False,
    empty_collector: bool = False,
) -> None:
    def fake_run_cli(argv: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        del env
        if argv[:2] == ["plan-review", "panel-dispatch"]:
            if panel_pruned_empty:
                return subprocess.CompletedProcess(argv, 0, "PANEL_PRUNED_EMPTY=true\n", "")
            manifest = design / "plan-review-slots.ndjson"
            paths_file = design / "plan-review-panel-paths.txt"
            reviewer_file = design / "cursor-plan-arch-output.txt"
            _ = manifest.write_text(
                '{"slot":"cursor-plan-arch","tool":"cursor","output":"'
                + str(reviewer_file)
                + '","prompt_file":"'
                + str(design / "cursor-plan-arch.prompt")
                + '"}\n',
                encoding="utf-8",
            )
            _ = paths_file.write_text(str(reviewer_file) + "\n", encoding="utf-8")
            return subprocess.CompletedProcess(argv, 0, f"PANEL_PRUNED_EMPTY=false\nPANEL_PATHS_FILE={paths_file}\n", "")
        if argv[:2] == ["agent", "collect-results"]:
            if empty_collector:
                return subprocess.CompletedProcess(argv, 0, "", "")
            sidecar = design / "cursor-plan-arch.sidecar.tsv"
            _write_sidecar(
                sidecar,
                [
                    {
                        "scope": "in_scope",
                        "severity": "high",
                        "focus_area": "correctness",
                        "location": "plan.md",
                        "what": "Missing requirement",
                        "scenario_or_breakage": "plan omits the requirement",
                        "suggested_fix": "add it",
                    }
                ],
            )
            return subprocess.CompletedProcess(
                argv,
                0,
                _collector_text(
                    [
                        collect_results.CollectorRecord(
                            reviewer_file=str(design / "cursor-plan-arch-output.txt"),
                            tool="cursor",
                            status="OK",
                            exit_code="0",
                            structured_sidecar=str(sidecar),
                        )
                    ]
                ),
                "",
            )
        if argv[:2] == ["review", "aggregate-findings"]:
            return subprocess.CompletedProcess(argv, 0, "REASON=ok\nAGGREGATED=true\n", "")
        if argv[:2] == ["plan-review", "voter-dispatch"]:
            return subprocess.CompletedProcess(
                argv,
                0,
                "DISPATCH_OK=true\n"
                f"VOTER_1_PATH={design / 'claude-vote-output.txt'}\n"
                "VOTER_1_TOOL=claude\n"
                "VOTER_1_STATUS=launched\n",
                "",
            )
        if argv[:2] == ["plan-review", "tally"]:
            classification = Path(argv[argv.index("--findings-classification-out") + 1])
            classification.parent.mkdir(parents=True, exist_ok=True)
            if empty_collector:
                _ = classification.write_text(
                    "finding_id\tfinding_reviewers\tvoting_result\n",
                    encoding="utf-8",
                )
            else:
                _ = classification.write_text(
                    "finding_id\tfinding_reviewers\tvoting_result\n"
                    "FINDING_1\tCursor-Arch\taccepted\n",
                    encoding="utf-8",
                )
            if tally_status != "main-agent-vote-required" and not empty_collector:
                _ = (design / "accepted-plan-findings.md").write_text("### FINDING_1:\n", encoding="utf-8")
            return subprocess.CompletedProcess(argv, 0, f"TALLY_PLAN_REVIEW_STATUS={tally_status}\n", "")
        raise AssertionError(f"unexpected argv: {argv}")

    monkeypatch.setattr(plan_review_round, "_run_cli", fake_run_cli)


def test_execute_round_records_plan_review_prune_ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path
    plan_file = design / "plan.txt"
    feature_file = design / "feature.txt"
    _ = plan_file.write_text("plan\n", encoding="utf-8")
    _ = feature_file.write_text("feature\n", encoding="utf-8")
    _install_execute_round_fake(monkeypatch, design)

    rc, values = plan_review_round.execute_round(
        design,
        round_num=1,
        prune_round_num=1,
        codex_present="false",
        cursor_present="true",
        plan_file=plan_file,
        feature_file=feature_file,
    )

    assert rc == 0
    assert values["LOOP_STATUS"] == "complete"
    assert (design / "plan-review-prune-label-map.tsv").read_text(encoding="utf-8") == "cursor-plan-arch\tCursor-Arch\n"
    ledger_lines = (design / "reviewer-prune-ledger.tsv").read_text(encoding="utf-8").splitlines()
    assert ledger_lines[0] == "round\ttool\tslot\tlabel\taccepted_count\trejected_count\ttotal_count"
    assert ledger_lines[1] == "1\tcursor\tcursor-plan-arch\tCursor-Arch\t1\t0\t1"


def test_execute_round_pruned_empty_does_not_record_prune_ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    plan_file = tmp_path / "plan.txt"
    feature_file = tmp_path / "feature.txt"
    _ = plan_file.write_text("plan\n", encoding="utf-8")
    _ = feature_file.write_text("feature\n", encoding="utf-8")
    _install_execute_round_fake(monkeypatch, tmp_path, panel_pruned_empty=True)

    rc, values = plan_review_round.execute_round(
        tmp_path,
        round_num=3,
        prune_round_num=3,
        codex_present="false",
        cursor_present="true",
        plan_file=plan_file,
        feature_file=feature_file,
    )

    assert rc == 0
    assert values["PANEL_PRUNED_EMPTY"] == "true"
    assert not (tmp_path / "reviewer-prune-ledger.tsv").exists()


def test_execute_round_main_agent_vote_required_does_not_record_prune_ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    plan_file = tmp_path / "plan.txt"
    feature_file = tmp_path / "feature.txt"
    _ = plan_file.write_text("plan\n", encoding="utf-8")
    _ = feature_file.write_text("feature\n", encoding="utf-8")
    _install_execute_round_fake(monkeypatch, tmp_path, tally_status="main-agent-vote-required")

    rc, values = plan_review_round.execute_round(
        tmp_path,
        round_num=1,
        prune_round_num=1,
        codex_present="false",
        cursor_present="true",
        plan_file=plan_file,
        feature_file=feature_file,
    )

    assert rc == 0
    assert values["LOOP_STATUS"] == "main-agent-vote-required"
    assert not (tmp_path / "reviewer-prune-ledger.tsv").exists()


def test_execute_round_degraded_empty_collector_records_prune_ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    plan_file = tmp_path / "plan.txt"
    feature_file = tmp_path / "feature.txt"
    _ = plan_file.write_text("plan\n", encoding="utf-8")
    _ = feature_file.write_text("feature\n", encoding="utf-8")
    _install_execute_round_fake(monkeypatch, tmp_path, empty_collector=True)

    rc, values = plan_review_round.execute_round(
        tmp_path,
        round_num=2,
        prune_round_num=2,
        codex_present="false",
        cursor_present="true",
        plan_file=plan_file,
        feature_file=feature_file,
    )

    assert rc == 0
    assert values["LOOP_STATUS"] == "degraded-empty-collector"
    ledger_lines = (tmp_path / "reviewer-prune-ledger.tsv").read_text(encoding="utf-8").splitlines()
    assert ledger_lines[0] == "round\ttool\tslot\tlabel\taccepted_count\trejected_count\ttotal_count"
    assert ledger_lines[1] == "2\tcursor\tcursor-plan-arch\tCursor-Arch\t0\t0\t0"
