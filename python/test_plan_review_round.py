r"""Coverage for python/plan_review_round.py finding collection and classification.

Regression guard for issue #4790: ``collect_results`` emits ``KEY=VALUE`` blocks,
but ``_compose_findings_from_collector`` parsed ``\x1f``-delimited records, so every
reviewer finding was silently dropped and a real zero-collector round was reported
as a clean ``complete``.
"""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from larch.agents import collect_results
from larch.review import plan_review_round
from larch.review import review_aggregate
from test_support import make_zero_findings_plan_review_fake_cli

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

    in_scope, oos_md, ok_count, fail_count = plan_review_round._compose_findings_from_collector(design=design, collect_text=collect_text, manifest=manifest)

    assert ok_count == 2
    assert fail_count == 0
    assert "### FINDING_1:" in in_scope
    assert "Off-by-one in loop bound" in in_scope
    assert "### OOS_1:" in oos_md
    assert "Rename ambiguous variable" in oos_md


def test_compose_findings_caps_oos_per_manifest_slot_and_keeps_later_in_scope(tmp_path: Path) -> None:
    design = tmp_path
    reviewer_a = design / "codex-plan-arch-output.txt"
    reviewer_b = design / "cursor-plan-arch-output.txt"
    sidecar_a = design / "codex-plan-arch.sidecar.tsv"
    sidecar_b = design / "cursor-plan-arch.sidecar.tsv"
    _write_sidecar(
        sidecar_a,
        [
            {
                "scope": "out_of_scope",
                "severity": "nit",
                "focus_area": "architecture",
                "location": f"python/a.py:{idx}",
                "what": f"Reviewer A OOS {idx}",
                "scenario_or_breakage": "future backlog item",
                "suggested_fix": "track later",
            }
            for idx in range(1, 5)
        ]
        + [
            {
                "scope": "in_scope",
                "severity": "important",
                "focus_area": "correctness",
                "location": "python/a.py:99",
                "what": "Reviewer A later in-scope row",
                "scenario_or_breakage": "post-overflow row still matters",
                "suggested_fix": "keep processing rows",
            }
        ],
    )
    _write_sidecar(
        sidecar_b,
        [
            {
                "scope": "out_of_scope",
                "severity": "nit",
                "focus_area": "risk-integration",
                "location": "python/b.py:1",
                "what": "Reviewer B independent OOS",
                "scenario_or_breakage": "separate reviewer allowance",
                "suggested_fix": "track separately",
            }
        ],
    )
    manifest = design / "plan-review-slots.ndjson"
    _ = manifest.write_text(
        f'{{"slot":"codex-plan-arch","tool":"codex","output":"{reviewer_a}","prompt_file":"prompt-a.md"}}\n'
        f'{{"slot":"cursor-plan-arch","tool":"cursor","output":"{reviewer_b}","prompt_file":"prompt-b.md"}}\n',
        encoding="utf-8",
    )
    records = [
        collect_results.CollectorRecord(
            reviewer_file=str(reviewer_a),
            tool="codex",
            status="OK",
            exit_code="0",
            structured_sidecar=str(sidecar_a),
        ),
        collect_results.CollectorRecord(
            reviewer_file=str(reviewer_b),
            tool="cursor",
            status="OK",
            exit_code="0",
            structured_sidecar=str(sidecar_b),
        ),
    ]

    in_scope, oos_md, ok_count, fail_count = plan_review_round._compose_findings_from_collector(
        design=design, collect_text=_collector_text(records), manifest=manifest
    )

    assert ok_count == 2
    assert fail_count == 0
    assert "Reviewer A OOS 1" in oos_md
    assert "Reviewer A OOS 2" in oos_md
    assert "Reviewer A OOS 3" in oos_md
    assert "Reviewer A OOS 4" not in oos_md
    assert "Reviewer A later in-scope row" in in_scope
    assert "Reviewer B independent OOS" in oos_md
    assert [int(value) for value in re.findall(r"### OOS_(\d+):", oos_md)] == [1, 2, 3, 4]
    assert [int(value) for value in re.findall(r"### FINDING_(\d+):", in_scope)] == [1]


