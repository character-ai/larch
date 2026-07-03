"""Tests for run_log_corpus manifest acceptance."""

from __future__ import annotations

import json
from pathlib import Path

from larch.report import run_log_corpus


def _write_manifest(run_dir: Path, payload: object) -> None:
    _ = (run_dir / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")


def test_load_run_manifest_rejects_bool_issue_number(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-1"
    run_dir.mkdir()
    _write_manifest(run_dir, {"issue_number": True})
    assert run_log_corpus.load_run_manifest(run_dir) is None


def test_load_run_manifest_accepts_padded_issue_number(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-2"
    run_dir.mkdir()
    _write_manifest(run_dir, {"issue_number": " 42 "})
    manifest = run_log_corpus.load_run_manifest(run_dir)
    assert manifest is not None
    assert manifest["issue_number"] == " 42 "


def test_load_run_manifest_accepts_comma_separated_issue_number(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-3"
    run_dir.mkdir()
    _write_manifest(run_dir, {"issue_number": "1,234"})
    manifest = run_log_corpus.load_run_manifest(run_dir)
    assert manifest is not None
    assert manifest["issue_number"] == "1,234"


def test_load_run_manifest_accepts_plain_issue_number(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-4"
    run_dir.mkdir()
    _write_manifest(run_dir, {"issue_number": 42})
    manifest = run_log_corpus.load_run_manifest(run_dir)
    assert manifest is not None
    assert manifest["issue_number"] == 42


def test_review_transcript_dirs_counts_manifestless_transcript(tmp_path: Path) -> None:
    review_root = tmp_path / "larch-logs" / "review"
    with_transcript = review_root / "run-a"
    with_transcript.mkdir(parents=True)
    _ = (with_transcript / "session-transcript.jsonl").write_text("{}\n", encoding="utf-8")
    without_transcript = review_root / "run-b"
    without_transcript.mkdir(parents=True)
    with_manifest = review_root / "run-c"
    with_manifest.mkdir(parents=True)
    _write_manifest(with_manifest, {"issue_number": 1})
    _ = (with_manifest / "session-transcript.jsonl").write_text("{}\n", encoding="utf-8")

    dirs = run_log_corpus.review_transcript_dirs(review_root)

    assert [path.name for path in dirs] == ["run-a", "run-c"]
