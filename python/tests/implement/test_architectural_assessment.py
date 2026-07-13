"""Tests for the Step 8 architectural assessment materialize/submit coordinator."""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest

from larch.core import config
from larch.implement import architectural_assessment as assessment


def _evidence(kind: str = config.ASSESSMENT_KIND_GUIDELINES) -> assessment.MaterializedEvidence:
    return assessment.MaterializedEvidence(
        kind=kind,
        head_sha="a" * 40,
        base_ref="origin/main",
        diff_path=Path("/tmp/diff"),
        diff_text="diff --git a/python/a.py b/python/a.py\n",
        diff_fingerprint="b" * 64,
        knowledge_path=Path("/tmp/knowledge"),
        knowledge_sha256="c" * 64,
        identifiers=frozenset({"G-Py-4"} if kind == config.ASSESSMENT_KIND_GUIDELINES else {"I-Stale-1"}),
    )


def _run_evidence(tmp_path: Path, kind: str = config.ASSESSMENT_KIND_GUIDELINES, *, docs_diff: bool = False) -> assessment.MaterializedEvidence:
    diff = tmp_path / f"{kind}-diff.txt"
    knowledge = tmp_path / f"{kind}-knowledge.md"
    diff_text = "diff --git a/docs/a.md b/docs/a.md\n" if docs_diff else "diff --git a/python/a.py b/python/a.py\n"
    _ = diff.write_text(diff_text, encoding="utf-8")
    _ = knowledge.write_text("### G-Py-4: Fail loudly\n" if kind == "guidelines" else "### I-Stale-1: Reject stale inputs\n", encoding="utf-8")
    base = _evidence(kind)
    return assessment.MaterializedEvidence(
        kind, base.head_sha, base.base_ref, diff, diff.read_text(encoding="utf-8"),
        base.diff_fingerprint, knowledge, assessment._sha256(knowledge.read_text(encoding="utf-8")),  # pyright: ignore[reportPrivateUsage]
        base.identifiers,
    )


def _stub_materialization(monkeypatch: pytest.MonkeyPatch, evidence_by_kind: dict[str, assessment.MaterializedEvidence]) -> None:
    head_sha = next(iter(evidence_by_kind.values())).head_sha
    monkeypatch.setattr(assessment, "_git_read", lambda *_args, **_kwargs: head_sha)  # type: ignore[reportUnknownLambdaType, reportUnknownArgumentType]
    monkeypatch.setattr(assessment, "_already_handled", lambda *_args, **_kwargs: False)  # type: ignore[reportUnknownLambdaType, reportUnknownArgumentType]
    monkeypatch.setattr(assessment, "_materialize_current", lambda kind, **_kwargs: evidence_by_kind[kind])  # type: ignore[reportUnknownLambdaType, reportUnknownArgumentType]


def test_normalize_kinds_deduplicates_and_orders() -> None:
    assert assessment.normalize_kinds(["guidelines", "invariants", "guidelines"]) == ("invariants", "guidelines")


@pytest.mark.parametrize("kinds", [[], ["other"]])
def test_normalize_kinds_rejects_invalid_requests(kinds: list[str]) -> None:
    with pytest.raises(ValueError, match=r"required|unsupported"):
        _ = assessment.normalize_kinds(kinds)


@pytest.mark.parametrize(
    ("diff_text", "expected"),
    [
        ("diff --git a/docs/a.md b/docs/a.md\n", True),
        ("diff --git a/larch-logs/run/a.txt b/larch-logs/run/a.txt\n", True),
        ("diff --git a/python/a.py b/python/a.py\n", False),
        ("diff --git a/docs/a.md b/docs/b.md\n", False),
        ("Binary files a/x and b/x differ\n", False),
        ("diff --git a/../x b/../x\n", False),
    ],
)
def test_deterministic_filter_is_conservative(diff_text: str, expected: bool) -> None:
    assert assessment.deterministic_out_of_scope(diff_text) is expected