def test_compose_findings_empty_collector_text(tmp_path: Path) -> None:
    """Empty collector output yields zero OK records and no findings."""
    in_scope, oos_md, ok_count, fail_count = plan_review_round._compose_findings_from_collector(
        design=tmp_path, collect_text="", manifest=tmp_path / "plan-review-slots.ndjson"
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
        design=design, collect_text=_collector_text(records), manifest=design / "plan-review-slots.ndjson"
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
        design=tmp_path, collect_text=_collector_text(records), manifest=manifest
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
        design=design,
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
    panel_dispatch_failed: bool = False,
    empty_collector: bool = False,
    collect_failed: bool = False,
    empty_paths: bool = False,
    aggregator_fail: bool = False,
) -> None:
    def fake_run_cli(argv: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        del env
        if argv[:2] == ["plan-review", "panel-dispatch"]:
            if panel_dispatch_failed:
                return subprocess.CompletedProcess(argv, 7, "", "panel waterfall failed\n")
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
            if empty_paths:
                _ = paths_file.write_text("", encoding="utf-8")
            else:
                _ = paths_file.write_text(str(reviewer_file) + "\n", encoding="utf-8")
            return subprocess.CompletedProcess(argv, 0, f"PANEL_PRUNED_EMPTY=false\nPANEL_PATHS_FILE={paths_file}\n", "")
        if argv[:2] == ["agent", "collect-results"]:
            if collect_failed:
                return subprocess.CompletedProcess(argv, 1, "not-parseable-collector-output\n", "")
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
            if aggregator_fail:
                _ = (design / "aggregator-validate.stderr").write_text(
                    "input reviewers missing from merge output: ['Cursor-Arch']\n",
                    encoding="utf-8",
                )
                _ = (design / "aggregator-output.txt").write_text(
                    "### FINDING_1: bad merge\n", encoding="utf-8"
                )
                return subprocess.CompletedProcess(argv, 0, "REASON=validation-failed\nAGGREGATED=false\n", "")
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
        design=design,
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
    assert ledger_lines[0] == "round\ttool\tslot\tlabel\taccepted_count\tweighted_accepted_count\trejected_count\ttotal_count"
    assert ledger_lines[1] == "1\tcursor\tcursor-plan-arch\tCursor-Arch\t1\t1\t0\t1"


def test_execute_round_snapshots_aggregator_forensics_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An aggregator validation failure mirrors its forensics into plan-review/round-N/ so a later
    round's success cannot clobber the early-round evidence at the stable top-level path (#4996).
    """
    design = tmp_path
    plan_file = design / "plan.txt"
    feature_file = design / "feature.txt"
    _ = plan_file.write_text("plan\n", encoding="utf-8")
    _ = feature_file.write_text("feature\n", encoding="utf-8")
    _install_execute_round_fake(monkeypatch, design, aggregator_fail=True)

    rc, values = plan_review_round.execute_round(
        design=design,
        round_num=1,
        prune_round_num=1,
        codex_present="false",
        cursor_present="true",
        plan_file=plan_file,
        feature_file=feature_file,
    )

    assert rc == 0
    assert values["AGGREGATOR_STATUS"] == "validation-failed"
    snapshot = design / "plan-review" / "round-1" / "aggregator-validate.stderr"
    assert snapshot.is_file()
    assert "input reviewers missing from merge output" in snapshot.read_text(encoding="utf-8")
    assert (design / "plan-review" / "round-1" / "aggregator-output.txt").is_file()

    # Emulate a later round overwriting the stable top-level path; the round-1 snapshot survives.
    _ = (design / "aggregator-validate.stderr").write_text("", encoding="utf-8")
    assert snapshot.read_text(encoding="utf-8") != ""


def test_aggregator_forensic_snapshot_covers_round_stamped_pointers() -> None:
    """Every basename review_aggregate round-stamps into a committed "See plan-review/round-N/..." pointer
    must be snapshotted into that directory, or the pointer dangles after a later round clobbers the stable
    top-level path (#4996/#5004). The snapshot list is sourced from the round-stamped set, so this guards
    against the two cross-module lists drifting apart again.
    """
    round_stamped = set(review_aggregate.ROUND_STAMPED_FORENSICS)
    snapshotted = set(plan_review_round._AGGREGATOR_FORENSIC_FILES)
    assert round_stamped <= snapshotted


def test_execute_round_panel_dispatch_failed_syncs_latest_reviewer_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """panel-dispatch failure refreshes latest-reviewer-status.tsv (#4848)."""
    plan_file = tmp_path / "plan.txt"
    feature_file = tmp_path / "feature.txt"
    _ = plan_file.write_text("plan\n", encoding="utf-8")
    _ = feature_file.write_text("feature\n", encoding="utf-8")
    stale_latest = tmp_path / "latest-reviewer-status.tsv"
    _ = stale_latest.write_text("slot\tstatus\telapsed\nStale\tskipped\t\n", encoding="utf-8")
    reviewer_file = tmp_path / "cursor-plan-arch-output.txt"
    _ = (tmp_path / "plan-review-slots.ndjson").write_text(
        '{"slot":"cursor-plan-arch","tool":"cursor","output":"'
        + str(reviewer_file)
        + '","prompt_file":"'
        + str(tmp_path / "cursor-plan-arch.prompt")
        + '"}\n',
        encoding="utf-8",
    )
    _install_execute_round_fake(monkeypatch, tmp_path, panel_dispatch_failed=True)

    rc, values = plan_review_round.execute_round(
        design=tmp_path,
        round_num=2,
        prune_round_num=2,
        codex_present="false",
        cursor_present="true",
        plan_file=plan_file,
        feature_file=feature_file,
    )

    assert rc == 7
    assert values["LOOP_STATUS"] == "panel-failed"
    round_status = tmp_path / "plan-review" / "round-2" / "reviewer-status.tsv"
    assert round_status.is_file()
    assert stale_latest.read_text(encoding="utf-8") == round_status.read_text(encoding="utf-8")
    assert "Stale" not in stale_latest.read_text(encoding="utf-8")
    assert round_status.read_text(encoding="utf-8").splitlines()[1] == "Cursor-Arch\tskipped\t"


def test_execute_round_collect_failed_syncs_latest_reviewer_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """collect-results failure with unparseable output still refreshes reviewer-status.tsv (#4848)."""
    plan_file = tmp_path / "plan.txt"
    feature_file = tmp_path / "feature.txt"
    _ = plan_file.write_text("plan\n", encoding="utf-8")
    _ = feature_file.write_text("feature\n", encoding="utf-8")
    stale_latest = tmp_path / "latest-reviewer-status.tsv"
    _ = stale_latest.write_text("slot\tstatus\telapsed\nStale\tskipped\t\n", encoding="utf-8")
    _install_execute_round_fake(monkeypatch, tmp_path, collect_failed=True)

    rc, values = plan_review_round.execute_round(
        design=tmp_path,
        round_num=2,
        prune_round_num=2,
        codex_present="false",
        cursor_present="true",
        plan_file=plan_file,
        feature_file=feature_file,
    )

    assert rc == 1
    assert values["LOOP_STATUS"] == "panel-failed"
    round_status = tmp_path / "plan-review" / "round-2" / "reviewer-status.tsv"
    assert round_status.is_file()
    assert stale_latest.read_text(encoding="utf-8") == round_status.read_text(encoding="utf-8")
    assert "Stale" not in stale_latest.read_text(encoding="utf-8")
    assert round_status.read_text(encoding="utf-8").splitlines()[1] == "Cursor-Arch\tskipped\t"


def test_execute_round_pruned_empty_syncs_latest_reviewer_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PANEL_PRUNED_EMPTY clears stale latest-reviewer-status.tsv (#4848)."""
    plan_file = tmp_path / "plan.txt"
    feature_file = tmp_path / "feature.txt"
    _ = plan_file.write_text("plan\n", encoding="utf-8")
    _ = feature_file.write_text("feature\n", encoding="utf-8")
    stale_latest = tmp_path / "latest-reviewer-status.tsv"
    _ = stale_latest.write_text("slot\tstatus\telapsed\nStale\tskipped\t\n", encoding="utf-8")
    _install_execute_round_fake(monkeypatch, tmp_path, panel_pruned_empty=True)

    rc, values = plan_review_round.execute_round(
        design=tmp_path,
        round_num=3,
        prune_round_num=3,
        codex_present="false",
        cursor_present="true",
        plan_file=plan_file,
        feature_file=feature_file,
    )

    assert rc == 0
    assert values["PANEL_PRUNED_EMPTY"] == "true"
    round_status = tmp_path / "plan-review" / "round-3" / "reviewer-status.tsv"
    assert round_status.is_file()
    assert round_status.read_text(encoding="utf-8") == "slot\tstatus\telapsed\n"
    assert stale_latest.read_text(encoding="utf-8") == "slot\tstatus\telapsed\n"
    assert "Stale" not in stale_latest.read_text(encoding="utf-8")


def test_execute_round_pruned_empty_does_not_record_prune_ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    plan_file = tmp_path / "plan.txt"
    feature_file = tmp_path / "feature.txt"
    _ = plan_file.write_text("plan\n", encoding="utf-8")
    _ = feature_file.write_text("feature\n", encoding="utf-8")
    _install_execute_round_fake(monkeypatch, tmp_path, panel_pruned_empty=True)

    rc, values = plan_review_round.execute_round(
        design=tmp_path,
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
        design=tmp_path,
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
        design=tmp_path,
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
    assert ledger_lines[0] == "round\ttool\tslot\tlabel\taccepted_count\tweighted_accepted_count\trejected_count\ttotal_count"
    assert ledger_lines[1] == "2\tcursor\tcursor-plan-arch\tCursor-Arch\t0\t0\t0\t0"


def test_execute_round_writes_reviewer_status_tsv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A settled round materializes round-N/reviewer-status.tsv and copies it to
    latest-reviewer-status.tsv, one row per launched slot (issue #4848).

    The producer is the missing half of the SKILL.md Step 3 post-notification
    reviewer-status table: consumers only ever copied this file, so before the fix it
    was never created and the table could not render.
    """
    plan_file = tmp_path / "plan.txt"
    feature_file = tmp_path / "feature.txt"
    _ = plan_file.write_text("plan\n", encoding="utf-8")
    _ = feature_file.write_text("feature\n", encoding="utf-8")
    _install_execute_round_fake(monkeypatch, tmp_path)

    rc, values = plan_review_round.execute_round(
        design=tmp_path,
        round_num=1,
        prune_round_num=1,
        codex_present="false",
        cursor_present="true",
        plan_file=plan_file,
        feature_file=feature_file,
    )

    assert rc == 0
    assert values["LOOP_STATUS"] == "complete"
    round_status = tmp_path / "plan-review" / "round-1" / "reviewer-status.tsv"
    latest = tmp_path / "latest-reviewer-status.tsv"
    assert round_status.is_file()
    assert latest.is_file()
    assert round_status.read_text(encoding="utf-8") == latest.read_text(encoding="utf-8")
    lines = round_status.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "slot\tstatus\telapsed"
    # One row per launched slot (the fake launches exactly cursor-plan-arch, STATUS=OK).
    assert lines[1] == "Cursor-Arch\tdone\t"
    assert len(lines) == 2


def test_write_reviewer_status_tsv_maps_status_per_slot(tmp_path: Path) -> None:
    """write_reviewer_status_tsv joins the launched-slot manifest to collector status:
    ``OK`` -> ``done``, any other collected status -> ``failed``, no record -> ``skipped``
    (issue #4848).
    """
    design = tmp_path
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    arch = round_dir / "cursor-plan-arch-output.txt"
    innovation = round_dir / "codex-primary-plan-innovation-output.txt"
    pragmatic = round_dir / "cursor-plan-pragmatic-output.txt"
    rows = [
        {"tool": "cursor", "slot": "cursor-plan-arch", "output": str(arch), "prompt_file": str(design / "p1")},
        {"tool": "codex", "slot": "codex-plan-innovation", "output": str(innovation), "prompt_file": str(design / "p2")},
        {"tool": "cursor", "slot": "cursor-plan-pragmatic", "output": str(pragmatic), "prompt_file": str(design / "p3")},
    ]
    _ = (design / "plan-review-slots.ndjson").write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    _ = (design / "collector-results.env").write_text(
        _collector_text(
            [
                collect_results.CollectorRecord(reviewer_file=str(arch), tool="cursor", status="OK", exit_code="0"),
                collect_results.CollectorRecord(reviewer_file=str(innovation), tool="codex", status="EMPTY_OUTPUT", exit_code="4"),
            ]
        ),
        encoding="utf-8",
    )
    latest = design / "latest-reviewer-status.tsv"
    latest.symlink_to(design / "blocked-latest.tsv")

    out = plan_review_round.write_reviewer_status_tsv(design=design, round_num=1)

    assert out == round_dir / "reviewer-status.tsv"
    assert out is not None
    assert out.read_text(encoding="utf-8").splitlines() == [
        "slot\tstatus\telapsed",
        "Cursor-Arch\tdone\t",
        "Codex-Innovation\tfailed\t",
        "Cursor-Pragmatic\tskipped\t",
    ]
    round_table = round_dir / "reviewer-status-table.txt"
    stable_table = design / "reviewer-status-table.txt"
    assert round_table.is_file()
    assert stable_table.is_file()
    assert round_table.read_text(encoding="utf-8") == stable_table.read_text(encoding="utf-8")
    assert stable_table.read_text(encoding="utf-8").strip() == (
        "📊 Reviewers: | Cursor-Arch: ✅ | Codex-Innovation: ❌ | Cursor-Pragmatic: ⊘ |"
    )
    assert latest.is_symlink()


def test_render_reviewer_status_table_maps_icons_and_elapsed(tmp_path: Path) -> None:
    status = tmp_path / "reviewer-status.tsv"
    _ = status.write_text(
        "slot\tstatus\telapsed\n"
        "Cursor-Arch\tdone\t4m12s\n"
        "Cursor-Innovation\tpending\t\n"
        "Cursor-Pragmatic\tin-progress\t1m00s\n"
        "Cursor-Requirements\tfailed\t8m03s\n"
        "Codex-Arch\ttimeout\t6m15s\n"
        "Codex-Innovation\tskipped\t\n"
        "Codex-Pragmatic\tmystery\t9m09s\n",
        encoding="utf-8",
    )

    assert plan_review_round.render_reviewer_status_table(status) == (
        "📊 Reviewers: | Cursor-Arch: ✅ 4m12s | Cursor-Innovation: ⏳ | "
        "Cursor-Pragmatic: ⏳ 1m00s | Cursor-Requirements: ❌ 8m03s | "
        "Codex-Arch: ❌ 6m15s | Codex-Innovation: ⊘ | Codex-Pragmatic: ❌ 9m09s |"
    )


def test_render_reviewer_status_table_returns_none_for_empty_or_malformed(tmp_path: Path) -> None:
    missing = tmp_path / "missing.tsv"
    assert plan_review_round.render_reviewer_status_table(missing) is None
    header_only = tmp_path / "header.tsv"
    _ = header_only.write_text("slot\tstatus\telapsed\n", encoding="utf-8")
    assert plan_review_round.render_reviewer_status_table(header_only) is None
    empty_slot = tmp_path / "empty-slot.tsv"
    _ = empty_slot.write_text("slot\tstatus\telapsed\n\tdone\t1m\n", encoding="utf-8")
    assert plan_review_round.render_reviewer_status_table(empty_slot) is None
    linked = tmp_path / "linked.tsv"
    linked.symlink_to(header_only)
    assert plan_review_round.render_reviewer_status_table(linked) is None
    slot_only = tmp_path / "slot-only.tsv"
    _ = slot_only.write_text("slot\nCursor-Arch\n", encoding="utf-8")
    assert plan_review_round.render_reviewer_status_table(slot_only) is None


def test_render_reviewer_status_table_skipped_omits_elapsed(tmp_path: Path) -> None:
    status = tmp_path / "reviewer-status.tsv"
    _ = status.write_text("slot\tstatus\telapsed\nCodex-Arch\tskipped\t2m\n", encoding="utf-8")
    assert plan_review_round.render_reviewer_status_table(status) == "📊 Reviewers: | Codex-Arch: ⊘ |"


def test_header_only_reviewer_status_fallback_clears_stale_table(tmp_path: Path) -> None:
    stale = tmp_path / "reviewer-status-table.txt"
    _ = stale.write_text("stale\n", encoding="utf-8")

    plan_review_round._write_header_only_reviewer_status_fallback(design=tmp_path, round_num=1)

    assert not stale.exists()
    assert not (tmp_path / "plan-review" / "round-1" / "reviewer-status-table.txt").exists()


def test_try_write_reviewer_status_tsv_terminal_none_clears_stale_table(tmp_path: Path) -> None:
    stale = tmp_path / "reviewer-status-table.txt"
    _ = stale.write_text("stale\n", encoding="utf-8")

    assert plan_review_round.try_write_reviewer_status_tsv(design=tmp_path, round_num=1) is None

    assert not stale.exists()


def test_failed_header_fallback_clears_stale_table(tmp_path: Path) -> None:
    stale = tmp_path / "reviewer-status-table.txt"
    _ = stale.write_text("stale\n", encoding="utf-8")
    round_dir = tmp_path / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    target = tmp_path / "blocked.tsv"
    _ = target.write_text("slot\tstatus\telapsed\nCursor-Arch\tdone\t\n", encoding="utf-8")
    (round_dir / "reviewer-status.tsv").symlink_to(target)

    assert plan_review_round.try_write_reviewer_status_tsv(design=tmp_path, round_num=1, header_fallback=True) is None

    assert not stale.exists()


def test_materialize_stable_reviewer_status_table_binds_env_and_prefers_explicit_round(tmp_path: Path) -> None:
    round1 = tmp_path / "plan-review" / "round-1"
    round2 = tmp_path / "plan-review" / "round-2"
    round1.mkdir(parents=True)
    round2.mkdir(parents=True)
    _ = (round1 / "reviewer-status.tsv").write_text("slot\tstatus\telapsed\nCursor-Arch\tdone\t\n", encoding="utf-8")
    _ = (round2 / "reviewer-status.tsv").write_text("slot\tstatus\telapsed\nCodex-Arch\tfailed\t2m\n", encoding="utf-8")
    _ = (tmp_path / ".step3-review-result.env").write_text("FINAL_ROUND_NUM=1\nROUNDS_COMPLETED=2\n", encoding="utf-8")

    assert plan_review_round.materialize_stable_reviewer_status_table(design=tmp_path)
    assert (tmp_path / "reviewer-status-table.txt").read_text(encoding="utf-8").strip() == "📊 Reviewers: | Cursor-Arch: ✅ |"

    assert plan_review_round.materialize_stable_reviewer_status_table(design=tmp_path, round_num=2)
    assert (tmp_path / "reviewer-status-table.txt").read_text(encoding="utf-8").strip() == "📊 Reviewers: | Codex-Arch: ❌ 2m |"


def test_materialize_stable_reviewer_status_table_early_exit_clears_stale_stable(tmp_path: Path) -> None:
    stale = tmp_path / "reviewer-status-table.txt"
    _ = stale.write_text("📊 Reviewers: | Cursor-Old: ✅ |\n", encoding="utf-8")

    assert not plan_review_round.materialize_stable_reviewer_status_table(design=tmp_path, round_num=99)

    assert not stale.exists()


def test_reviewer_status_table_destination_symlink_is_replaced_on_explicit_round(tmp_path: Path) -> None:
    round_dir = tmp_path / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    _ = (round_dir / "reviewer-status.tsv").write_text("slot\tstatus\telapsed\nCursor-Arch\tdone\t\n", encoding="utf-8")
    stable = tmp_path / "reviewer-status-table.txt"
    stable.symlink_to(tmp_path / "target.txt")

    assert plan_review_round.materialize_stable_reviewer_status_table(design=tmp_path, round_num=1)

    assert stable.is_file()
    assert not stable.is_symlink()
    assert stable.read_text(encoding="utf-8").strip() == "📊 Reviewers: | Cursor-Arch: ✅ |"


def test_reviewer_status_table_write_oserror_clears_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    round_dir = tmp_path / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    status = round_dir / "reviewer-status.tsv"
    _ = status.write_text("slot\tstatus\telapsed\nCursor-Arch\tdone\t\n", encoding="utf-8")

    def missing_stable_table(_design: Path) -> Path:
        return tmp_path / "missing-parent" / "reviewer-status-table.txt"

    logged: list[str] = []

    def record_failure(**kwargs: object) -> None:
        logged.append(f"{kwargs['tool']}:{type(kwargs['exc']).__name__}")

    monkeypatch.setattr(plan_review_round, "_stable_reviewer_status_table_path", missing_stable_table)
    monkeypatch.setattr(plan_review_round, "_log_reviewer_status_failure", record_failure)

    assert not plan_review_round.materialize_stable_reviewer_status_table(design=tmp_path, round_num=1)

    assert not (round_dir / "reviewer-status-table.txt").exists()
    assert logged == ["write_reviewer_status_table:FileNotFoundError"]


def test_write_reviewer_status_tsv_no_manifest_returns_none(tmp_path: Path) -> None:
    """No launched-slot manifest -> nothing to render, returns None (issue #4848)."""
    assert plan_review_round.write_reviewer_status_tsv(design=tmp_path, round_num=1) is None


def test_write_reviewer_status_tsv_retry_path_maps_to_done(tmp_path: Path) -> None:
    """Collector retry paths join to manifest phase-1 output paths (issue #4848)."""
    design = tmp_path
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    manifest_output = round_dir / "cursor-plan-arch-output.txt"
    retry_output = round_dir / "cursor-plan-arch-output-retry.txt"
    rows = [
        {
            "tool": "cursor",
            "slot": "cursor-plan-arch",
            "output": str(manifest_output),
            "prompt_file": str(design / "p1"),
        }
    ]
    _ = (design / "plan-review-slots.ndjson").write_text(json.dumps(rows[0]) + "\n", encoding="utf-8")
    _ = (design / "collector-results.env").write_text(
        _collector_text(
            [
                collect_results.CollectorRecord(
                    reviewer_file=str(retry_output),
                    tool="cursor",
                    status="OK",
                    exit_code="0",
                )
            ]
        ),
        encoding="utf-8",
    )

    out = plan_review_round.write_reviewer_status_tsv(design=design, round_num=1)

    assert out is not None
    assert out.read_text(encoding="utf-8").splitlines() == [
        "slot\tstatus\telapsed",
        "Cursor-Arch\tdone\t",
    ]
    latest = design / "latest-reviewer-status.tsv"
    assert latest.is_file()
    assert latest.read_text(encoding="utf-8") == out.read_text(encoding="utf-8")


def test_write_reviewer_status_tsv_phase3_path_maps_to_done(tmp_path: Path) -> None:
    """Collector waterfall phase-3 paths join to manifest phase-1 output paths (issue #4848)."""
    design = tmp_path
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    manifest_output = round_dir / "cursor-plan-arch-output.txt"
    phase3_output = round_dir / "cursor-plan-arch-output-phase3.txt"
    rows = [
        {
            "tool": "cursor",
            "slot": "cursor-plan-arch",
            "output": str(manifest_output),
            "prompt_file": str(design / "p1"),
        }
    ]
    _ = (design / "plan-review-slots.ndjson").write_text(json.dumps(rows[0]) + "\n", encoding="utf-8")
    _ = (design / "collector-results.env").write_text(
        _collector_text(
            [
                collect_results.CollectorRecord(
                    reviewer_file=str(phase3_output),
                    tool="cursor",
                    status="OK",
                    exit_code="0",
                )
            ]
        ),
        encoding="utf-8",
    )

    out = plan_review_round.write_reviewer_status_tsv(design=design, round_num=1)

    assert out is not None
    assert out.read_text(encoding="utf-8").splitlines()[1] == "Cursor-Arch\tdone\t"


def test_write_reviewer_status_tsv_collect_text_overrides_stale_collector_file(tmp_path: Path) -> None:
    """In-memory collect_text wins over a stale on-disk collector-results.env (#4848)."""
    design = tmp_path
    round_dir = design / "plan-review" / "round-2"
    round_dir.mkdir(parents=True)
    arch = round_dir / "cursor-plan-arch-output.txt"
    rows = [
        {"tool": "cursor", "slot": "cursor-plan-arch", "output": str(arch), "prompt_file": str(design / "p1")},
    ]
    _ = (design / "plan-review-slots.ndjson").write_text(json.dumps(rows[0]) + "\n", encoding="utf-8")
    _ = (design / "collector-results.env").write_text(
        _collector_text(
            [
                collect_results.CollectorRecord(
                    reviewer_file=str(arch),
                    tool="cursor",
                    status="OK",
                    exit_code="0",
                )
            ]
        ),
        encoding="utf-8",
    )

    out = plan_review_round.write_reviewer_status_tsv(design=design, round_num=2, collect_text="")

    assert out is not None
    assert out.read_text(encoding="utf-8").splitlines()[1] == "Cursor-Arch\tskipped\t"


def test_write_reviewer_status_tsv_basename_collision_prefers_ok(tmp_path: Path) -> None:
    """Normalized basename collisions prefer OK over non-OK collector statuses (#4848)."""
    design = tmp_path
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    manifest_output = round_dir / "cursor-plan-arch-output.txt"
    retry_output = round_dir / "cursor-plan-arch-output-retry.txt"
    rows = [
        {
            "tool": "cursor",
            "slot": "cursor-plan-arch",
            "output": str(manifest_output),
            "prompt_file": str(design / "p1"),
        }
    ]
    _ = (design / "plan-review-slots.ndjson").write_text(json.dumps(rows[0]) + "\n", encoding="utf-8")
    for records in (
        [
            collect_results.CollectorRecord(reviewer_file=str(manifest_output), tool="cursor", status="EMPTY_OUTPUT", exit_code="4"),
            collect_results.CollectorRecord(reviewer_file=str(retry_output), tool="cursor", status="OK", exit_code="0"),
        ],
        [
            collect_results.CollectorRecord(reviewer_file=str(retry_output), tool="cursor", status="OK", exit_code="0"),
            collect_results.CollectorRecord(reviewer_file=str(manifest_output), tool="cursor", status="EMPTY_OUTPUT", exit_code="4"),
        ],
    ):
        _ = (design / "collector-results.env").write_text(_collector_text(records), encoding="utf-8")
        out = plan_review_round.write_reviewer_status_tsv(design=design, round_num=1)
        assert out is not None
        assert out.read_text(encoding="utf-8").splitlines()[1] == "Cursor-Arch\tdone\t"


def test_execute_round_empty_paths_clears_stale_collector_for_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Skipped collection must not reuse a prior round's collector-results.env (#4848)."""
    plan_file = tmp_path / "plan.txt"
    feature_file = tmp_path / "feature.txt"
    _ = plan_file.write_text("plan\n", encoding="utf-8")
    _ = feature_file.write_text("feature\n", encoding="utf-8")
    reviewer_file = tmp_path / "cursor-plan-arch-output.txt"
    _ = (tmp_path / "collector-results.env").write_text(
        _collector_text(
            [
                collect_results.CollectorRecord(
                    reviewer_file=str(reviewer_file),
                    tool="cursor",
                    status="OK",
                    exit_code="0",
                )
            ]
        ),
        encoding="utf-8",
    )
    _install_execute_round_fake(monkeypatch, tmp_path, empty_paths=True, empty_collector=True)

    rc, values = plan_review_round.execute_round(
        design=tmp_path,
        round_num=2,
        prune_round_num=2,
        codex_present="false",
        cursor_present="true",
        plan_file=plan_file,
        feature_file=feature_file,
    )

    assert rc == 0
    assert values["LOOP_STATUS"] == "degraded-empty-collector"
    round_status = tmp_path / "plan-review" / "round-2" / "reviewer-status.tsv"
    assert round_status.read_text(encoding="utf-8").splitlines()[1] == "Cursor-Arch\tskipped\t"
    assert (tmp_path / "collector-results.env").read_text(encoding="utf-8") == ""


def test_execute_round_tally_error_syncs_latest_reviewer_status(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-success terminals still refresh latest-reviewer-status.tsv (issue #4848)."""
    plan_file = tmp_path / "plan.txt"
    feature_file = tmp_path / "feature.txt"
    _ = plan_file.write_text("plan\n", encoding="utf-8")
    _ = feature_file.write_text("feature\n", encoding="utf-8")
    _install_execute_round_fake(monkeypatch, tmp_path, tally_status="tally-error")

    rc, values = plan_review_round.execute_round(
        design=tmp_path,
        round_num=2,
        prune_round_num=2,
        codex_present="false",
        cursor_present="true",
        plan_file=plan_file,
        feature_file=feature_file,
    )

    assert rc == 2
    assert values["LOOP_STATUS"] == "tally-error"
    round_status = tmp_path / "plan-review" / "round-2" / "reviewer-status.tsv"
    latest = tmp_path / "latest-reviewer-status.tsv"
    assert round_status.is_file()
    assert latest.is_file()
    assert round_status.read_text(encoding="utf-8") == latest.read_text(encoding="utf-8")


def test_execute_round_degraded_empty_collector_syncs_latest_reviewer_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """degraded-empty-collector refreshes latest-reviewer-status.tsv (issue #4848)."""
    plan_file = tmp_path / "plan.txt"
    feature_file = tmp_path / "feature.txt"
    _ = plan_file.write_text("plan\n", encoding="utf-8")
    _ = feature_file.write_text("feature\n", encoding="utf-8")
    _install_execute_round_fake(monkeypatch, tmp_path, empty_collector=True)
    stale_latest = tmp_path / "latest-reviewer-status.tsv"
    _ = stale_latest.write_text("slot\tstatus\telapsed\nStale\tskipped\t\n", encoding="utf-8")

    rc, values = plan_review_round.execute_round(
        design=tmp_path,
        round_num=2,
        prune_round_num=2,
        codex_present="false",
        cursor_present="true",
        plan_file=plan_file,
        feature_file=feature_file,
    )

    assert rc == 0
    assert values["LOOP_STATUS"] == "degraded-empty-collector"
    round_status = tmp_path / "plan-review" / "round-2" / "reviewer-status.tsv"
    assert round_status.is_file()
    assert stale_latest.read_text(encoding="utf-8") == round_status.read_text(encoding="utf-8")
    assert "Stale" not in stale_latest.read_text(encoding="utf-8")


def test_execute_round_zero_findings_short_circuits_before_voting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """All reviewers report no findings (ok_count>0, empty ballot): the round short-circuits
    to zero-findings-degraded-panel and skips voter dispatch, never panel-failed (issue #5032).

    A converged round collects OK reviewers that each found nothing, so findings-in-scope.md and
    the ballot are empty. Pre-fix, that empty ballot was dispatched to the 3-voter panel, which
    inevitably degraded, and the voter-dispatch failure gate mapped the degraded result to
    panel-failed before the benign _classify_round_loop_status could return
    zero-findings-degraded-panel. This guards the short-circuit and proves voting is skipped.
    """
    design = tmp_path
    plan_file = design / "plan.txt"
    feature_file = design / "feature.txt"
    _ = plan_file.write_text("plan\n", encoding="utf-8")
    _ = feature_file.write_text("feature\n", encoding="utf-8")
    reviewer_file = design / "cursor-plan-arch-output.txt"
    voter_called = {"hit": False}

    def fake_run_cli(argv: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        del env
        if argv[:2] == ["plan-review", "panel-dispatch"]:
            _ = (design / "plan-review-slots.ndjson").write_text(
                '{"slot":"cursor-plan-arch","tool":"cursor","output":"'
                + str(reviewer_file)
                + '","prompt_file":"'
                + str(design / "cursor-plan-arch.prompt")
                + '"}\n',
                encoding="utf-8",
            )
            paths_file = design / "plan-review-panel-paths.txt"
            _ = paths_file.write_text(str(reviewer_file) + "\n", encoding="utf-8")
            return subprocess.CompletedProcess(argv, 0, f"PANEL_PRUNED_EMPTY=false\nPANEL_PATHS_FILE={paths_file}\n", "")
        if argv[:2] == ["agent", "collect-results"]:
            # OK reviewer with no structured sidecar: a genuine zero-findings review
            # (ok_count==1, no findings parsed -> empty ballot), unlike the empty-collector
            # (ok_count==0) case that must stay degraded-empty-collector (issue #4790).
            record = collect_results.CollectorRecord(
                reviewer_file=str(reviewer_file),
                tool="cursor",
                status="OK",
                exit_code="0",
            )
            return subprocess.CompletedProcess(argv, 0, _collector_text([record]), "")
        if argv[:2] == ["review", "aggregate-findings"]:
            return subprocess.CompletedProcess(argv, 0, "REASON=insufficient-input\nAGGREGATED=false\n", "")
        if argv[:2] == ["plan-review", "voter-dispatch"]:
            voter_called["hit"] = True
            # Faithful empty-ballot degradation: pre-fix this maps to panel-failed.
            return subprocess.CompletedProcess(argv, 0, "DISPATCH_OK=false\nDEGRADED_PANEL=1\n", "")
        if argv[:2] == ["plan-review", "tally"]:
            return subprocess.CompletedProcess(argv, 0, "TALLY_PLAN_REVIEW_STATUS=ok\n", "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(plan_review_round, "_run_cli", fake_run_cli)

    rc, values = plan_review_round.execute_round(
        design=design,
        round_num=5,
        prune_round_num=5,
        codex_present="false",
        cursor_present="true",
        plan_file=plan_file,
        feature_file=feature_file,
    )

    assert rc == 0
    assert values["LOOP_STATUS"] == "zero-findings-degraded-panel"
    assert values["TALLY_PLAN_REVIEW_STATUS"] == "ok"
    assert values["DEGRADED_PANEL"] == "0"
    # The whole point of the fix: voting is skipped for an empty ballot (issue #5032).
    assert voter_called["hit"] is False


def test_execute_round_zero_findings_short_circuit_requires_zero_fail_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Partial collector failure (ok_count>0, fail_count>0, empty ballot) must not benign-short-circuit."""
    design = tmp_path
    plan_file = design / "plan.txt"
    feature_file = design / "feature.txt"
    _ = plan_file.write_text("plan\n", encoding="utf-8")
    _ = feature_file.write_text("feature\n", encoding="utf-8")
    ok_reviewer = design / "cursor-plan-arch-output.txt"
    fail_reviewer = design / "codex-plan-arch-output.txt"
    voter_called = {"hit": False}

    def fake_run_cli(argv: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        del env
        if argv[:2] == ["plan-review", "panel-dispatch"]:
            _ = (design / "plan-review-slots.ndjson").write_text(
                "\n".join(
                    [
                        '{"slot":"cursor-plan-arch","tool":"cursor","output":"'
                        + str(ok_reviewer)
                        + '","prompt_file":"'
                        + str(design / "cursor-plan-arch.prompt")
                        + '"}',
                        '{"slot":"codex-plan-arch","tool":"codex","output":"'
                        + str(fail_reviewer)
                        + '","prompt_file":"'
                        + str(design / "codex-plan-arch.prompt")
                        + '"}',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            paths_file = design / "plan-review-panel-paths.txt"
            _ = paths_file.write_text(f"{ok_reviewer}\n{fail_reviewer}\n", encoding="utf-8")
            return subprocess.CompletedProcess(argv, 0, f"PANEL_PRUNED_EMPTY=false\nPANEL_PATHS_FILE={paths_file}\n", "")
        if argv[:2] == ["agent", "collect-results"]:
            records = [
                collect_results.CollectorRecord(
                    reviewer_file=str(ok_reviewer),
                    tool="cursor",
                    status="OK",
                    exit_code="0",
                ),
                collect_results.CollectorRecord(
                    reviewer_file=str(fail_reviewer),
                    tool="codex",
                    status="TIMEOUT",
                    exit_code="124",
                    failure_reason="timed out",
                ),
            ]
            return subprocess.CompletedProcess(argv, 0, _collector_text(records), "")
        if argv[:2] == ["review", "aggregate-findings"]:
            return subprocess.CompletedProcess(argv, 0, "REASON=insufficient-input\nAGGREGATED=false\n", "")
        if argv[:2] == ["plan-review", "voter-dispatch"]:
            voter_called["hit"] = True
            return subprocess.CompletedProcess(argv, 0, "DISPATCH_OK=false\nDEGRADED_PANEL=1\n", "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(plan_review_round, "_run_cli", fake_run_cli)

    rc, values = plan_review_round.execute_round(
        design=design,
        round_num=6,
        prune_round_num=6,
        codex_present="true",
        cursor_present="true",
        plan_file=plan_file,
        feature_file=feature_file,
    )

    assert rc == 1
    assert values["LOOP_STATUS"] == "panel-failed"
    assert values["DEGRADED_PANEL"] == "1"
    assert voter_called["hit"] is True


def test_execute_round_zero_findings_clears_stale_tally_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stale accepted-plan-findings.md from a prior round must not survive zero-findings short-circuit (#5032)."""
    design = tmp_path
    plan_file = design / "plan.txt"
    feature_file = design / "feature.txt"
    _ = plan_file.write_text("plan\n", encoding="utf-8")
    _ = feature_file.write_text("feature\n", encoding="utf-8")
    reviewer_file = design / "cursor-plan-arch-output.txt"
    _ = (design / "accepted-plan-findings.md").write_text(
        "### FINDING_1: Stale from round 4\n- **Concern**: already applied\n",
        encoding="utf-8",
    )
    _ = (design / "rejected-findings.md").write_text("### [Plan Review] FINDING_2\n", encoding="utf-8")
    _ = (design / "oos.md").write_text("### OOS_1: stale\n", encoding="utf-8")
    _ = (design / "oos-accepted-design.md").write_text("stale oos accepted\n", encoding="utf-8")
    _ = (design / "voting-tally.md").write_text(
        "## Findings\n| Item | YES | NO | JERR | Result |\n| FINDING_1 | 3 | 0 | 0 | accepted |\n",
        encoding="utf-8",
    )

    fake_run_cli = make_zero_findings_plan_review_fake_cli(design, reviewer_file)

    monkeypatch.setattr(plan_review_round, "_run_cli", fake_run_cli)

    rc, values = plan_review_round.execute_round(
        design=design,
        round_num=5,
        prune_round_num=5,
        codex_present="false",
        cursor_present="true",
        plan_file=plan_file,
        feature_file=feature_file,
    )

    assert rc == 0
    assert values["LOOP_STATUS"] == "zero-findings-degraded-panel"
    assert values["ACCEPTED_COUNT"] == "0"
    assert not (design / "accepted-plan-findings.md").read_text(encoding="utf-8").strip()
    assert not (design / "rejected-findings.md").read_text(encoding="utf-8").strip()
    assert not (design / "oos.md").read_text(encoding="utf-8").strip()
    assert not (design / "oos-accepted-design.md").read_text(encoding="utf-8").strip()
    assert "FINDING_1" not in (design / "voting-tally.md").read_text(encoding="utf-8")
    assert values.get("VOTING_TALLY_FILE") == str(design / "voting-tally.md")


def test_execute_round_degraded_usable_voter_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Degraded-but-usable voter dispatch (Claude fails, Codex+Cursor succeed) proceeds to tally (issue #5637)."""
    design = tmp_path
    plan_file = design / "plan.txt"
    feature_file = design / "feature.txt"
    _ = plan_file.write_text("plan\n", encoding="utf-8")
    _ = feature_file.write_text("feature\n", encoding="utf-8")
    reviewer_file = design / "cursor-plan-arch-output.txt"
    voter_1_path = design / "claude-vote-output.txt"
    voter_2_path = design / "codex-vote-output.txt"
    voter_3_path = design / "cursor-vote-output.txt"
    tally_calls: list[list[str]] = []

    def fake_run_cli(argv: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        del env
        if argv[:2] == ["plan-review", "panel-dispatch"]:
            manifest = design / "plan-review-slots.ndjson"
            paths_file = design / "plan-review-panel-paths.txt"
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
            sidecar = design / "cursor-plan-arch.sidecar.tsv"
            _write_sidecar(
                sidecar,
                [{"scope": "in_scope", "severity": "high", "focus_area": "correctness", "location": "plan.md", "what": "Issue", "scenario_or_breakage": "x", "suggested_fix": "y"}],
            )
            return subprocess.CompletedProcess(
                argv, 0,
                _collector_text([collect_results.CollectorRecord(reviewer_file=str(reviewer_file), tool="cursor", status="OK", exit_code="0", structured_sidecar=str(sidecar))]),
                "",
            )
        if argv[:2] == ["review", "aggregate-findings"]:
            return subprocess.CompletedProcess(argv, 0, "REASON=ok\nAGGREGATED=true\n", "")
        if argv[:2] == ["plan-review", "voter-dispatch"]:
            return subprocess.CompletedProcess(
                argv, 0,
                "DISPATCH_OK=true\n"
                "DEGRADED_PANEL=1\n"
                f"VOTER_1_PATH={voter_1_path}\n"
                "VOTER_1_TOOL=claude\n"
                "VOTER_1_STATUS=failed\n"
                "VOTER_1_PARSE_RATE_STATUS=SKIPPED\n"
                f"VOTER_2_PATH={voter_2_path}\n"
                "VOTER_2_TOOL=codex\n"
                "VOTER_2_STATUS=launched\n"
                "VOTER_2_PARSE_RATE_STATUS=OK\n"
                f"VOTER_3_PATH={voter_3_path}\n"
                "VOTER_3_TOOL=cursor\n"
                "VOTER_3_STATUS=launched\n"
                "VOTER_3_PARSE_RATE_STATUS=OK\n",
                "",
            )
        if argv[:2] == ["plan-review", "tally"]:
            tally_calls.append(argv[:])
            classification = Path(argv[argv.index("--findings-classification-out") + 1])
            classification.parent.mkdir(parents=True, exist_ok=True)
            _ = classification.write_text(
                "finding_id\tfinding_reviewers\tvoting_result\nFINDING_1\tCodex,Cursor\taccepted\n",
                encoding="utf-8",
            )
            _ = (design / "accepted-plan-findings.md").write_text("### FINDING_1:\nsome content\n", encoding="utf-8")
            return subprocess.CompletedProcess(argv, 0, "TALLY_PLAN_REVIEW_STATUS=ok\n", "")
        raise AssertionError(f"unexpected argv: {argv}")

    monkeypatch.setattr(plan_review_round, "_run_cli", fake_run_cli)

    rc, values = plan_review_round.execute_round(
        design=design,
        round_num=1,
        prune_round_num=1,
        codex_present="true",
        cursor_present="true",
        plan_file=plan_file,
        feature_file=feature_file,
    )

    assert rc == 0
    assert values["LOOP_STATUS"] != "panel-failed"
    assert int(values.get("ACCEPTED_COUNT", "0")) > 0
    assert tally_calls, "plan-review tally was not called"
    tally_str = " ".join(tally_calls[0])
    assert str(voter_2_path) in tally_str
    assert str(voter_3_path) in tally_str
    assert str(voter_1_path) not in tally_str
