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