def test_materialize_returns_pending_evidence_and_deterministic_status(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    inv = _run_evidence(tmp_path, config.ASSESSMENT_KIND_INVARIANTS)
    guide = _run_evidence(tmp_path, docs_diff=True)
    _stub_materialization(monkeypatch, {inv.kind: inv, guide.kind: guide})
    cleaned: list[str] = []

    def _fake_clean(evidence: assessment.MaterializedEvidence, *, repo_root: Path, implement_tmpdir: Path) -> None:
        _ = (repo_root, implement_tmpdir)
        cleaned.append(evidence.kind)

    monkeypatch.setattr(assessment, "_persist_clean", _fake_clean)
    statuses, pending = assessment.materialize(
        kinds=[config.ASSESSMENT_KIND_INVARIANTS, config.ASSESSMENT_KIND_GUIDELINES],
        repo_root=tmp_path, implement_tmpdir=tmp_path,
    )
    assert pending == [inv]
    assert statuses == {config.ASSESSMENT_KIND_GUIDELINES: "deterministic-clean"}
    assert cleaned == [config.ASSESSMENT_KIND_GUIDELINES]


def test_materialize_main_emits_per_kind_paths_and_identity(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    evidence = _run_evidence(tmp_path)
    _stub_materialization(monkeypatch, {evidence.kind: evidence})
    assert assessment.materialize_main([
        "--kind", "guidelines", "--repo-root", str(tmp_path), "--implement-tmpdir", str(tmp_path),
    ]) == config.EXIT_OK
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "ASSESSMENT_MATERIALIZE_STATUS=ok"
    assert "ASSESSMENT_REQUESTED_KINDS=guidelines" in out
    assert "ASSESSMENT_PENDING_KINDS=guidelines" in out
    assert f"ASSESSMENT_KIND_GUIDELINES_DIFF_PATH={evidence.diff_path}" in out
    assert f"ASSESSMENT_KIND_GUIDELINES_KNOWLEDGE_PATH={evidence.knowledge_path}" in out
    assert f"ASSESSMENT_KIND_GUIDELINES_HEAD_SHA={evidence.head_sha}" in out
    assert f"ASSESSMENT_KIND_GUIDELINES_DIFF_FINGERPRINT={evidence.diff_fingerprint}" in out


def test_materialize_main_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert assessment.materialize_main([]) == config.EXIT_USAGE
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "ASSESSMENT_MATERIALIZE_STATUS=usage-error"


def _stub_submit(monkeypatch: pytest.MonkeyPatch, evidence: assessment.MaterializedEvidence, *, head_sha: str | None = None) -> list[assessment.AssessmentResult]:
    monkeypatch.setattr(assessment, "validate_materialization", lambda *_args, **_kwargs: evidence)
    monkeypatch.setattr(assessment, "_git_read", lambda *_args, **_kwargs: head_sha if head_sha is not None else evidence.head_sha)
    persisted: list[assessment.AssessmentResult] = []
    monkeypatch.setattr(assessment, "_persist_result", lambda result, **_kwargs: persisted.append(result))
    return persisted


def test_submit_persists_valid_note_and_emits_identity(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    evidence = _run_evidence(tmp_path)
    persisted = _stub_submit(monkeypatch, evidence)
    result = assessment.submit(
        kind=config.ASSESSMENT_KIND_GUIDELINES, state="clean", note="No deviations identified.",
        repo_root=tmp_path, implement_tmpdir=tmp_path,
    )
    assert result.kind == config.ASSESSMENT_KIND_GUIDELINES
    assert result.state == "clean"
    assert result.head_sha == evidence.head_sha
    assert result.diff_fingerprint == evidence.diff_fingerprint
    assert persisted
    assert persisted[0].assessment == "No deviations identified."


def test_submit_rejects_head_drift_with_distinct_signal(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    evidence = _run_evidence(tmp_path)
    _stub_submit(monkeypatch, evidence, head_sha="z" * 40)
    with pytest.raises(assessment._HeadDrift):  # pyright: ignore[reportPrivateUsage]
        assessment.submit(
            kind=config.ASSESSMENT_KIND_GUIDELINES, state="clean", note="clean",
            repo_root=tmp_path, implement_tmpdir=tmp_path,
        )


def test_submit_rejects_invalid_state_token(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    guide = _run_evidence(tmp_path)
    _stub_submit(monkeypatch, guide)
    with pytest.raises(ValueError, match="unsupported"):
        assessment.submit(kind=config.ASSESSMENT_KIND_GUIDELINES, state="violation", note="x", repo_root=tmp_path, implement_tmpdir=tmp_path)
    inv = _run_evidence(tmp_path, config.ASSESSMENT_KIND_INVARIANTS)
    _stub_submit(monkeypatch, inv)
    with pytest.raises(ValueError, match="unsupported"):
        assessment.submit(kind=config.ASSESSMENT_KIND_INVARIANTS, state="deviation", note="x", repo_root=tmp_path, implement_tmpdir=tmp_path)


@pytest.mark.parametrize("note", ["", "   ", "x" * (assessment._MAX_ASSESSMENT_CHARS + 1)])  # pyright: ignore[reportPrivateUsage]
def test_submit_rejects_empty_or_oversized_note(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, note: str) -> None:
    evidence = _run_evidence(tmp_path)
    _stub_submit(monkeypatch, evidence)
    with pytest.raises(ValueError, match="empty or oversized"):
        assessment.submit(kind=config.ASSESSMENT_KIND_GUIDELINES, state="clean", note=note, repo_root=tmp_path, implement_tmpdir=tmp_path)


def test_submit_redacts_note_before_persist(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    evidence = _run_evidence(tmp_path)
    persisted = _stub_submit(monkeypatch, evidence)
    token = "ghp_" + "x" * 30
    assessment.submit(
        kind=config.ASSESSMENT_KIND_GUIDELINES, state="clean", note=f"clean note {token}",
        repo_root=tmp_path, implement_tmpdir=tmp_path,
    )
    assert persisted
    assert token not in persisted[0].assessment
    assert "<REDACTED-TOKEN>" in persisted[0].assessment


def test_submit_main_returns_head_drift_exit_code(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    evidence = _run_evidence(tmp_path)
    note = tmp_path / "note.md"
    _ = note.write_text("clean", encoding="utf-8")
    _stub_submit(monkeypatch, evidence, head_sha="z" * 40)
    rc = assessment.submit_main([
        "--kind", "guidelines", "--state", "clean", "--note-file", str(note),
        "--repo-root", str(tmp_path), "--implement-tmpdir", str(tmp_path),
    ])
    assert rc == 10
    assert "ASSESSMENT_STATUS=head-drift" in capsys.readouterr().out


def test_submit_main_complete_stdout_contract(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    evidence = _run_evidence(tmp_path)
    note = tmp_path / "note.md"
    _ = note.write_text("No deviations identified.", encoding="utf-8")
    _stub_submit(monkeypatch, evidence)
    assert assessment.submit_main([
        "--kind", "guidelines", "--state", "clean", "--note-file", str(note),
        "--repo-root", str(tmp_path), "--implement-tmpdir", str(tmp_path),
    ]) == config.EXIT_OK
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "ASSESSMENT_STATUS=complete"
    assert "ASSESSMENT_KIND=guidelines" in out
    assert "ASSESSMENT_STATE=clean" in out
    assert "ASSESSMENT_RESULTS=guidelines:clean" in out


def test_submit_main_rejects_note_file_outside_tmpdir(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    evidence = _run_evidence(tmp_path)
    _stub_submit(monkeypatch, evidence)
    outside = Path("/tmp/assessment-note-outside.md")
    rc = assessment.submit_main([
        "--kind", "guidelines", "--state", "clean", "--note-file", str(outside),
        "--repo-root", str(tmp_path), "--implement-tmpdir", str(tmp_path),
    ])
    assert rc == config.EXIT_USAGE
    assert "ASSESSMENT_STATUS=usage-error" in capsys.readouterr().out


def test_sanitize_detail_main_reads_stdin_and_emits_one_safe_line(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    token = "ghp_" + "x" * 30
    monkeypatch.setattr(sys, "stdin", io.StringIO(f"first\n{tmp_path}\t{token}"))
    rc = assessment.sanitize_detail_main(["--implement-tmpdir", str(tmp_path)])
    output = capsys.readouterr().out
    assert rc == config.EXIT_OK
    assert output.count("\n") == 1
    assert str(tmp_path) not in output
    assert token not in output
    assert output == "first <implement-tmpdir> <REDACTED-TOKEN>\n"


def test_sanitize_detail_main_caps_stdin_before_sanitizing(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    class _RecordingBuffer:
        def __init__(self) -> None:
            self.size: int | None = None

        def read(self, size: int) -> bytes:
            self.size = size
            return b"bounded diagnostic"

    class _Stdin:
        def __init__(self) -> None:
            self.buffer = _RecordingBuffer()

    stdin = _Stdin()
    monkeypatch.setattr(sys, "stdin", stdin)
    assert assessment.sanitize_detail_main(["--implement-tmpdir", str(tmp_path)]) == config.EXIT_OK
    assert stdin.buffer.size == assessment._MAX_SANITIZE_DETAIL_BYTES  # pyright: ignore[reportPrivateUsage]
    assert capsys.readouterr().out == "bounded diagnostic\n"


def _true_kwargs(**_kwargs: object) -> bool:
    return True


def _true_args(*_args: object, **_kwargs: object) -> bool:
    return True


def test_already_handled_refuses_unavailable_note(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def _unavailable_meta(_tmpdir: Path) -> dict[str, str]:
        return {"BASE_REF": "origin/main", "NOTE_STATE": config.NOTE_STATE_UNAVAILABLE}

    monkeypatch.setattr(assessment.architectural_guidelines, "invariant_durable_note_metadata", _unavailable_meta)
    monkeypatch.setattr(assessment.architectural_guidelines, "invariant_note_consumable", _true_kwargs)
    monkeypatch.setattr(assessment, "_outcome_valid", _true_args)
    handled = assessment._already_handled(  # pyright: ignore[reportPrivateUsage]
        config.ASSESSMENT_KIND_INVARIANTS, repo_root=tmp_path, implement_tmpdir=tmp_path, head_sha="a" * 40
    )
    assert handled is False


def test_already_handled_accepts_valid_authored_note(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def _authored_meta(_tmpdir: Path) -> dict[str, str]:
        return {
            "BASE_REF": "origin/main",
            "NOTE_STATE": config.NOTE_STATE_AUTHORED,
            "ASSESSMENT_KIND": config.ASSESSMENT_OUTCOME_CLEAN,
        }

    monkeypatch.setattr(assessment.architectural_guidelines, "invariant_durable_note_metadata", _authored_meta)
    monkeypatch.setattr(assessment.architectural_guidelines, "invariant_note_consumable", _true_kwargs)
    monkeypatch.setattr(assessment, "_authored_note_valid", _true_args)
    monkeypatch.setattr(assessment, "_outcome_valid", _true_args)
    handled = assessment._already_handled(  # pyright: ignore[reportPrivateUsage]
        config.ASSESSMENT_KIND_INVARIANTS, repo_root=tmp_path, implement_tmpdir=tmp_path, head_sha="a" * 40
    )
    assert handled is True


def _repair_stubs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, kind: str, state: str, invalidated: list[Path]) -> None:
    head = "a" * 40

    def _head(*_args: object, **_kwargs: object) -> str:
        return head

    def _meta(_tmpdir: Path) -> dict[str, str]:
        return {"BASE_REF": "origin/main", "ASSESSMENT_KIND": state}

    def _note_path(_tmpdir: Path) -> Path:
        return tmp_path / "note.md"

    def _fake_invalidate(tmpdir: Path) -> None:
        invalidated.append(tmpdir)

    monkeypatch.setattr(assessment, "_git_read", _head)
    if kind == config.ASSESSMENT_KIND_INVARIANTS:
        monkeypatch.setattr(assessment.architectural_guidelines, "invariant_durable_note_metadata", _meta)
        monkeypatch.setattr(assessment.architectural_guidelines, "invariant_durable_note_path", _note_path)
        monkeypatch.setattr(assessment.architectural_guidelines, "invalidate_invariant_implement_note", _fake_invalidate)
    else:
        monkeypatch.setattr(assessment.architectural_guidelines, "durable_note_metadata", _meta)
        monkeypatch.setattr(assessment.architectural_guidelines, "durable_note_path", _note_path)
        monkeypatch.setattr(assessment.architectural_guidelines, "invalidate_implement_note", _fake_invalidate)


def test_repair_current_outcome_invalid_kind_reauthors_and_invalidates(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    invalidated: list[Path] = []
    _repair_stubs(monkeypatch, tmp_path, kind=config.ASSESSMENT_KIND_GUIDELINES, state="bogus", invalidated=invalidated)
    status = assessment._repair_current_outcome(  # pyright: ignore[reportPrivateUsage]
        config.ASSESSMENT_KIND_GUIDELINES, repo_root=tmp_path, implement_tmpdir=tmp_path, head_sha="a" * 40
    )
    assert status == assessment._reauthor_status(config.ASSESSMENT_REAUTHOR_REASON_INVALID_OUTCOME)  # pyright: ignore[reportPrivateUsage]
    assert invalidated == [tmp_path]


def test_repair_current_outcome_unreadable_note_reauthors_and_invalidates(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    invalidated: list[Path] = []
    _repair_stubs(monkeypatch, tmp_path, kind=config.ASSESSMENT_KIND_INVARIANTS, state="clean", invalidated=invalidated)

    def _unreadable(_path: Path, **_kwargs: object) -> str:
        raise OSError("note unreadable")

    monkeypatch.setattr(assessment, "_read_regular", _unreadable)
    status = assessment._repair_current_outcome(  # pyright: ignore[reportPrivateUsage]
        config.ASSESSMENT_KIND_INVARIANTS, repo_root=tmp_path, implement_tmpdir=tmp_path, head_sha="a" * 40
    )
    assert status == assessment._reauthor_status(config.ASSESSMENT_REAUTHOR_REASON_MISSING_METADATA)  # pyright: ignore[reportPrivateUsage]
    assert invalidated == [tmp_path]


def test_repair_current_outcome_clean_classification_mismatch_reauthors_and_invalidates(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    invalidated: list[Path] = []
    _repair_stubs(monkeypatch, tmp_path, kind=config.ASSESSMENT_KIND_GUIDELINES, state="clean", invalidated=invalidated)

    def _note_text(_path: Path, **_kwargs: object) -> str:
        return "clean note prose that mentions G-Py-4"

    monkeypatch.setattr(assessment, "_read_regular", _note_text)
    monkeypatch.setattr(assessment.architectural_guidelines, "authored_outcome_valid", lambda **_kwargs: False)  # type: ignore[reportUnknownLambdaType, reportUnknownArgumentType]
    status = assessment._repair_current_outcome(  # pyright: ignore[reportPrivateUsage]
        config.ASSESSMENT_KIND_GUIDELINES, repo_root=tmp_path, implement_tmpdir=tmp_path, head_sha="a" * 40
    )
    assert status == assessment._reauthor_status(config.ASSESSMENT_REAUTHOR_REASON_CLEAN_MISMATCH)  # pyright: ignore[reportPrivateUsage]
    assert invalidated == [tmp_path]


def test_repair_current_outcome_non_clean_classification_mismatch_reauthors_and_invalidates(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    invalidated: list[Path] = []
    _repair_stubs(monkeypatch, tmp_path, kind=config.ASSESSMENT_KIND_GUIDELINES, state="deviation", invalidated=invalidated)

    def _note_text(_path: Path, **_kwargs: object) -> str:
        return "deviation note prose"

    monkeypatch.setattr(assessment, "_read_regular", _note_text)
    monkeypatch.setattr(assessment.architectural_guidelines, "authored_outcome_valid", lambda **_kwargs: False)  # type: ignore[reportUnknownLambdaType, reportUnknownArgumentType]
    status = assessment._repair_current_outcome(  # pyright: ignore[reportPrivateUsage]
        config.ASSESSMENT_KIND_GUIDELINES, repo_root=tmp_path, implement_tmpdir=tmp_path, head_sha="a" * 40
    )
    assert status == assessment._reauthor_status(config.ASSESSMENT_REAUTHOR_REASON_INVALID_OUTCOME)  # pyright: ignore[reportPrivateUsage]
    assert invalidated == [tmp_path]
