# pyright: reportUnusedCallResult=false, reportArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false
from __future__ import annotations

import json
from pathlib import Path

from larch import cli
from larch.issue import rejected_analysis as ra


def _write_json_lines(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _write_rust_work_dir(work_dir: Path, state_root: Path) -> dict[str, object]:
    """Seed the exact work-directory model consumed from Rust prepare/ingest."""
    work_dir.mkdir()
    candidate: dict[str, object] = {
        "candidate_id": "C1",
        "finding_hash": "finding-hash",
        "concern_hash": "concern-hash",
        "prompt_path": str(work_dir / "verify-C1.md"),
        "finding": {
            "finding_hash": "finding-hash",
            "concern_hash": "concern-hash",
            "source_skill": "implement",
            "run_id": "RUN-1",
            "round_num": "1",
            "canonical_finding_id": "FINDING_1",
            "synthetic_id": "REJ_CR1_1",
            "reviewer_slots": ["cursor-specialist"],
            "dissenting_slots": ["cursor"],
            "file_path": "python/foo.py",
            "line_hint": "12",
            "concern": "Missing required check",
            "prose_body": "### FINDING_1: Missing required check\n",
            "classification_row": {},
            "vote_split": {
                "yes_votes": 1,
                "no_votes": 2,
                "yes_slots": ["cursor"],
                "no_slots": ["codex", "claude"],
                "high_severity": True,
            },
            "started_at": "2026-08-14T12:00:00Z",
            "demoted_later_touched": False,
        },
    }
    (work_dir / "candidates.json").write_text(
        json.dumps([candidate], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (work_dir / "verdicts.jsonl").write_text("", encoding="utf-8")
    (work_dir / ra.INGEST_STATUS_FILE).write_text("", encoding="utf-8")
    (work_dir / "ledger-pending.tsv").write_text(
        "\t".join(ra.LEDGER_COLUMNS) + "\n",
        encoding="utf-8",
    )
    (work_dir / "repo-root.txt").write_text(str(state_root) + "\n", encoding="utf-8")
    (work_dir / "state-root.txt").write_text(str(state_root) + "\n", encoding="utf-8")
    return candidate


def _write_confirmed_rust_ingest(work_dir: Path) -> None:
    _write_json_lines(
        work_dir / "verdicts.jsonl",
        [
            {
                "candidate_id": "C1",
                "finding_hash": "finding-hash",
                "status": "confirmed",
                "current_location": "python/foo.py:13",
                "evidence": "Current code still omits the check.",
                "dirty_tree": False,
            }
        ],
    )
    _write_json_lines(
        work_dir / ra.INGEST_STATUS_FILE,
        [
            {
                "schema_version": 1,
                "candidate_id": "C1",
                "finding_hash": "finding-hash",
                "status": "ingested",
                "disposition": "confirmed",
                "launcher_exit": 0,
                "output_path": str(work_dir / "verdict-C1.txt"),
            }
        ],
    )


def test_rust_owned_prepare_and_ingest_have_no_python_entrypoints() -> None:
    assert ("rejected-analysis", "prepare") not in cli._REGISTRY  # pyright: ignore[reportPrivateUsage]
    assert ("rejected-analysis", "ingest-verdict") not in cli._REGISTRY  # pyright: ignore[reportPrivateUsage]
    assert not hasattr(ra, "prepare")
    assert not hasattr(ra, "prepare_main")
    assert not hasattr(ra, "ingest_verdict")
    assert not hasattr(ra, "ingest_verdict_main")


def test_finalize_and_record_consume_rust_wire_artifacts(tmp_path: Path) -> None:
    work_dir = tmp_path / "work"
    _write_rust_work_dir(work_dir, tmp_path)
    _write_confirmed_rust_ingest(work_dir)

    finalized = ra.finalize(work_dir=work_dir)

    assert finalized.confirmed_count == 1
    assert "Dissenting voter(s):" in finalized.issue_batch_file.read_text(encoding="utf-8")
    issue_output = work_dir / "issue.stdout.txt"
    issue_output.write_text(
        "ISSUES_CREATED=1\nISSUES_FAILED=0\nISSUES_DEDUPLICATED=0\n"
        "ISSUE_1_NUMBER=123\nISSUE_1_URL=https://example.invalid/123\n",
        encoding="utf-8",
    )
    recorded = ra.record(
        work_dir=work_dir,
        issue_output=issue_output,
        issue_verified=True,
        repo_root=tmp_path,
        state_root=tmp_path,
    )

    assert recorded.rc == 0
    ledger = (tmp_path / ra.LEDGER_PATH).read_text(encoding="utf-8")
    assert "filed-as" in ledger
    assert "123" in ledger


def test_launch_failed_rust_ingest_status_remains_retryable(tmp_path: Path) -> None:
    work_dir = tmp_path / "work"
    _write_rust_work_dir(work_dir, tmp_path)
    _write_json_lines(
        work_dir / ra.INGEST_STATUS_FILE,
        [
            {
                "schema_version": 1,
                "candidate_id": "C1",
                "finding_hash": "finding-hash",
                "status": "launch-failed",
                "disposition": "",
                "launcher_exit": 1,
                "output_path": str(work_dir / "verdict-C1.txt"),
            }
        ],
    )

    finalized = ra.finalize(work_dir=work_dir)
    recorded = ra.record(
        work_dir=work_dir,
        launch_failures=0,
        repo_root=tmp_path,
        state_root=tmp_path,
    )

    assert finalized.launch_failures == 1
    assert recorded.rc == 1
    ledger = (tmp_path / ra.LEDGER_PATH).read_text(encoding="utf-8")
    assert "finding-hash" not in ledger
    assert "dismissed:verification-failed" not in ledger


def test_dirty_tree_rust_ingest_status_is_not_published_to_sidecar(tmp_path: Path) -> None:
    work_dir = tmp_path / "work"
    _write_rust_work_dir(work_dir, tmp_path)
    _write_json_lines(
        work_dir / ra.INGEST_STATUS_FILE,
        [
            {
                "schema_version": 1,
                "candidate_id": "C1",
                "finding_hash": "finding-hash",
                "status": "dirty-tree",
                "disposition": "dismissed:dirty-tree",
                "launcher_exit": 0,
                "output_path": str(work_dir / "verdict-C1.txt"),
            }
        ],
    )

    _ = ra.finalize(work_dir=work_dir)
    _ = ra.record(work_dir=work_dir, repo_root=tmp_path, state_root=tmp_path)

    sidecar = tmp_path / ra.VERDICT_SIDECAR
    assert not sidecar.is_file() or "finding-hash" not in sidecar.read_text(encoding="utf-8")


def test_record_prefers_filed_rows_from_rust_wire_work_dir(tmp_path: Path) -> None:
    work_dir = tmp_path / "work"
    _write_rust_work_dir(work_dir, tmp_path)
    _write_confirmed_rust_ingest(work_dir)
    _ = ra.finalize(work_dir=work_dir)
    issue_output = work_dir / "issue.stdout.txt"
    issue_output.write_text(
        "ISSUES_CREATED=1\nISSUES_FAILED=1\nISSUES_DEDUPLICATED=0\n"
        "ISSUE_1_NUMBER=456\nISSUE_1_URL=https://example.invalid/456\n",
        encoding="utf-8",
    )

    recorded = ra.record(
        work_dir=work_dir,
        issue_output=issue_output,
        issue_verified=True,
        issues_failed=1,
        repo_root=tmp_path,
        state_root=tmp_path,
    )

    assert recorded.rc == 1
    ledger = (tmp_path / ra.LEDGER_PATH).read_text(encoding="utf-8")
    assert "filed-as" in ledger
    assert "456" in ledger
