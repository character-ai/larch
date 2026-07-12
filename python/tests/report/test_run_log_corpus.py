"""Tests for shared run_log_corpus helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from larch.report import run_log_corpus

# pytest.MonkeyPatch is used by enumeration-error coverage below.


def _write_manifest(run_dir: Path, payload: object, *, name: str = "manifest.json") -> None:
    _ = (run_dir / name).write_text(json.dumps(payload), encoding="utf-8")


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


def test_load_run_manifest_rejects_run_manifest_only(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-alt"
    run_dir.mkdir()
    _write_manifest(run_dir, {"issue_number": 7, "started_at": "2026-01-01T00:00:00Z"}, name="run-manifest.json")
    assert run_log_corpus.load_run_manifest(run_dir) is None
    assert run_log_corpus.run_dirs(tmp_path) == []


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


def test_safe_child_run_dirs_skips_symlinks_and_escapes(tmp_path: Path) -> None:
    root = tmp_path / "implement"
    root.mkdir()
    good = root / "run-good"
    good.mkdir()
    linked = root / "run-link"
    target = tmp_path / "outside"
    target.mkdir()
    linked.symlink_to(target)
    warnings: list[run_log_corpus.WalkWarning] = []
    dirs = run_log_corpus.safe_child_run_dirs(root, on_warning=warnings.append)
    assert [path.name for path in dirs] == ["run-good"]
    assert any(warning.kind is run_log_corpus.WalkWarningKind.CHILD_SYMLINK for warning in warnings)


def test_safe_child_run_dirs_missing_root(tmp_path: Path) -> None:
    warnings: list[run_log_corpus.WalkWarning] = []
    dirs = run_log_corpus.safe_child_run_dirs(tmp_path / "missing", on_warning=warnings.append)
    assert dirs == []
    assert warnings[0].kind is run_log_corpus.WalkWarningKind.ROOT_MISSING


def test_safe_child_run_dirs_rejects_symlinked_and_non_directory_roots(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    linked = tmp_path / "linked"
    linked.symlink_to(target)
    file_root = tmp_path / "file-root"
    _ = file_root.write_text("not a directory\n", encoding="utf-8")
    assert run_log_corpus.safe_child_run_dirs(linked) == []
    assert run_log_corpus.safe_child_run_dirs(file_root) == []


def test_run_started_at_policies(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    _write_manifest(run_dir, {"updated_at": "2026-02-01T00:00:00Z"})
    _write_manifest(
        run_dir,
        {"started_at": "2026-03-01T00:00:00Z"},
        name="run-manifest.json",
    )
    assert (
        run_log_corpus.run_started_at(run_dir, allow_updated_at_fallback=True, continue_on_empty=False)
        == "2026-02-01T00:00:00Z"
    )
    assert (
        run_log_corpus.run_started_at(run_dir, allow_updated_at_fallback=False, continue_on_empty=True)
        == "2026-03-01T00:00:00Z"
    )
    assert (
        run_log_corpus.run_started_at(
            run_dir,
            allow_updated_at_fallback=False,
            continue_on_empty=False,
            manifest_candidates=("manifest.json",),
        )
        == ""
    )


def test_run_started_at_stops_on_first_valid_object(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    _write_manifest(run_dir, {"started_at": "", "updated_at": ""})
    _write_manifest(run_dir, {"started_at": "2026-04-01T00:00:00Z"}, name="run-manifest.json")
    assert (
        run_log_corpus.run_started_at(run_dir, allow_updated_at_fallback=True, continue_on_empty=False)
        == ""
    )


def test_run_ended_at_precedence(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    _write_manifest(
        run_dir,
        {
            "ended_at": "2026-01-02T00:00:00Z",
            "completed_at": "2026-01-03T00:00:00Z",
            "updated_at": "2026-01-04T00:00:00Z",
        },
    )
    assert run_log_corpus.run_ended_at(run_dir) == "2026-01-02T00:00:00Z"
    _write_manifest(run_dir, {"completed_at": "2026-01-03T00:00:00Z", "updated_at": "2026-01-04T00:00:00Z"})
    assert run_log_corpus.run_ended_at(run_dir) == "2026-01-03T00:00:00Z"


def test_larch_version_continue_on_empty(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    _write_manifest(run_dir, {"larch_version": ""})
    _write_manifest(run_dir, {"larch_version": "1.2.3"}, name="run-manifest.json")
    assert run_log_corpus.larch_version(run_dir, continue_on_empty=False) == ""
    assert run_log_corpus.larch_version(run_dir, continue_on_empty=True) == "1.2.3"


def test_metadata_skips_invalid_values_for_valid_fallbacks(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    _write_manifest(run_dir, {"started_at": 42, "updated_at": "not-a-timestamp", "larch_version": "bad"})
    _write_manifest(
        run_dir,
        {"started_at": "2026-05-01T00:00:00Z", "ended_at": "2026-05-02T00:00:00Z", "larch_version": "1.2.3"},
        name="run-manifest.json",
    )
    assert run_log_corpus.run_started_at(run_dir) == "2026-05-01T00:00:00Z"
    assert run_log_corpus.run_ended_at(run_dir) == "2026-05-02T00:00:00Z"
    assert run_log_corpus.larch_version(run_dir) == "1.2.3"


def test_round_num_from_path() -> None:
    assert run_log_corpus.round_num_from_path(Path("round-3/findings-classification.tsv")) == 3
    assert run_log_corpus.round_num_from_path(Path("review-findings-classification-round-12.tsv")) == 12
    assert run_log_corpus.round_num_from_path(Path("findings-classification.tsv")) is None


def test_classification_and_discover(tmp_path: Path) -> None:
    log_root = tmp_path / "larch-logs"
    design = log_root / "design" / "d1" / "plan-review" / "round-2"
    design.mkdir(parents=True)
    _ = (design / "findings-classification.tsv").write_text("h\n", encoding="utf-8")
    implement = log_root / "implement" / "i1" / "round-1"
    implement.mkdir(parents=True)
    _ = (implement / "findings-classification.tsv").write_text("h\n", encoding="utf-8")
    review = log_root / "review" / "r1"
    review.mkdir(parents=True)
    _ = (review / "review-findings-classification-round-4.tsv").write_text("h\n", encoding="utf-8")
    rows = run_log_corpus.discover_classifications(log_root, round_sort="numeric")
    assert [(skill, path.name) for skill, path in rows] == [
        ("design", "findings-classification.tsv"),
        ("implement", "findings-classification.tsv"),
        ("review", "review-findings-classification-round-4.tsv"),
    ]
    lexical = run_log_corpus.classification_tsv_paths(
        "review",
        review,
        round_sort="lexical",
    )
    assert [path.name for path in lexical] == ["review-findings-classification-round-4.tsv"]


def test_validated_run_escape_and_bytes(tmp_path: Path) -> None:
    logs = tmp_path / "larch-logs"
    run_dir = logs / "implement" / "run-1"
    nested = run_dir / "nested"
    nested.mkdir(parents=True)
    file_path = nested / "keep.txt"
    _ = file_path.write_text("abc", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    _ = outside.write_text("x", encoding="utf-8")
    escape = nested / "escape"
    escape.symlink_to(outside)
    assert run_log_corpus.validated_run_has_escape_symlink(run_dir, contain_root=logs) is True
    assert run_log_corpus.validated_run_dir_bytes(run_dir) >= 3
    with pytest.raises(ValueError, match="could not resolve run directory"):
        _ = list(run_log_corpus.iter_validated_run_walk(tmp_path / "missing-run", contain_root=tmp_path))
    with pytest.raises(ValueError, match="direct safe child"):
        _ = list(run_log_corpus.iter_validated_run_walk(logs, contain_root=logs))


def test_iter_validated_run_files_skips_fifo(tmp_path: Path) -> None:
    logs = tmp_path / "larch-logs"
    run_dir = logs / "implement" / "run-1"
    run_dir.mkdir(parents=True)
    fifo = run_dir / "findings-classification.tsv"
    os.mkfifo(fifo)
    assert list(run_log_corpus.iter_validated_run_files(run_dir, name=fifo.name, contain_root=run_dir.parent)) == []


def test_safe_child_run_dirs_enumeration_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "implement"
    root.mkdir()

    def _boom(*_args: object, **_kwargs: object) -> list[Path]:
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "glob", _boom)
    warnings: list[run_log_corpus.WalkWarning] = []
    assert run_log_corpus.safe_child_run_dirs(root, on_warning=warnings.append) == []
    assert warnings[0].kind is run_log_corpus.WalkWarningKind.ROOT_UNREADABLE


def test_metadata_skips_malformed_and_non_object_candidates(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    _ = (run_dir / "manifest.json").write_text("not-json", encoding="utf-8")
    _write_manifest(run_dir, ["array"], name="run-manifest.json")
    assert run_log_corpus.run_started_at(run_dir, allow_updated_at_fallback=True) == ""
    _write_manifest(run_dir, {"started_at": "2026-05-01T00:00:00Z"}, name="run-manifest.json")
    assert run_log_corpus.run_started_at(run_dir, allow_updated_at_fallback=False) == "2026-05-01T00:00:00Z"


def test_discover_design_classification_paths_recursive(tmp_path: Path) -> None:
    design_root = tmp_path / "design"
    nested = design_root / "run-a" / "extra" / "round-9"
    nested.mkdir(parents=True)
    _ = (nested / "findings-classification.tsv").write_text("h\n", encoding="utf-8")
    linked = design_root / "run-link"
    linked.symlink_to(tmp_path / "outside")
    (tmp_path / "outside").mkdir()
    paths = run_log_corpus.discover_design_classification_paths(design_root)
    assert [path.name for path in paths] == ["findings-classification.tsv"]
    assert paths[0].parent == nested


def test_classification_numeric_sort_orders_by_round(tmp_path: Path) -> None:
    run_dir = tmp_path / "implement" / "run"
    for round_num in (10, 2):
        round_dir = run_dir / f"round-{round_num}"
        round_dir.mkdir(parents=True)
        _ = (round_dir / "findings-classification.tsv").write_text("h\n", encoding="utf-8")
    numeric = run_log_corpus.classification_tsv_paths("implement", run_dir, round_sort="numeric")
    lexical = run_log_corpus.classification_tsv_paths("implement", run_dir, round_sort="lexical")
    assert [path.parent.name for path in numeric] == ["round-2", "round-10"]
    assert [path.parent.name for path in lexical] == ["round-10", "round-2"]


def test_classification_paths_reject_symlinked_tsv(tmp_path: Path) -> None:
    run_dir = tmp_path / "implement" / "run"
    round_dir = run_dir / "round-1"
    round_dir.mkdir(parents=True)
    outside = tmp_path / "outside.tsv"
    _ = outside.write_text("untrusted\n", encoding="utf-8")
    (round_dir / "findings-classification.tsv").symlink_to(outside)
    assert run_log_corpus.classification_tsv_paths("implement", run_dir) == []
