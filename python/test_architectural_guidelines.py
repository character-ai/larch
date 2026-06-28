"""Tests for ARCHITECTURAL_GUIDELINES.md helper surfaces."""
# pyright: reportUnusedCallResult=false

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

from larch.core import architectural_guidelines as ag
def _git(cwd: Path, *args: str) -> None:
    completed = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=False)
    assert completed.returncode == 0, completed.stderr or completed.stdout


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    _git(repo, "init")
    _git(repo, "config", "user.name", "Larch Test")
    _git(repo, "config", "user.email", "larch@example.invalid")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "base")
    _git(repo, "branch", "-M", "main")
    _git(repo, "remote", "add", "origin", str(repo))
    _git(repo, "remote", "add", "upstream", str(repo))
    _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    _git(repo, "update-ref", "refs/remotes/upstream/main", "HEAD")
    return repo


def test_absent_file_returns_absent(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    result = ag.read_guidelines(repo_root=repo)
    assert result.status == "absent"
    assert result.content == ""


def test_present_file_emits_only_normalized_entries(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / ag.GUIDELINES_FILENAME).write_text(
        """Preamble ignored.

### G-python-1: Prefer direct Python helpers
- Why: They are easier to test & review.
- Run: rm -rf ignored
- Deviate when: A hook must target Bash.

### Not emitted
- Why: no.

### G-skill-2: Keep context small
- Why: Smaller prompts reduce anchoring.
- Deviate when: The contract requires a full file read.
""",
        encoding="utf-8",
    )
    result = ag.read_guidelines(repo_root=repo)
    assert result.status == "present"
    assert "Preamble" not in result.content
    assert "Run:" not in result.content
    assert "### Not emitted" not in result.content
    assert "### G-python-1: Prefer direct Python helpers" in result.content
    assert "- Why: They are easier to test & review." in result.content


def _write_guidelines(repo: Path) -> None:
    (repo / ag.GUIDELINES_FILENAME).write_text(
        """### G-design-1: Keep run evidence
- Why: Audits need durable evidence.
- Deviate when: The evidence would leak secrets.
""",
        encoding="utf-8",
    )


def _design_tmpdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    return tmp_path / "design-tmp"


def test_persist_design_assessment_clean_writes_clean_note(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _repo(tmp_path)
    _write_guidelines(repo)
    design_tmpdir = _design_tmpdir(tmp_path, monkeypatch)

    rc = ag.persist_design_assessment_main(["--repo-root", str(repo), "--design-tmpdir", str(design_tmpdir), "--assessment", "clean"])

    assert rc == 0
    assert (design_tmpdir / ag.DESIGN_ASSESSMENT).read_text(encoding="utf-8") == ag.CLEAN_PRESENTATION_NOTE + "\n"


def test_persist_design_assessment_file_normalizes_final_newline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _repo(tmp_path)
    _write_guidelines(repo)
    design_tmpdir = _design_tmpdir(tmp_path, monkeypatch)
    sidecar = tmp_path / "assessment.input.sidecar"
    sidecar.write_text("Deviation line 1\nDeviation line 2\n\n", encoding="utf-8")

    rc = ag.persist_design_assessment_main(["--repo-root", str(repo), "--design-tmpdir", str(design_tmpdir), "--assessment-file", str(sidecar)])

    assert rc == 0
    assert (design_tmpdir / ag.DESIGN_ASSESSMENT).read_text(encoding="utf-8") == "Deviation line 1\nDeviation line 2\n"


def test_persist_design_assessment_present_requires_exactly_one_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _repo(tmp_path)
    _write_guidelines(repo)
    design_tmpdir = _design_tmpdir(tmp_path, monkeypatch)
    sidecar = tmp_path / "assessment.input.sidecar"
    sidecar.write_text("Deviation\n", encoding="utf-8")

    assert ag.persist_design_assessment_main(["--repo-root", str(repo), "--design-tmpdir", str(design_tmpdir)]) == 1
    assert not (design_tmpdir / ag.DESIGN_ASSESSMENT).exists()
    assert (
        ag.persist_design_assessment_main(
            ["--repo-root", str(repo), "--design-tmpdir", str(design_tmpdir), "--assessment", "clean", "--assessment-file", str(sidecar)]
        )
        == 1
    )
    assert not (design_tmpdir / ag.DESIGN_ASSESSMENT).exists()


def test_persist_design_assessment_absent_and_invalid_remove_stale_artifact(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _repo(tmp_path)
    design_tmpdir = _design_tmpdir(tmp_path, monkeypatch)
    design_tmpdir.mkdir()
    stale = design_tmpdir / ag.DESIGN_ASSESSMENT
    stale.write_text("stale\n", encoding="utf-8")

    assert ag.persist_design_assessment_main(["--repo-root", str(repo), "--design-tmpdir", str(design_tmpdir)]) == 0
    assert not stale.exists()

    stale.write_text("stale\n", encoding="utf-8")
    target = tmp_path / "guidelines-target.md"
    target.write_text("not parsed\n", encoding="utf-8")
    (repo / ag.GUIDELINES_FILENAME).symlink_to(target)
    assert ag.persist_design_assessment_main(["--repo-root", str(repo), "--design-tmpdir", str(design_tmpdir)]) == 0
    assert not stale.exists()


def test_persist_design_assessment_file_rejects_whitespace_only_sidecar(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _repo(tmp_path)
    _write_guidelines(repo)
    design_tmpdir = _design_tmpdir(tmp_path, monkeypatch)
    sidecar = tmp_path / "assessment.input.sidecar"
    sidecar.write_text("   \n", encoding="utf-8")

    assert ag.persist_design_assessment_main(["--repo-root", str(repo), "--design-tmpdir", str(design_tmpdir), "--assessment-file", str(sidecar)]) == 1
    assert not (design_tmpdir / ag.DESIGN_ASSESSMENT).exists()


def test_persist_design_assessment_absent_invalid_reject_source_flags(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _repo(tmp_path)
    design_tmpdir = _design_tmpdir(tmp_path, monkeypatch)
    sidecar = tmp_path / "assessment.input.sidecar"
    sidecar.write_text("Deviation\n", encoding="utf-8")

    assert ag.persist_design_assessment_main(["--repo-root", str(repo), "--design-tmpdir", str(design_tmpdir), "--assessment", "clean"]) == 1
    assert ag.persist_design_assessment_main(["--repo-root", str(repo), "--design-tmpdir", str(design_tmpdir), "--assessment-file", str(sidecar)]) == 1


def test_persist_design_assessment_unlink_failure_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _repo(tmp_path)
    design_tmpdir = _design_tmpdir(tmp_path, monkeypatch)
    design_tmpdir.mkdir()
    stale = design_tmpdir / ag.DESIGN_ASSESSMENT
    stale.write_text("stale\n", encoding="utf-8")
    original_unlink = Path.unlink

    def fail_unlink(self: Path, missing_ok: bool = False) -> None:
        if self == stale:
            raise OSError("denied")
        original_unlink(self, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", fail_unlink)

    assert ag.persist_design_assessment_main(["--repo-root", str(repo), "--design-tmpdir", str(design_tmpdir)]) == 1
    assert stale.read_text(encoding="utf-8") == "stale\n"


def test_persist_design_assessment_absent_invalid_rejects_stale_symlink_or_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _repo(tmp_path)
    design_tmpdir = _design_tmpdir(tmp_path, monkeypatch)
    design_tmpdir.mkdir()
    stale = design_tmpdir / ag.DESIGN_ASSESSMENT
    target = tmp_path / "stale-target.md"
    target.write_text("stale\n", encoding="utf-8")
    stale.symlink_to(target)

    assert ag.persist_design_assessment_main(["--repo-root", str(repo), "--design-tmpdir", str(design_tmpdir)]) == 1
    assert stale.is_symlink()

    stale.unlink()
    stale.mkdir()

    assert ag.persist_design_assessment_main(["--repo-root", str(repo), "--design-tmpdir", str(design_tmpdir)]) == 1
    assert stale.is_dir()


def test_persist_design_assessment_overwrites_and_removes_after_prior_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _repo(tmp_path)
    _write_guidelines(repo)
    design_tmpdir = _design_tmpdir(tmp_path, monkeypatch)
    first = tmp_path / "first.sidecar"
    second = tmp_path / "second.sidecar"
    first.write_text("First deviation\n", encoding="utf-8")
    second.write_text("Second deviation", encoding="utf-8")

    assert ag.persist_design_assessment_main(["--repo-root", str(repo), "--design-tmpdir", str(design_tmpdir), "--assessment-file", str(first)]) == 0
    assert ag.persist_design_assessment_main(["--repo-root", str(repo), "--design-tmpdir", str(design_tmpdir), "--assessment-file", str(second)]) == 0
    assert (design_tmpdir / ag.DESIGN_ASSESSMENT).read_text(encoding="utf-8") == "Second deviation\n"
    (repo / ag.GUIDELINES_FILENAME).unlink()
    assert ag.persist_design_assessment_main(["--repo-root", str(repo), "--design-tmpdir", str(design_tmpdir)]) == 0
    assert not (design_tmpdir / ag.DESIGN_ASSESSMENT).exists()


def test_persist_design_assessment_fails_on_symlink_target_disallowed_tmpdir_or_unreadable_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _repo(tmp_path)
    _write_guidelines(repo)
    design_tmpdir = _design_tmpdir(tmp_path, monkeypatch)
    design_tmpdir.mkdir()
    target = tmp_path / "target.md"
    target.write_text("target\n", encoding="utf-8")
    (design_tmpdir / ag.DESIGN_ASSESSMENT).symlink_to(target)

    assert ag.persist_design_assessment_main(["--repo-root", str(repo), "--design-tmpdir", str(design_tmpdir), "--assessment", "clean"]) == 1
    assert target.read_text(encoding="utf-8") == "target\n"
    assert ag.persist_design_assessment_main(["--repo-root", str(repo), "--design-tmpdir", "/usr", "--assessment", "clean"]) == 1
    symlink_tmpdir = tmp_path / "symlink-design-tmp"
    symlink_tmpdir.symlink_to(design_tmpdir, target_is_directory=True)
    assert ag.persist_design_assessment_main(["--repo-root", str(repo), "--design-tmpdir", str(symlink_tmpdir), "--assessment", "clean"]) == 1

    (design_tmpdir / ag.DESIGN_ASSESSMENT).unlink()
    sidecar = tmp_path / "assessment.input.sidecar"
    sidecar.write_text("Deviation\n", encoding="utf-8")

    def unreadable(_path: Path) -> str:
        raise OSError("unreadable")

    monkeypatch.setattr(ag, "_read_regular_text_no_follow", unreadable)
    assert ag.persist_design_assessment_main(["--repo-root", str(repo), "--design-tmpdir", str(design_tmpdir), "--assessment-file", str(sidecar)]) == 1
    assert not (design_tmpdir / ag.DESIGN_ASSESSMENT).exists()


def test_parse_guideline_entries_omits_bullets_after_non_entry_heading() -> None:
    parsed = ag.parse_guideline_entries(
        """### G-python-1: First entry
- Why: first why.
- Deviate when: first carve-out.

### Not a guideline entry
- Why: leaked why.
- Deviate when: leaked carve-out.

### G-skill-2: Second entry
- Why: second why.
- Deviate when: second carve-out.
"""
    )
    assert "leaked why" not in parsed
    assert "leaked carve-out" not in parsed
    assert "### G-python-1: First entry" in parsed
    assert "### G-skill-2: Second entry" in parsed
    assert "- Why: second why." in parsed


def test_pin_note_from_staged_rejects_fingerprint_mismatch(tmp_path: Path) -> None:
    tmpdir = tmp_path / "implement"
    ag.write_staged_assessment(
        implement_tmpdir=tmpdir,
        assessment_text="note\n",
        assessed_head_sha="head-a",
        diff_fingerprint_value="mismatch",
        base_ref="origin/main",
        diff_text="implementation diff",
    )
    assert not ag.pin_note_from_staged(tmpdir, head_sha="head-b", base_ref="origin/main")
    assert not ag.note_consumable(implement_tmpdir=tmpdir, head_sha="head-b")


def test_staged_assessment_present_requires_regular_present_artifacts(tmp_path: Path) -> None:
    tmpdir = tmp_path / "implement"
    ag.write_staged_assessment(
        implement_tmpdir=tmpdir,
        assessment_text="note\n",
        assessed_head_sha="head-a",
        diff_fingerprint_value=ag.diff_fingerprint("diff"),
        base_ref="origin/main",
        diff_text="diff",
    )
    assert ag.staged_assessment_present(tmpdir)

    missing = tmp_path / "missing"
    assert not ag.staged_assessment_present(missing)

    (tmpdir / ag.STAGED_ASSESSMENT_ENV).write_text("STATUS=absent\n", encoding="utf-8")
    assert not ag.staged_assessment_present(tmpdir)

    ag.write_staged_assessment(
        implement_tmpdir=tmpdir,
        assessment_text="note\n",
        assessed_head_sha="head-a",
        diff_fingerprint_value=ag.diff_fingerprint("diff"),
        base_ref="origin/main",
        diff_text="diff",
    )
    target = tmp_path / "staged-target.md"
    target.write_text("note\n", encoding="utf-8")
    (tmpdir / ag.STAGED_ASSESSMENT).unlink()
    (tmpdir / ag.STAGED_ASSESSMENT).symlink_to(target)
    assert not ag.staged_assessment_present(tmpdir)

    (tmpdir / ag.STAGED_ASSESSMENT).unlink()
    (tmpdir / ag.STAGED_ASSESSMENT).write_text("note\n", encoding="utf-8")
    sidecar_target = tmp_path / "sidecar.env"
    sidecar_target.write_text("STATUS=present\n", encoding="utf-8")
    (tmpdir / ag.STAGED_ASSESSMENT_ENV).unlink()
    (tmpdir / ag.STAGED_ASSESSMENT_ENV).symlink_to(sidecar_target)
    assert not ag.staged_assessment_present(tmpdir)


def test_durable_note_present_requires_regular_present_artifacts(tmp_path: Path) -> None:
    tmpdir = tmp_path / "implement"
    ag.write_implement_note(
        implement_tmpdir=tmpdir,
        note_text="note\n",
        head_sha="head",
        metadata={"ASSESSED_HEAD_SHA": "old", "DIFF_FINGERPRINT": ag.diff_fingerprint("diff")},
        base_ref="origin/main",
    )
    assert ag.durable_note_present(tmpdir)

    (tmpdir / ag.DURABLE_NOTE_ENV).write_text("STATUS=absent\n", encoding="utf-8")
    assert not ag.durable_note_present(tmpdir)

    (tmpdir / ag.DURABLE_NOTE_ENV).write_text("STATUS=present\n", encoding="utf-8")
    target = tmp_path / "note-target.md"
    target.write_text("note\n", encoding="utf-8")
    (tmpdir / ag.DURABLE_NOTE).unlink()
    (tmpdir / ag.DURABLE_NOTE).symlink_to(target)
    assert not ag.durable_note_present(tmpdir)


def test_dropped_notice_round_trips_and_survives_invalidation(tmp_path: Path) -> None:
    tmpdir = tmp_path / "implement"
    assert ag.persist_dropped_note_notice(tmpdir, notice_text="dropped\n")
    assert ag.read_dropped_note_notice(tmpdir) == "dropped"

    ag.write_staged_assessment(
        implement_tmpdir=tmpdir,
        assessment_text="note\n",
        assessed_head_sha="head-a",
        diff_fingerprint_value=ag.diff_fingerprint("diff"),
        base_ref="origin/main",
        diff_text="diff",
    )
    assert ag.pin_note_from_staged(tmpdir, head_sha="head-b", base_ref="origin/main")
    assert ag.durable_note_present(tmpdir)
    assert ag.persist_dropped_note_notice(tmpdir, notice_text="dropped\n")
    ag.invalidate_implement_note(tmpdir)
    assert ag.read_dropped_note_notice(tmpdir) == "dropped"
    assert not (tmpdir / ag.STAGED_ASSESSMENT).exists()
    assert not (tmpdir / ag.DURABLE_NOTE).exists()


def test_dropped_notice_persist_rejects_unwritable_target_shape(tmp_path: Path) -> None:
    tmpdir = tmp_path / "implement"
    (tmpdir / ag.DROPPED_NOTE_ARTIFACT).mkdir(parents=True)
    assert not ag.persist_dropped_note_notice(tmpdir, notice_text="dropped\n")
    assert ag.read_dropped_note_notice(tmpdir) == ""


def test_dropped_notice_cleared_by_successful_pin(tmp_path: Path) -> None:
    tmpdir = tmp_path / "implement"
    assert ag.persist_dropped_note_notice(tmpdir, notice_text="old marker\n")
    diff_text = "implementation diff"
    ag.write_staged_assessment(
        implement_tmpdir=tmpdir,
        assessment_text="fresh note\n",
        assessed_head_sha="old",
        diff_fingerprint_value=ag.diff_fingerprint(diff_text),
        base_ref="origin/main",
        diff_text=diff_text,
    )
    assert ag.pin_note_from_staged(tmpdir, head_sha="head", base_ref="origin/main")
    assert ag.note_consumable(implement_tmpdir=tmpdir, head_sha="head")
    assert ag.read_dropped_note_notice(tmpdir) == ""


def test_dropped_notice_clear_failure_does_not_block_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmpdir = tmp_path / "implement"
    assert ag.persist_dropped_note_notice(tmpdir, notice_text="old marker\n")
    original_unlink = Path.unlink

    def fail_marker_unlink(self: Path, *args: object, **kwargs: object) -> None:
        if self.name == ag.DROPPED_NOTE_ARTIFACT:
            raise OSError("blocked")
        original_unlink(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "unlink", fail_marker_unlink)
    ag.write_implement_note(
        implement_tmpdir=tmpdir,
        note_text="fresh note\n",
        head_sha="head",
        metadata={"ASSESSED_HEAD_SHA": "old", "DIFF_FINGERPRINT": ag.diff_fingerprint("diff")},
        base_ref="origin/main",
    )
    assert ag.note_consumable(implement_tmpdir=tmpdir, head_sha="head")
    assert ag.read_dropped_note_notice(tmpdir) == "old marker"


def test_maybe_persist_dropped_note_before_invalidate_paths(tmp_path: Path) -> None:
    tmpdir = tmp_path / "implement"
    assert not ag.maybe_persist_dropped_note_before_invalidate(tmpdir, redact_fn=lambda text: text)

    ag.write_implement_note(
        implement_tmpdir=tmpdir,
        note_text="note\n",
        head_sha="head",
        metadata={"ASSESSED_HEAD_SHA": "old", "DIFF_FINGERPRINT": ag.diff_fingerprint("diff")},
        base_ref="origin/main",
    )
    assert ag.maybe_persist_dropped_note_before_invalidate(tmpdir, redact_fn=lambda text: text)
    assert ag.read_dropped_note_notice(tmpdir) == ag.dropped_note_message()
    assert not ag.maybe_persist_dropped_note_before_invalidate(tmpdir, redact_fn=lambda _text: "replacement")
    assert ag.read_dropped_note_notice(tmpdir) == ag.dropped_note_message()

    ag.clear_dropped_note_notice(tmpdir)
    ag.invalidate_implement_note(tmpdir)
    ag.write_staged_assessment(
        implement_tmpdir=tmpdir,
        assessment_text="note\n",
        assessed_head_sha="head-a",
        diff_fingerprint_value=ag.diff_fingerprint("diff"),
        base_ref="origin/main",
        diff_text="diff",
    )
    assert ag.maybe_persist_dropped_note_before_invalidate(tmpdir, redact_fn=lambda text: text)


def test_maybe_persist_dropped_notice_returns_false_on_persist_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmpdir = tmp_path / "implement"
    ag.write_staged_assessment(
        implement_tmpdir=tmpdir,
        assessment_text="note\n",
        assessed_head_sha="head-a",
        diff_fingerprint_value=ag.diff_fingerprint("diff"),
        base_ref="origin/main",
        diff_text="diff",
    )

    def fail_persist(_implement_tmpdir: Path, *, notice_text: str) -> bool:
        del notice_text
        return False

    monkeypatch.setattr(ag, "persist_dropped_note_notice", fail_persist)
    assert not ag.maybe_persist_dropped_note_before_invalidate(tmpdir, redact_fn=lambda text: text)


def test_staged_fingerprint_valid_uses_live_diff_when_repo_available(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmpdir = tmp_path / "implement"
    staged_diff = "stale staged diff"
    live_diff = "current live diff"
    ag.write_staged_assessment(
        implement_tmpdir=tmpdir,
        assessment_text="note\n",
        assessed_head_sha="head-a",
        diff_fingerprint_value=ag.diff_fingerprint(staged_diff),
        base_ref="origin/main",
        diff_text=staged_diff,
    )
    repo = _repo(tmp_path / "git")

    def fake_materialize(*_args: object, **_kwargs: object) -> str:
        return live_diff

    monkeypatch.setattr(ag, "materialize_implementation_diff", fake_materialize)
    assert not ag.pin_note_from_staged(tmpdir, head_sha="head-b", base_ref="origin/main", repo_root=repo)


def test_refresh_staged_assessment_for_current_head_updates_staged_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmpdir = tmp_path / "implement"
    live_diff = "current live diff"
    ag.write_staged_assessment(
        implement_tmpdir=tmpdir,
        assessment_text="note\n",
        assessed_head_sha="head-a",
        diff_fingerprint_value=ag.diff_fingerprint(live_diff),
        base_ref="origin/main",
        diff_text="stale staged diff",
    )
    repo = _repo(tmp_path / "git")

    def fake_materialize(*_args: object, **_kwargs: object) -> str:
        return live_diff

    monkeypatch.setattr(ag, "materialize_implementation_diff", fake_materialize)

    assert ag.refresh_staged_assessment_for_current_head(
        tmpdir,
        head_sha="head-b",
        repo_root=repo,
    )
    assert (tmpdir / ag.MATERIALIZED_DIFF).read_text(encoding="utf-8") == live_diff
    sidecar = (tmpdir / ag.STAGED_ASSESSMENT_ENV).read_text(encoding="utf-8")
    assert f"DIFF_FINGERPRINT={ag.diff_fingerprint(live_diff)}" in sidecar
    assert "ASSESSED_HEAD_SHA=head-b" in sidecar
    assert ag.pin_note_from_staged(tmpdir, head_sha="head-b", base_ref="origin/main", repo_root=repo)
    assert ag.note_consumable(implement_tmpdir=tmpdir, head_sha="head-b")


def test_refresh_staged_assessment_for_current_head_returns_false_when_diff_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmpdir = tmp_path / "implement"
    staged_diff = "stale staged diff"
    live_diff = "current live diff"
    ag.write_staged_assessment(
        implement_tmpdir=tmpdir,
        assessment_text="note\n",
        assessed_head_sha="head-a",
        diff_fingerprint_value=ag.diff_fingerprint(staged_diff),
        base_ref="origin/main",
        diff_text=staged_diff,
    )
    repo = _repo(tmp_path / "git")

    def fake_materialize(*_args: object, **_kwargs: object) -> str:
        return live_diff

    monkeypatch.setattr(ag, "materialize_implementation_diff", fake_materialize)
    assert not ag.refresh_staged_assessment_for_current_head(
        tmpdir,
        head_sha="head-b",
        repo_root=repo,
    )


def test_materialize_live_diff_returns_none_on_os_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _repo(tmp_path / "git")

    def fail_materialize(*_args: object, **_kwargs: object) -> str:
        raise FileNotFoundError("repo root vanished")

    monkeypatch.setattr(ag, "materialize_implementation_diff", fail_materialize)
    assert ag._materialize_live_diff(repo_root=repo, resolved_base="origin/main") is None
    assert "ARCHITECTURAL_GUIDELINES_WARNING=repo root vanished" in capsys.readouterr().err


def test_refresh_staged_assessment_for_current_head_returns_false_when_missing_artifacts(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "git")
    assert not ag.refresh_staged_assessment_for_current_head(
        tmp_path / "missing",
        head_sha="head-b",
        base_ref="origin/main",
        repo_root=repo,
    )


def test_refresh_staged_assessment_for_current_head_returns_false_when_live_diff_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmpdir = tmp_path / "implement"
    ag.write_staged_assessment(
        implement_tmpdir=tmpdir,
        assessment_text="note\n",
        assessed_head_sha="head-a",
        diff_fingerprint_value=ag.diff_fingerprint("staged diff"),
        base_ref="origin/main",
        diff_text="staged diff",
    )
    repo = _repo(tmp_path / "git")

    def fail_materialize(*_args: object, **_kwargs: object) -> str:
        raise RuntimeError("missing remote ref")

    monkeypatch.setattr(ag, "materialize_implementation_diff", fail_materialize)
    assert not ag.refresh_staged_assessment_for_current_head(
        tmpdir,
        head_sha="head-b",
        base_ref="origin/main",
        repo_root=repo,
    )


def test_refresh_staged_assessment_for_current_head_returns_false_without_resolved_base(tmp_path: Path) -> None:
    tmpdir = tmp_path / "implement"
    ag.write_staged_assessment(
        implement_tmpdir=tmpdir,
        assessment_text="note\n",
        assessed_head_sha="head-a",
        diff_fingerprint_value=ag.diff_fingerprint("staged diff"),
        base_ref="",
        diff_text="staged diff",
    )
    repo = _repo(tmp_path / "git")
    assert not ag.refresh_staged_assessment_for_current_head(
        tmpdir,
        head_sha="head-b",
        repo_root=repo,
    )


def test_note_fingerprint_stale_returns_true_when_git_diff_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tmpdir = tmp_path / "implement"
    ag.write_staged_assessment(
        implement_tmpdir=tmpdir,
        assessment_text="note\n",
        assessed_head_sha="head-a",
        diff_fingerprint_value=ag.diff_fingerprint("diff"),
        base_ref="origin/main",
        diff_text="diff",
    )
    assert ag.pin_note_from_staged(tmpdir, head_sha="head-b", base_ref="origin/main")
    (tmpdir / ag.MATERIALIZED_DIFF).unlink()
    repo = _repo(tmp_path / "git")

    def fail_materialize(*_args: object, **_kwargs: object) -> str:
        msg = "missing remote ref"
        raise RuntimeError(msg)

    monkeypatch.setattr(ag, "materialize_implementation_diff", fail_materialize)
    assert ag.note_fingerprint_stale(tmpdir, base_ref="origin/main", repo_root=repo)
    assert "ARCHITECTURAL_GUIDELINES_WARNING=missing remote ref" in capsys.readouterr().err


def test_prepare_absent_emits_status_without_diff(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _repo(tmp_path)
    assert ag.prepare_main(["--repo-root", str(repo)]) == 0
    out = capsys.readouterr().out
    assert "ARCHITECTURAL_GUIDELINES_STATUS=absent" in out
    assert "ARCHITECTURAL_GUIDELINES_DIFF_STATUS" not in out


def test_prepare_invalid_emits_warning_without_diff(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _repo(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("### G-python-1: nope\n", encoding="utf-8")
    (repo / ag.GUIDELINES_FILENAME).symlink_to(outside)
    assert ag.prepare_main(["--repo-root", str(repo)]) == 0
    out = capsys.readouterr().out
    assert "ARCHITECTURAL_GUIDELINES_STATUS=invalid" in out
    assert "ARCHITECTURAL_GUIDELINES_WARNING=" in out
    assert "symlinks are not read" in out
    assert "ARCHITECTURAL_GUIDELINES_DIFF_STATUS" not in out


def test_prepare_present_emits_guidelines_and_diff(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _repo(tmp_path)
    (repo / ag.GUIDELINES_FILENAME).write_text(
        "### G-python-1: Escape <xml>\n- Why: token sk-" + "A" * 24 + "\n- Deviate when: never\n",
        encoding="utf-8",
    )
    (repo / "README.md").write_text("base\nchange\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "change")
    assert ag.prepare_main(["--repo-root", str(repo)]) == 0
    out = capsys.readouterr().out
    assert "ARCHITECTURAL_GUIDELINES_STATUS=present" in out
    assert f"ARCHITECTURAL_GUIDELINES_PATH={repo / ag.GUIDELINES_FILENAME}" in out
    assert '<architectural_guidelines encoding="literal-redacted">' in out
    assert "&lt;xml&gt;" in out
    assert "&lt;REDACTED-TOKEN&gt;" in out
    assert "ARCHITECTURAL_GUIDELINES_DIFF_STATUS=ok" in out
    assert "ARCHITECTURAL_GUIDELINES_BASE_REF=origin/main" in out
    assert "ARCHITECTURAL_GUIDELINES_DIFF_FINGERPRINT=" in out
    assert '<architectural_guidelines_diff encoding="literal-redacted">' in out
    assert "+change" in out


def test_prepare_present_writes_diff_snapshot_and_metadata(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _repo(tmp_path)
    tmpdir = tmp_path / "implement"
    (repo / ag.GUIDELINES_FILENAME).write_text(
        "### G-python-1: Keep small\n- Why: minimal change.\n- Deviate when: never\n",
        encoding="utf-8",
    )
    (repo / "README.md").write_text("base\nchange\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "change")
    assert ag.prepare_main(["--repo-root", str(repo), "--implement-tmpdir", str(tmpdir)]) == 0
    out = capsys.readouterr().out
    assert "ARCHITECTURAL_GUIDELINES_DIFF_STATUS=ok" in out
    diff_text = (tmpdir / ag.MATERIALIZED_DIFF).read_text(encoding="utf-8")
    assert "+change" in diff_text
    meta = (tmpdir / ag.MATERIALIZE_ENV).read_text(encoding="utf-8")
    assert "BASE_REF=origin/main" in meta
    assert f"DIFF_FINGERPRINT={ag.diff_fingerprint(diff_text)}" in meta


def test_prepare_present_diff_failure_returns_one(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _repo(tmp_path)
    (repo / ag.GUIDELINES_FILENAME).write_text(
        "### G-python-1: Keep small\n- Why: minimal change.\n- Deviate when: never\n",
        encoding="utf-8",
    )

    def fail_materialize(*_args: object, **_kwargs: object) -> str:
        raise RuntimeError("missing remote ref")

    monkeypatch.setattr(ag, "materialize_implementation_diff", fail_materialize)
    assert ag.prepare_main(["--repo-root", str(repo)]) == 1
    out = capsys.readouterr().out
    assert "ARCHITECTURAL_GUIDELINES_STATUS=present" in out
    assert "ARCHITECTURAL_GUIDELINES_DIFF_STATUS=failed" in out
    assert "ARCHITECTURAL_GUIDELINES_WARNING=missing remote ref" in out


def test_prepare_invalidates_stale_artifacts_before_reading(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _repo(tmp_path)
    tmpdir = tmp_path / "implement"
    ag.write_staged_assessment(
        implement_tmpdir=tmpdir,
        assessment_text="note\n",
        assessed_head_sha="head-a",
        diff_fingerprint_value=ag.diff_fingerprint("diff"),
        base_ref="origin/main",
        diff_text="diff",
    )
    ag.write_implement_note(
        implement_tmpdir=tmpdir,
        note_text="note\n",
        head_sha="head-b",
        metadata={"ASSESSED_HEAD_SHA": "head-a", "DIFF_FINGERPRINT": ag.diff_fingerprint("diff")},
        base_ref="origin/main",
    )
    assert ag.prepare_main(["--repo-root", str(repo), "--implement-tmpdir", str(tmpdir)]) == 0
    assert capsys.readouterr().out == "ARCHITECTURAL_GUIDELINES_STATUS=absent\n"
    assert not (tmpdir / ag.STAGED_ASSESSMENT).exists()
    assert not (tmpdir / ag.STAGED_ASSESSMENT_ENV).exists()
    assert not (tmpdir / ag.MATERIALIZED_DIFF).exists()
    assert not (tmpdir / ag.MATERIALIZE_ENV).exists()
    assert not (tmpdir / ag.DURABLE_NOTE).exists()
    assert not (tmpdir / ag.DURABLE_NOTE_ENV).exists()


def test_prepare_invalidation_failure_returns_two_without_read_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _repo(tmp_path)
    tmpdir = tmp_path / "implement"

    def fail_invalidate(_implement_tmpdir: Path) -> None:
        raise OSError("artifact survived")

    monkeypatch.setattr(ag, "invalidate_implement_note", fail_invalidate)
    assert ag.prepare_main(["--repo-root", str(repo), "--implement-tmpdir", str(tmpdir)]) == 2
    out = capsys.readouterr().out
    assert "ARCHITECTURAL_GUIDELINES_INVALIDATE_STATUS=failed" in out
    assert "ARCHITECTURAL_GUIDELINES_WARNING=artifact survived" in out
    assert "ARCHITECTURAL_GUIDELINES_STATUS" not in out


def test_cli_present_uses_untrusted_content_block(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _repo(tmp_path)
    (repo / ag.GUIDELINES_FILENAME).write_text(
        "### G-python-1: Escape <xml>\n- Why: token sk-" + "A" * 24 + "\n- Deviate when: never\n",
        encoding="utf-8",
    )
    assert ag.read_main(["--repo-root", str(repo)]) == 0
    out = capsys.readouterr().out
    assert "ARCHITECTURAL_GUIDELINES_STATUS=present" in out
    assert '<architectural_guidelines encoding="literal-redacted">' in out
    assert "&lt;xml&gt;" in out
    assert "&lt;REDACTED-TOKEN&gt;" in out


def test_present_note_pending_absent_emits_nothing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _repo(tmp_path)
    assert ag.present_note_main(["--repo-root", str(repo)]) == 0
    out = capsys.readouterr().out
    assert out == ""
    assert ag.GUIDELINES_DEVIATION_ASSESSMENT_REQUIRED not in out


def test_present_note_pending_invalid_emits_warning_without_assessment_marker(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _repo(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("### G-python-1: nope\n", encoding="utf-8")
    (repo / ag.GUIDELINES_FILENAME).symlink_to(outside)
    assert ag.present_note_main(["--repo-root", str(repo)]) == 0
    out = capsys.readouterr().out
    assert "ARCHITECTURAL_GUIDELINES_WARNING=" in out
    assert "symlinks are not read" in out
    assert ag.GUIDELINES_DEVIATION_ASSESSMENT_REQUIRED not in out


def test_present_note_pending_present_emits_content_and_assessment_marker(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _repo(tmp_path)
    (repo / ag.GUIDELINES_FILENAME).write_text(
        "### G-python-1: Escape <xml>\n- Why: token sk-" + "A" * 24 + "\n- Deviate when: never\n",
        encoding="utf-8",
    )
    assert ag.present_note_main(["--repo-root", str(repo)]) == 0
    out = capsys.readouterr().out
    assert f"ARCHITECTURAL_GUIDELINES_PATH={repo / ag.GUIDELINES_FILENAME}" in out
    assert '<architectural_guidelines encoding="literal-redacted">' in out
    assert "&lt;xml&gt;" in out
    assert "&lt;REDACTED-TOKEN&gt;" in out
    assert ag.GUIDELINES_DEVIATION_ASSESSMENT_REQUIRED in out


def test_present_note_clean_absent_emits_nothing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _repo(tmp_path)
    assert ag.present_note_main(["--repo-root", str(repo), "--assessment", "clean"]) == 0
    assert capsys.readouterr().out == ""


def test_present_note_clean_present_emits_only_clean_note(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _repo(tmp_path)
    (repo / ag.GUIDELINES_FILENAME).write_text(
        "### G-python-1: Keep small\n- Why: minimal change.\n- Deviate when: never\n",
        encoding="utf-8",
    )
    assert ag.present_note_main(["--repo-root", str(repo), "--assessment", "clean"]) == 0
    out = capsys.readouterr().out
    assert out == f"{ag.CLEAN_PRESENTATION_NOTE}\n"
    assert "ARCHITECTURAL_GUIDELINES_PATH" not in out
    assert "<architectural_guidelines" not in out
    assert "GUIDELINES_DEVIATION_ASSESSMENT_REQUIRED" not in out


def test_present_note_clean_invalid_emits_warning_only(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _repo(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("### G-python-1: nope\n", encoding="utf-8")
    (repo / ag.GUIDELINES_FILENAME).symlink_to(outside)
    assert ag.present_note_main(["--repo-root", str(repo), "--assessment", "clean"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("ARCHITECTURAL_GUIDELINES_WARNING=")
    assert "symlinks are not read" in out
    assert ag.CLEAN_PRESENTATION_NOTE not in out
    assert "GUIDELINES_DEVIATION_ASSESSMENT_REQUIRED" not in out


def test_claude_project_dir_preferred(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cwd_repo = _repo(tmp_path / "cwd")
    project_repo = _repo(tmp_path / "project")
    (project_repo / ag.GUIDELINES_FILENAME).write_text(
        "### G-python-1: Project wins\n- Why: explicit project dir.\n- Deviate when: never.\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(cwd_repo)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project_repo))
    result = ag.read_guidelines()
    assert result.status == "present"
    assert "Project wins" in result.content


def test_cwd_fallback_works(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _repo(tmp_path)
    (repo / ag.GUIDELINES_FILENAME).write_text(
        "### G-python-1: Cwd wins\n- Why: fallback.\n- Deviate when: never.\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.chdir(repo)
    assert ag.read_guidelines().status == "present"


def test_symlinked_guidelines_file_invalid(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("### G-python-1: nope\n", encoding="utf-8")
    (repo / ag.GUIDELINES_FILENAME).symlink_to(outside)
    result = ag.read_guidelines(repo_root=repo)
    assert result.status == "invalid"
    assert "symlinks" in result.warning


def test_materialize_diff_uses_upstream_for_forked_target(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "README.md").write_text("base\nchange\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "change")
    assert ag.resolve_diff_base(forked_target=True) == ("upstream", "main")
    diff_text = ag.materialize_implementation_diff(repo, base_remote="upstream", base_ref="main")
    assert "+change" in diff_text


def test_staged_pin_consumable_and_invalidate(tmp_path: Path) -> None:
    tmpdir = tmp_path / "implement"
    body = "Consulted ARCHITECTURAL_GUIDELINES.md; no deviations identified.\n"
    ag.write_staged_assessment(
        implement_tmpdir=tmpdir,
        assessment_text=body,
        assessed_head_sha="head-a",
        diff_fingerprint_value=ag.diff_fingerprint("diff"),
        base_ref="origin/main",
        diff_text="diff",
    )
    assert (tmpdir / ag.STAGED_ASSESSMENT).read_text(encoding="utf-8") == body
    assert (tmpdir / ag.MATERIALIZED_DIFF).read_text(encoding="utf-8") == "diff"
    assert not ag.note_consumable(implement_tmpdir=tmpdir, head_sha="head-b")
    assert ag.pin_note_from_staged(tmpdir, head_sha="head-b", base_ref="origin/main")
    assert ag.note_consumable(implement_tmpdir=tmpdir, head_sha="head-b")
    assert not ag.note_consumable(implement_tmpdir=tmpdir, head_sha="head-c")
    assert (tmpdir / ag.DURABLE_NOTE).read_text(encoding="utf-8") == body
    ag.invalidate_implement_note(tmpdir)
    assert not (tmpdir / ag.STAGED_ASSESSMENT).exists()
    assert not (tmpdir / ag.DURABLE_NOTE).exists()


def test_pr_prep_log_only_head_advance_keeps_body_bytes(tmp_path: Path) -> None:
    tmpdir = tmp_path / "implement"
    body = "Deviation warning body\n"
    ag.write_staged_assessment(
        implement_tmpdir=tmpdir,
        assessment_text=body,
        assessed_head_sha="N",
        diff_fingerprint_value=ag.diff_fingerprint("implementation diff"),
        base_ref="origin/main",
        diff_text="implementation diff",
    )
    assert ag.pin_note_from_staged(tmpdir, head_sha="N-plus-1", base_ref="origin/main")
    assert ag.note_consumable(implement_tmpdir=tmpdir, head_sha="N-plus-1")
    assert (tmpdir / ag.DURABLE_NOTE).read_bytes() == body.encode("utf-8")


def test_log_only_head_bump_pin_succeeds_with_repo_root(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "impl.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "impl.py")
    _git(repo, "commit", "-m", "impl")
    assessed_head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    ).stdout.strip()
    diff_text = ag.materialize_implementation_diff(repo, base_remote="origin", base_ref="main")
    tmpdir = tmp_path / "implement"
    body = "Deviation warning body\n"
    ag.write_staged_assessment(
        implement_tmpdir=tmpdir,
        assessment_text=body,
        assessed_head_sha=assessed_head,
        diff_fingerprint_value=ag.diff_fingerprint(diff_text),
        base_ref="origin/main",
        diff_text=diff_text,
    )
    log_dir = repo / "larch-logs" / "implement" / "run1"
    log_dir.mkdir(parents=True)
    (log_dir / "log.txt").write_text("log\n", encoding="utf-8")
    _git(repo, "add", "larch-logs")
    _git(repo, "commit", "-m", "logs only")
    new_head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    ).stdout.strip()
    assert ag.pin_note_from_staged(tmpdir, head_sha=new_head, base_ref="origin/main", repo_root=repo)
    assert ag.note_consumable(implement_tmpdir=tmpdir, head_sha=new_head)
# pyright: reportPrivateUsage=false
