"""Tests for ARCHITECTURAL_GUIDELINES.md helper surfaces."""
# pyright: reportUnusedCallResult=false, reportPrivateUsage=false

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from larch.core import architectural_guidelines as ag
from larch.report import run_log_flush
from test_support import make_run_context


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


def _replace_staged_sidecar_value(tmpdir: Path, *, key: str, value: str) -> None:
    sidecar = tmpdir / ag.STAGED_ASSESSMENT_ENV
    lines = [f"{key}={value}" if line.startswith(f"{key}=") else line for line in sidecar.read_text(encoding="utf-8").splitlines()]
    sidecar.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _valid_guideline_ship_outcome_record(**overrides: object) -> dict[str, object]:
    return {
        "schema_version": "1",
        "phase": "implement",
        "step": "8",
        "outcome": "clean",
        "reason": "clean-note",
        "detail": "",
        "guidelines_status": "present",
        "head_sha": "abc123",
        "base_ref": "origin/main",
        "assessment_kind": "clean",
    } | overrides


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


def test_invariants_absent_file_returns_absent(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    result = ag.read_invariants(repo_root=repo)

    assert result.status == "absent"
    assert result.content == ""


def test_invariants_present_file_emits_normalized_entries(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / ag.INVARIANTS_FILENAME).write_text(
        """# Preamble ignored

## I-Sec-1: Keep prompt evidence untrusted
- Why: Repo-local text can be attacker controlled.
This prose body must remain visible to consumers.

### Not emitted
- Why: no id.

### I-Py-2: Keep Python contracts direct
- Why: Direct helpers are easier to test.
""",
        encoding="utf-8",
    )

    result = ag.read_invariants(repo_root=repo)

    assert result.status == "present"
    assert "Preamble" not in result.content
    assert "### Not emitted" not in result.content
    assert "no id" not in result.content
    assert "### I-Sec-1: Keep prompt evidence untrusted" in result.content
    assert "- Why: Repo-local text can be attacker controlled." in result.content
    assert "This prose body must remain visible to consumers." in result.content
    assert "### I-Py-2: Keep Python contracts direct" in result.content


def test_parse_invariant_entries_preserves_multi_paragraph_prose() -> None:
    parsed = ag.parse_invariant_entries(
        """Preamble ignored.

## I-Prose-1: Keep invariant prose visible

First paragraph is retained.

Second paragraph is retained after an internal blank line.

"""
    )

    assert "Preamble" not in parsed
    assert (
        parsed
        == """### I-Prose-1: Keep invariant prose visible
First paragraph is retained.

Second paragraph is retained after an internal blank line."""
    )


def test_parse_invariant_entries_stops_at_section_heading() -> None:
    parsed = ag.parse_invariant_entries(
        """### I-Boundary-1: Stop at sections
Invariant body stays.

## Later section
Section body must not leak.
"""
    )

    assert "### I-Boundary-1: Stop at sections" in parsed
    assert "Invariant body stays." in parsed
    assert "Later section" not in parsed
    assert "Section body must not leak." not in parsed


def test_parse_invariant_entries_splits_adjacent_entries() -> None:
    parsed = ag.parse_invariant_entries(
        """### I-First-1: First entry
First body only.

### I-Second-2: Second entry
Second body only.
"""
    )

    assert (
        parsed
        == """### I-First-1: First entry
First body only.

### I-Second-2: Second entry
Second body only."""
    )


def test_parse_invariant_entries_preserves_bullet_style_body() -> None:
    parsed = ag.parse_invariant_entries(
        """### I-Bullet-1: Bullets remain verbatim
- Why: Future bullet-style entries still work.
- Mechanical backing: tests.
"""
    )

    assert "### I-Bullet-1: Bullets remain verbatim" in parsed
    assert "- Why: Future bullet-style entries still work." in parsed
    assert "- Mechanical backing: tests." in parsed


def test_parse_invariant_entries_preserves_seeded_invariant_bodies() -> None:
    seeded_invariants_fixture: str = """# Architectural Invariants

Absolute invariants: rules that must always hold, with no legitimate exception.
Unlike the aspirational entries in `ARCHITECTURAL_GUIDELINES.md`, an invariant
has no "Deviate when" clause, and any violation is a defect. Where an invariant
can be enforced mechanically, back it with a lint, hook, or test; this file is
the human-readable specification, not a replacement for those checks.

## Workflow integrity

### I-Gate-1: A gate never disarms on data authored by the gated entity

A hard gate (a size trigger, a publish gate, a safety check) must not be
suppressed, weakened, or disarmed solely by metadata that the gated entity
itself declared, such as a drafting model's self-reported `diff_added` or
`mechanical_churn`. Disarming a hard gate requires independently computed
evidence or an explicit operator decision recorded in run state. Self-declared
metadata may soften presentation, never the trigger condition. Evidence of
violation: a gate whose disarm inputs are all writable by the entity under
evaluation (#6542, #6524).

### I-Pause-1: A pause snapshot contains every artifact a resume guard reads

The /design pause snapshot must include every file and sentinel that any
resume-path guard or validator reads to corroborate prior progress, including
the `.completed/` step sentinels. When a guard gains a new required artifact,
the snapshot allowlist changes in the same commit. A resume that false-refuses
on an artifact the pause omitted is a defect of the snapshot, not of the guard
(#6548). Mechanical backing: the pause snapshot regression tests in
`python/tests/design/test_design_pause.py` cover `.completed/` inclusion;
extend them when the guard-read artifact set grows.

## Run-log integrity

### I-Flush-1: A missing required run-log artifact is a recorded execution issue, never a silent status string

Every run-log flush must either commit the run's required artifact set (session
transcript, voted-finding bodies, final report) or record the omission as a
category-keyed execution issue that flushes into the committed run log. A
capture failure that exists only as a status value inside the session tmpdir is
invisible to every audit surface and is a defect of the flush, not acceptable
drift. Evidence of violation: every post-migration /implement run recorded
`SESSION_TRANSCRIPT_STATUS=write-failed` with no execution issue while runs
completed green (#6263), and rejected and neutral finding bodies were absent
from committed logs with nothing recorded anywhere (#6027). Mechanical backing:
a post-flush manifest completeness check that asserts the expected artifact set,
or its recorded execution-issue entries, before the run-log commit, with
regression tests in `python/tests/report/test_run_log_flush.py`.

## Agent contracts

### I-Agent-1: A machine-ingested agent verdict is backed by evidence the agent actually read

An agent whose output is machine-parsed (JSONL verdicts, vote rows, manifests)
must either read its evidence through its own tools or emit the designated
cannot-read outcome for that item. It must never emit well-formed output for
evidence it could not open. A dispatch that inlines evidence must fit the
worst case computed from the owning cap constants; when it cannot, it passes
paths and grants a Read tool. Evidence of violation: a toolless triage agent
play-acted tool calls and fabricated JSONL verdicts, and the dispatching
skill's inlining assumption failed at the configured caps (#6671). Mechanical
backing: `python3 python/cli.py lint agent-tool-contract` over agent
frontmatter, plus fail-closed prompt language in the triage agent definition.
"""
    parsed = ag.parse_invariant_entries(seeded_invariants_fixture)

    assert "### I-Gate-1: A gate never disarms on data authored by the gated entity" in parsed
    assert "### I-Pause-1: A pause snapshot contains every artifact a resume guard reads" in parsed
    assert "### I-Flush-1: A missing required run-log artifact is a recorded execution issue, never a silent status string" in parsed
    assert "### I-Agent-1: A machine-ingested agent verdict is backed by evidence the agent actually read" in parsed
    assert "A hard gate" in parsed
    assert "Evidence of violation:" in parsed
    assert "Mechanical backing:" in parsed


def test_invariants_present_with_no_entries_counts_present(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / ag.INVARIANTS_FILENAME).write_text("# Architectural Invariants\n\n_No entries yet._\n", encoding="utf-8")

    result = ag.read_invariants(repo_root=repo)

    assert result.status == "present"
    assert result.content == ""
    assert ag.architectural_knowledge_required(repo_root=repo)


def test_invariants_invalid_symlink_directory_and_utf8(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    target = tmp_path / "target.md"
    target.write_text("### I-Test-1: outside\n", encoding="utf-8")
    (repo / ag.INVARIANTS_FILENAME).symlink_to(target)

    result = ag.read_invariants(repo_root=repo)

    assert result.status == "invalid"
    assert "symlinks are not read" in result.warning

    (repo / ag.INVARIANTS_FILENAME).unlink()
    (repo / ag.INVARIANTS_FILENAME).mkdir()
    result = ag.read_invariants(repo_root=repo)
    assert result.status == "invalid"
    assert "found a directory" in result.warning

    (repo / ag.INVARIANTS_FILENAME).rmdir()
    (repo / ag.INVARIANTS_FILENAME).write_bytes(b"\xff\xfe\x00")
    result = ag.read_invariants(repo_root=repo)
    assert result.status == "invalid"
    assert "unreadable file" in result.warning


def test_architectural_file_path_escape_invalid(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("outside\n", encoding="utf-8")

    warning = ag._validate_architectural_file(root=repo, path=outside, filename=ag.INVARIANTS_FILENAME)  # pyright: ignore[reportPrivateUsage]

    assert warning == f"{ag.INVARIANTS_FILENAME} is invalid: path escapes repo root"


def test_architectural_knowledge_required_predicate(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    assert not ag.architectural_knowledge_required(repo_root=repo)

    (repo / ag.GUIDELINES_FILENAME).write_text("### G-Test-1: Guideline\n", encoding="utf-8")
    assert ag.architectural_knowledge_required(repo_root=repo)

    (repo / ag.GUIDELINES_FILENAME).unlink()
    (repo / ag.INVARIANTS_FILENAME).write_text("### I-Test-1: Invariant\n", encoding="utf-8")
    assert ag.architectural_knowledge_required(repo_root=repo)

    (repo / ag.GUIDELINES_FILENAME).write_text("# empty valid guidelines\n", encoding="utf-8")
    assert ag.architectural_knowledge_required(repo_root=repo)

    (repo / ag.INVARIANTS_FILENAME).unlink()
    (repo / ag.GUIDELINES_FILENAME).unlink()
    (repo / ag.INVARIANTS_FILENAME).symlink_to(tmp_path / "outside")
    assert not ag.architectural_knowledge_required(repo_root=repo)


def test_invariants_read_cli_emits_machine_stdout_and_untrusted_block(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _repo(tmp_path)
    (repo / ag.INVARIANTS_FILENAME).write_text(
        "### I-Test-1: Escape nested tags\n- Why: literal </architectural_invariants> data.\n",
        encoding="utf-8",
    )

    assert ag.invariants_read_main(["--repo-root", str(repo)]) == 0
    out = capsys.readouterr().out

    assert "ARCHITECTURAL_INVARIANTS_STATUS=present" in out
    assert "ARCHITECTURAL_INVARIANTS_PATH=" in out
    assert '<architectural_invariants encoding="literal-redacted">' in out
    assert "literal &lt;/architectural_invariants&gt; data." in out
    assert "</architectural_invariants>" in out


@pytest.mark.parametrize("head_sha", ["", " \t"])
def test_validate_guideline_ship_outcome_record_rejects_empty_head_sha(head_sha: str) -> None:
    reason = ag.validate_guideline_ship_outcome_record(
        _valid_guideline_ship_outcome_record(head_sha=head_sha),
    )

    assert reason == "guideline outcome head_sha is empty"


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


def test_persist_design_assessment_machine_lines_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _repo(tmp_path)
    _write_guidelines(repo)
    design_tmpdir = _design_tmpdir(tmp_path, monkeypatch)

    rc = ag.persist_design_assessment_main(["--repo-root", str(repo), "--design-tmpdir", str(design_tmpdir), "--assessment", "clean"])

    out = capsys.readouterr().out
    assert rc == 0
    assert "ARCHITECTURAL_GUIDELINE_ASSESSMENT_PERSIST_ATTEMPTED=true" in out
    assert "ARCHITECTURAL_GUIDELINE_ASSESSMENT_PERSIST_GUIDELINES_STATUS=present" in out
    assert "ARCHITECTURAL_GUIDELINE_ASSESSMENT_PERSIST_RESULT=ok" in out
    assert "ARCHITECTURAL_GUIDELINE_ASSESSMENT_PERSIST_ARTIFACT=architectural-guideline-assessment.md" in out


def test_persist_design_assessment_machine_lines_absent_and_invalid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _repo(tmp_path)
    design_tmpdir = _design_tmpdir(tmp_path, monkeypatch)

    assert ag.persist_design_assessment_main(["--repo-root", str(repo), "--design-tmpdir", str(design_tmpdir)]) == 0
    absent_out = capsys.readouterr().out
    assert "ARCHITECTURAL_GUIDELINE_ASSESSMENT_PERSIST_GUIDELINES_STATUS=absent" in absent_out
    assert "ARCHITECTURAL_GUIDELINE_ASSESSMENT_PERSIST_RESULT=ok" in absent_out
    assert "ARCHITECTURAL_GUIDELINE_ASSESSMENT_PERSIST_REASON=not-required" in absent_out

    (repo / ag.GUIDELINES_FILENAME).mkdir()
    assert ag.persist_design_assessment_main(["--repo-root", str(repo), "--design-tmpdir", str(design_tmpdir)]) == 0
    invalid_out = capsys.readouterr().out
    assert "ARCHITECTURAL_GUIDELINE_ASSESSMENT_PERSIST_GUIDELINES_STATUS=invalid" in invalid_out
    assert "ARCHITECTURAL_GUIDELINE_ASSESSMENT_PERSIST_RESULT=ok" in invalid_out


def test_persist_design_assessment_machine_lines_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _repo(tmp_path)
    _write_guidelines(repo)
    design_tmpdir = _design_tmpdir(tmp_path, monkeypatch)

    rc = ag.persist_design_assessment_main(["--repo-root", str(repo), "--design-tmpdir", str(design_tmpdir)])

    out = capsys.readouterr().out
    assert rc == 1
    assert "ARCHITECTURAL_GUIDELINE_ASSESSMENT_PERSIST_ATTEMPTED=true" in out
    assert "ARCHITECTURAL_GUIDELINE_ASSESSMENT_PERSIST_RESULT=failed" in out


def test_skip_approve_sequence_uses_explicit_repo_root_from_wrong_cwd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _repo(tmp_path)
    _write_guidelines(repo)
    design_tmpdir = _design_tmpdir(tmp_path, monkeypatch)
    cache_cwd = tmp_path / "plugin-cache"
    cache_cwd.mkdir()
    monkeypatch.chdir(cache_cwd)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)

    assert ag.read_guidelines().status == "absent"
    assert ag.present_note_main(["--repo-root", str(repo)]) == 0
    presented = capsys.readouterr().out
    assert ag.GUIDELINES_DEVIATION_ASSESSMENT_REQUIRED in presented
    assert ag.present_note_main(["--repo-root", str(repo), "--assessment", "clean"]) == 0
    assert ag.persist_design_assessment_main(["--repo-root", str(repo), "--design-tmpdir", str(design_tmpdir), "--assessment", "clean"]) == 0
    assert (design_tmpdir / ag.DESIGN_ASSESSMENT).read_text(encoding="utf-8") == ag.CLEAN_PRESENTATION_NOTE + "\n"


def test_skip_approve_guideline_prompt_contracts_bind_repo_root() -> None:
    root = Path(__file__).resolve().parents[3]
    approval = (root / "skills" / "design" / "references" / "approval-gates-gate-c.md").read_text(encoding="utf-8")
    skill = (root / "skills" / "design" / "SKILL.md").read_text(encoding="utf-8")
    outline = (root / "skills" / "design" / "references" / "design-outline.md").read_text(encoding="utf-8")

    assert '. "$DESIGN_TMPDIR/source-env.sh"' in approval
    assert 'present-note --repo-root "$REPO_ROOT"' in approval
    assert 'persist-design-assessment --repo-root "$REPO_ROOT"' in approval
    assert 'architectural-invariants persist-design-assessment --repo-root "$REPO_ROOT"' in approval
    assert approval.index('architectural-invariants persist-design-assessment --repo-root "$REPO_ROOT"') < approval.index('architectural-guidelines persist-design-assessment --repo-root "$REPO_ROOT"')
    assert "**Absent, invalid, or present-but-empty**: when `read_invariants().status` is not `present` or parsed `content.strip()` is empty after parsing `I-*` entries." in approval
    assert "**Clean**: only when invariants are `present` with parsed non-empty content and no violation assessment was required (no `INVARIANTS_VIOLATION_ASSESSMENT_REQUIRED=true` path and no remediated-violations sidecar)." in approval
    assert "**Remediated-violations**: when violations were identified and the remediation loop produced a clean plan." in approval
    assert "If invariant present-note emits `INVARIANTS_VIOLATION_ASSESSMENT_REQUIRED=true`, assess the parsed untrusted entries against the complete on-disk `$DESIGN_TMPDIR/plan.txt`, not the chat preview." in approval
    assert approval.index("INVARIANTS_VIOLATION_ASSESSMENT_REQUIRED=true") < approval.index("**Clean**: only when invariants are `present`")
    assert "reason=persist-design-assessment-failed" in approval
    assert approval.index("reason=persist-design-assessment-failed") < approval.index("Do not fire `AskUserQuestion`, approve, auto-approve, or transition to Step 5.")
    assert "**Step 5c missing-invariant-assessment.**" in skill
    assert skill.index("**Step 5c missing-invariant-assessment.**") < skill.index("**Step 5c missing-guideline-assessment.**")
    assert '. "$DESIGN_TMPDIR/source-env.sh"' in outline
    assert 'present-note --repo-root "$REPO_ROOT"' in outline
    assert "auto-approved (--skip-approve)" in outline


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


def test_parse_guideline_entries_slims_marked_guideline_to_mechanized_line() -> None:
    parsed = ag.parse_guideline_entries(
        """### G-Cfg-1: Define config literals once
- Mechanized: `python3 python/cli.py lint env-via-config-constant` covers env-var literals only.
- Why: this must not appear.
- Deviate when: this carve-out must not appear.
"""
    )

    assert (
        parsed
        == """### G-Cfg-1: Define config literals once
- Mechanized: `python3 python/cli.py lint env-via-config-constant` covers env-var literals only."""
    )


def test_parse_guideline_entries_ignores_mechanized_line_outside_guideline() -> None:
    parsed = ag.parse_guideline_entries(
        """- Mechanized: outside entries must not create output.

### Notes
- Mechanized: section bullets must not create output.

### G-Bash-3: Keep shell scripts portable
- Why: portability matters.
- Deviate when: a script documents a narrower runtime.
"""
    )

    assert (
        parsed
        == """### G-Bash-3: Keep shell scripts portable
- Why: portability matters.
- Deviate when: a script documents a narrower runtime."""
    )


def test_parse_guideline_entries_preserves_unmarked_guideline_normalization() -> None:
    parsed = ag.parse_guideline_entries(
        """Preamble ignored.

### G-Py-4: Fail loudly
- Why: loud failure preserves auditability.
- Guidance: extra guidance is intentionally omitted.
- Deviate when: a documented degraded path exists.
"""
    )

    assert (
        parsed
        == """### G-Py-4: Fail loudly
- Why: loud failure preserves auditability.
- Deviate when: a documented degraded path exists."""
    )


def test_parse_guideline_entries_mixes_marked_and_unmarked_entries_in_order() -> None:
    parsed = ag.parse_guideline_entries(
        """### G-Py-4: Fail loudly
- Why: loud failure preserves auditability.
- Deviate when: a documented degraded path exists.

### G-Bash-3: Keep shell scripts portable
- Why: this must not appear.
- Mechanized: `make lint-bash32` covers Bash 3.2 constructs.
- Deviate when: this carve-out must not appear.

### G-Obs-3: Record execution issues
- Why: tmpdir-only failures vanish.
- Deviate when: no committed log exists.
"""
    )

    assert (
        parsed
        == """### G-Py-4: Fail loudly
- Why: loud failure preserves auditability.
- Deviate when: a documented degraded path exists.

### G-Bash-3: Keep shell scripts portable
- Mechanized: `make lint-bash32` covers Bash 3.2 constructs.

### G-Obs-3: Record execution issues
- Why: tmpdir-only failures vanish.
- Deviate when: no committed log exists."""
    )


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


def test_note_readable_any_head_accepts_present_durable_note_with_mismatched_head(tmp_path: Path) -> None:
    tmpdir = tmp_path / "implement"
    ag.write_implement_note(
        implement_tmpdir=tmpdir,
        note_text="note\n",
        head_sha="other",
        metadata={"ASSESSED_HEAD_SHA": "old", "DIFF_FINGERPRINT": ag.diff_fingerprint("diff")},
        base_ref="origin/main",
    )

    assert ag.note_readable_any_head(tmpdir)


def test_note_readable_any_head_rejects_non_present_status(tmp_path: Path) -> None:
    tmpdir = tmp_path / "implement"
    ag.write_implement_note(
        implement_tmpdir=tmpdir,
        note_text="note\n",
        head_sha="head",
        metadata={"ASSESSED_HEAD_SHA": "old", "DIFF_FINGERPRINT": ag.diff_fingerprint("diff")},
        base_ref="origin/main",
    )

    (tmpdir / ag.DURABLE_NOTE_ENV).write_text("STATUS=absent\nHEAD_SHA=other\n", encoding="utf-8")

    assert not ag.note_readable_any_head(tmpdir)


def test_note_readable_any_head_rejects_symlinked_durable_artifacts(tmp_path: Path) -> None:
    note_tmpdir = tmp_path / "note"
    ag.write_implement_note(
        implement_tmpdir=note_tmpdir,
        note_text="note\n",
        head_sha="head",
        metadata={"ASSESSED_HEAD_SHA": "old", "DIFF_FINGERPRINT": ag.diff_fingerprint("diff")},
        base_ref="origin/main",
    )
    note_target = tmp_path / "note-target.md"
    note_target.write_text("note\n", encoding="utf-8")
    (note_tmpdir / ag.DURABLE_NOTE).unlink()
    (note_tmpdir / ag.DURABLE_NOTE).symlink_to(note_target)

    meta_tmpdir = tmp_path / "meta"
    ag.write_implement_note(
        implement_tmpdir=meta_tmpdir,
        note_text="note\n",
        head_sha="head",
        metadata={"ASSESSED_HEAD_SHA": "old", "DIFF_FINGERPRINT": ag.diff_fingerprint("diff")},
        base_ref="origin/main",
    )
    meta_target = tmp_path / "meta-target.env"
    meta_target.write_text("STATUS=present\nHEAD_SHA=head\n", encoding="utf-8")
    (meta_tmpdir / ag.DURABLE_NOTE_ENV).unlink()
    (meta_tmpdir / ag.DURABLE_NOTE_ENV).symlink_to(meta_target)

    assert not ag.note_readable_any_head(note_tmpdir)
    assert not ag.note_readable_any_head(meta_tmpdir)


def test_dropped_notice_round_trips_and_clears_on_invalidation(tmp_path: Path) -> None:
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
    assert ag.read_dropped_note_notice(tmpdir) == ""
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
    assert not ag.maybe_persist_dropped_note_before_invalidate(tmpdir, redact_fn=lambda text: text)
    assert ag.read_dropped_note_notice(tmpdir) == ""
    assert not ag.maybe_persist_dropped_note_before_invalidate(tmpdir, redact_fn=lambda _text: "replacement")
    assert ag.read_dropped_note_notice(tmpdir) == ""

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
    assert not ag.maybe_persist_dropped_note_before_invalidate(tmpdir, redact_fn=lambda text: text)


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


def test_refresh_staged_assessment_for_current_head_recovers_when_diff_changes(
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


def test_pin_note_from_staged_for_current_head_refreshes_from_live_diff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmpdir = tmp_path / "implement"
    staged_diff = "stale staged diff"
    live_diff = "current live diff"
    live_fingerprint = ag.diff_fingerprint(live_diff)
    ag.write_staged_assessment(
        implement_tmpdir=tmpdir,
        assessment_text="note\n",
        assessed_head_sha="head-a",
        diff_fingerprint_value=ag.diff_fingerprint(staged_diff),
        base_ref="origin/main",
        diff_text=staged_diff,
    )
    repo = _repo(tmp_path / "git")
    materialize_mock = Mock(return_value=live_diff)
    monkeypatch.setattr(ag, "materialize_implementation_diff", materialize_mock)

    assert ag.pin_note_from_staged_for_current_head(
        tmpdir,
        head_sha="head-b",
        base_ref="origin/main",
        repo_root=repo,
    )

    materialize_mock.assert_called_once_with(repo, base_remote="origin", base_ref="main")
    assert (tmpdir / ag.MATERIALIZED_DIFF).read_text(encoding="utf-8") == live_diff
    assert not (tmpdir / ag.STAGED_ASSESSMENT_ENV).exists()
    durable_metadata = ag.durable_note_metadata(tmpdir)
    assert durable_metadata["HEAD_SHA"] == "head-b"
    assert durable_metadata["ASSESSED_HEAD_SHA"] == "head-b"
    assert durable_metadata["DIFF_FINGERPRINT"] == live_fingerprint
    assert ag.note_consumable(implement_tmpdir=tmpdir, head_sha="head-b")


def test_pin_note_from_staged_for_current_head_empty_fingerprint_fails_after_live_materialize(
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
    _replace_staged_sidecar_value(tmpdir, key="DIFF_FINGERPRINT", value="")
    repo = _repo(tmp_path / "git")
    materialize_mock = Mock(return_value=live_diff)
    monkeypatch.setattr(ag, "materialize_implementation_diff", materialize_mock)

    assert not ag.pin_note_from_staged_for_current_head(
        tmpdir,
        head_sha="head-b",
        base_ref="origin/main",
        repo_root=repo,
    )

    materialize_mock.assert_called_once_with(repo, base_remote="origin", base_ref="main")
    assert not ag.note_consumable(implement_tmpdir=tmpdir, head_sha="head-b")


def test_pin_note_from_live_diff_refreshes_staged_and_durable_metadata(tmp_path: Path) -> None:
    tmpdir = tmp_path / "implement"
    live_diff = "current live diff"
    live_fingerprint = ag.diff_fingerprint(live_diff)
    ag.write_staged_assessment(
        implement_tmpdir=tmpdir,
        assessment_text="note\n",
        assessed_head_sha="head-a",
        diff_fingerprint_value=ag.diff_fingerprint("stale staged diff"),
        base_ref="origin/main",
        diff_text="stale staged diff",
    )

    assert ag._pin_note_from_live_diff(
        implement_tmpdir=tmpdir,
        head_sha="head-b",
        resolved_base="origin/main",
        live_diff=(live_diff, live_fingerprint),
    )

    assert (tmpdir / ag.MATERIALIZED_DIFF).read_text(encoding="utf-8") == live_diff
    assert not (tmpdir / ag.STAGED_ASSESSMENT_ENV).exists()
    durable_metadata = ag.durable_note_metadata(tmpdir)
    assert durable_metadata["HEAD_SHA"] == "head-b"
    assert durable_metadata["ASSESSED_HEAD_SHA"] == "head-b"
    assert durable_metadata["DIFF_FINGERPRINT"] == live_fingerprint
    assert durable_metadata["BASE_REF"] == "origin/main"


def test_pin_note_from_live_diff_returns_false_on_durable_write_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmpdir = tmp_path / "implement"
    live_diff = "current live diff"
    live_fingerprint = ag.diff_fingerprint(live_diff)
    ag.write_staged_assessment(
        implement_tmpdir=tmpdir,
        assessment_text="note\n",
        assessed_head_sha="head-a",
        diff_fingerprint_value=ag.diff_fingerprint("stale staged diff"),
        base_ref="origin/main",
        diff_text="stale staged diff",
    )

    def fail_write_note(**_kwargs: object) -> None:
        raise OSError("durable write failed")

    monkeypatch.setattr(ag, "write_implement_note", fail_write_note)

    assert not ag._pin_note_from_live_diff(
        implement_tmpdir=tmpdir,
        head_sha="head-b",
        resolved_base="origin/main",
        live_diff=(live_diff, live_fingerprint),
    )
    assert not ag.note_consumable(implement_tmpdir=tmpdir, head_sha="head-b")


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


def test_note_fingerprint_stale_ignores_stale_snapshot_when_base_moves(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path / "git")
    (repo / "README.md").write_text("base\nfeature\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "feature")
    head_sha = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    ).stdout.strip()
    diff_text = ag.materialize_implementation_diff(repo, base_remote="origin", base_ref="main")
    tmpdir = tmp_path / "implement"
    ag.write_implement_note(
        implement_tmpdir=tmpdir,
        note_text="fresh note\n",
        head_sha=head_sha,
        metadata={
            "ASSESSED_HEAD_SHA": head_sha,
            "DIFF_FINGERPRINT": ag.diff_fingerprint(diff_text),
            "BASE_REF": "origin/main",
        },
        base_ref="origin/main",
    )
    (tmpdir / ag.MATERIALIZED_DIFF).write_text(diff_text, encoding="utf-8")
    tree_sha = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD^{tree}"],
        text=True,
        capture_output=True,
        check=False,
    ).stdout.strip()
    moved_main = subprocess.run(
        ["git", "-C", str(repo), "commit-tree", tree_sha, "-p", head_sha, "-m", "move main"],
        text=True,
        capture_output=True,
        check=False,
    ).stdout.strip()
    assert moved_main
    _git(repo, "update-ref", "refs/remotes/origin/main", moved_main)
    _git(repo, "update-ref", "refs/remotes/upstream/main", moved_main)

    assert ag.note_fingerprint_stale(tmpdir, base_ref="origin/main", repo_root=repo)


def test_prepare_compose_assessment_rematerializes_when_durable_note_fingerprint_stale(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path / "git")
    (repo / ag.GUIDELINES_FILENAME).write_text(
        "### G-python-1: Keep small\n- Why: minimal change.\n- Deviate when: never\n",
        encoding="utf-8",
    )
    (repo / "README.md").write_text("base\nfirst change\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "change-a")
    head_sha = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    ).stdout.strip()
    diff_text = ag.materialize_implementation_diff(repo, base_remote="origin", base_ref="main")
    tmpdir = tmp_path / "implement"
    ag.write_implement_note(
        implement_tmpdir=tmpdir,
        note_text="fresh note\n",
        head_sha=head_sha,
        metadata={
            "ASSESSED_HEAD_SHA": head_sha,
            "DIFF_FINGERPRINT": ag.diff_fingerprint(diff_text),
            "BASE_REF": "origin/main",
        },
        base_ref="origin/main",
    )
    tree_sha = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD^{tree}"],
        text=True,
        capture_output=True,
        check=False,
    ).stdout.strip()
    moved_main = subprocess.run(
        ["git", "-C", str(repo), "commit-tree", tree_sha, "-p", head_sha, "-m", "move main"],
        text=True,
        capture_output=True,
        check=False,
    ).stdout.strip()
    assert moved_main
    _git(repo, "update-ref", "refs/remotes/origin/main", moved_main)
    _git(repo, "update-ref", "refs/remotes/upstream/main", moved_main)

    result = ag.prepare_compose_assessment(
        implement_tmpdir=tmpdir,
        repo_root=repo,
        expected_head_sha=head_sha,
    )

    assert result.status == "assessment-required"
    assert result.head_sha == head_sha
    assert result.base_ref == "origin/main"
    assert result.diff_fingerprint == ag.diff_fingerprint("")
    assert (tmpdir / ag.MATERIALIZED_DIFF).read_text(encoding="utf-8") == ""


def test_write_compose_assessment_persists_durable_note(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "git")
    (repo / ag.GUIDELINES_FILENAME).write_text(
        "### G-python-1: Keep small\n- Why: minimal change.\n- Deviate when: never\n",
        encoding="utf-8",
    )
    (repo / "README.md").write_text("base\ncompose\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "compose")
    head_sha = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    ).stdout.strip()
    tmpdir = tmp_path / "implement"

    assert ag.prepare_compose_assessment(implement_tmpdir=tmpdir, repo_root=repo, expected_head_sha=head_sha).status == "assessment-required"
    ag.write_compose_assessment(implement_tmpdir=tmpdir, assessment_text="Compose assessment", repo_root=repo)

    assert (tmpdir / ag.DURABLE_NOTE).read_text(encoding="utf-8") == "Compose assessment\n"
    assert ag.note_consumable(implement_tmpdir=tmpdir, head_sha=head_sha)


def test_write_compose_assessment_rejects_head_drift(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "git")
    (repo / ag.GUIDELINES_FILENAME).write_text(
        "### G-python-1: Keep small\n- Why: minimal change.\n- Deviate when: never\n",
        encoding="utf-8",
    )
    (repo / "README.md").write_text("base\ncompose\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "compose")
    head_sha = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    ).stdout.strip()
    tmpdir = tmp_path / "implement"

    assert ag.prepare_compose_assessment(implement_tmpdir=tmpdir, repo_root=repo, expected_head_sha=head_sha).status == "assessment-required"
    (repo / "README.md").write_text("base\ncompose\nfollow-up\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "drift")

    with pytest.raises(ValueError, match="HEAD changed after compose materialization"):
        ag.write_compose_assessment(implement_tmpdir=tmpdir, assessment_text="Compose assessment", repo_root=repo)


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
    (tmpdir / ag.MATERIALIZED_DIFF).write_text("snapshot\n", encoding="utf-8")
    (tmpdir / ag.MATERIALIZE_ENV).write_text("STATUS=present\n", encoding="utf-8")
    assert ag.prepare_main(["--repo-root", str(repo), "--implement-tmpdir", str(tmpdir)]) == 0
    assert capsys.readouterr().out == "ARCHITECTURAL_GUIDELINES_STATUS=absent\n"
    assert not (tmpdir / ag.STAGED_ASSESSMENT).exists()
    assert not (tmpdir / ag.STAGED_ASSESSMENT_ENV).exists()
    assert (tmpdir / ag.MATERIALIZED_DIFF).exists()
    assert (tmpdir / ag.MATERIALIZE_ENV).exists()
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


def test_materialize_diff_freezes_head_for_merge_base_and_diff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        if argv == ["git", "-C", str(repo), "rev-parse", "--verify", "HEAD^{commit}"]:
            return subprocess.CompletedProcess(argv, 0, "resolved-head\n", "")
        if argv == ["git", "merge-base", "resolved-head", "origin/main"]:
            return subprocess.CompletedProcess(argv, 0, "base-sha\n", "")
        if argv == ["git", "diff", "base-sha..resolved-head", "--", ".", ":(exclude)larch-logs/**"]:
            return subprocess.CompletedProcess(argv, 0, "diff body\n", "")
        return subprocess.CompletedProcess(argv, 1, "", "unexpected command")

    monkeypatch.setattr(ag.subprocess, "run", fake_run)

    assert ag.materialize_implementation_diff(repo, base_remote="origin", base_ref="main") == "diff body\n"
    assert calls == [
        ["git", "-C", str(repo), "rev-parse", "--verify", "HEAD^{commit}"],
        ["git", "merge-base", "resolved-head", "origin/main"],
        ["git", "diff", "base-sha..resolved-head", "--", ".", ":(exclude)larch-logs/**"],
    ]
    assert "HEAD" not in calls[1]
    assert "HEAD" not in calls[2]


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


def test_append_deviation_note_writes_warnings_not_tool_failures(tmp_path: Path) -> None:
    tmpdir = tmp_path / "implement"
    tmpdir.mkdir()
    (tmpdir / "execution-issues.md").write_text("### Tool Failures\n- existing tool failure\n", encoding="utf-8")

    status = ag.append_deviation_note(tmpdir, "G-Py-4 deviation: Bash wrapper kept for hook compatibility.\n")

    assert status == "ok"
    text = (tmpdir / "execution-issues.md").read_text(encoding="utf-8")
    assert "### Tool Failures\n- existing tool failure\n" in text
    assert "### Warnings\n" in text
    assert "- G-Py-4 deviation: Bash wrapper kept for hook compatibility." in text
    assert text.index("- G-Py-4 deviation") > text.index("### Warnings")


def test_append_deviation_note_is_idempotent_against_markdown_keys(tmp_path: Path) -> None:
    tmpdir = tmp_path / "implement"
    note = "- G-Cfg-1 deviation: configuration stayed in prose for compatibility.\n"

    assert ag.append_deviation_note(tmpdir, note) == "ok"
    assert ag.append_deviation_note(tmpdir, note) == "duplicate"

    text = (tmpdir / "execution-issues.md").read_text(encoding="utf-8")
    assert text.count("G-Cfg-1 deviation") == 1


def test_append_deviation_note_dedupes_against_ndjson_batch(tmp_path: Path) -> None:
    tmpdir = tmp_path / "implement"
    run_id = "run-abc"
    (tmpdir / "parent-issue.md").parent.mkdir(parents=True)
    (tmpdir / "parent-issue.md").write_text(f"RUN_ID={run_id}\n", encoding="utf-8")
    note = "- G-Py-4 deviation: helper stays prompt-authored for final diff evidence.\n"
    issue_log = tmpdir / "execution-issues.md"
    issue_log.write_text(f"### Warnings\n{note}", encoding="utf-8")
    (tmpdir / ".execution-issues-step7a-reached").write_text("", encoding="utf-8")
    batch_dir = tmpdir / "larch-logs" / "implement" / run_id
    batch_dir.mkdir(parents=True)
    ctx = make_run_context(run_id=run_id, tmpdir=str(tmpdir), manifest_path=str(tmpdir / "manifest.json"))

    run_log_flush._render_execution_issues_batch(
        ctx=ctx,
        batch_dir=batch_dir,
        step_label="pre-push",
        source_label="test",
    )
    batch_rows = [
        json.loads(line)
        for line in (batch_dir / "execution-issues.ndjson").read_text(encoding="utf-8").splitlines()
    ]
    assert batch_rows[0]["category"] == "Warnings"
    issue_log.write_text("", encoding="utf-8")

    assert ag.append_deviation_note(tmpdir, note) == "duplicate"
    assert issue_log.read_text(encoding="utf-8") == ""


def test_append_deviation_note_preserves_new_chunks_when_one_chunk_matches(tmp_path: Path) -> None:
    tmpdir = tmp_path / "implement"
    tmpdir.mkdir()
    issue_log = tmpdir / "execution-issues.md"
    issue_log.write_text(
        "### Warnings\n- G-Py-4 deviation: helper stays prompt-authored for final diff evidence.\n",
        encoding="utf-8",
    )
    note = (
        "- G-Py-4 deviation: helper stays prompt-authored for final diff evidence.\n"
        "- G-Cfg-1 deviation: configuration stayed in prose for compatibility.\n"
    )

    assert ag.append_deviation_note(tmpdir, note) == "ok"
    text = issue_log.read_text(encoding="utf-8")
    assert text.count("G-Py-4 deviation") == 1
    assert text.count("G-Cfg-1 deviation") == 1
    assert "- G-Cfg-1 deviation: configuration stayed in prose for compatibility." in text


def test_append_deviation_note_main_rejects_empty_note(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tmpdir = tmp_path / "implement"
    tmpdir.mkdir()
    note = tmp_path / "note.md"
    note.write_text("  \n\t\n", encoding="utf-8")

    rc = ag.append_deviation_note_main(["--implement-tmpdir", str(tmpdir), "--note-file", str(note)])

    assert rc == 1
    assert "ARCHITECTURAL_GUIDELINES_APPEND_STATUS=failed" in capsys.readouterr().out
    assert not (tmpdir / "execution-issues.md").exists()


def test_append_deviation_note_main_rejects_symlink_note_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tmpdir = tmp_path / "implement"
    tmpdir.mkdir()
    target = tmp_path / "target.md"
    target.write_text("- deviation\n", encoding="utf-8")
    note = tmp_path / "note.md"
    note.symlink_to(target)

    rc = ag.append_deviation_note_main(["--implement-tmpdir", str(tmpdir), "--note-file", str(note)])

    assert rc == 1
    assert "ARCHITECTURAL_GUIDELINES_APPEND_STATUS=failed" in capsys.readouterr().out
    assert not (tmpdir / "execution-issues.md").exists()


def test_append_deviation_note_main_missing_tmpdir_exits_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("IMPLEMENT_TMPDIR", raising=False)
    note = tmp_path / "note.md"
    note.write_text("- deviation\n", encoding="utf-8")

    rc = ag.append_deviation_note_main(["--note-file", str(note)])

    assert rc == 2
    assert "ARCHITECTURAL_GUIDELINES_APPEND_STATUS=failed" in capsys.readouterr().out


def test_log_only_head_advance_keeps_durable_note_consumable_without_repin(
    tmp_path: Path,
) -> None:
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
    assert ag.pin_note_from_staged(tmpdir, head_sha=assessed_head, base_ref="origin/main", repo_root=repo)

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

    assert ag.note_consumable(
        implement_tmpdir=tmpdir,
        head_sha=new_head,
        base_ref="origin/main",
        repo_root=repo,
    )
# pyright: reportPrivateUsage=false


def test_invariants_present_note_empty_has_no_assessment_marker(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _repo(tmp_path)
    (repo / ag.INVARIANTS_FILENAME).write_text("# No entries yet\n", encoding="utf-8")

    assert ag.invariants_present_note_main(["--repo-root", str(repo)]) == 0
    out = capsys.readouterr().out

    assert "ARCHITECTURAL_INVARIANTS_PATH=" in out
    assert ag.INVARIANTS_VIOLATION_ASSESSMENT_REQUIRED not in out


def test_invariant_compose_assessment_persists_durable_note(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "git")
    (repo / ag.INVARIANTS_FILENAME).write_text(
        "### I-Test-1: Keep tests direct\n- Why: invariant coverage.\n",
        encoding="utf-8",
    )
    (repo / "README.md").write_text("base\ninvariant\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "invariant")
    head_sha = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    ).stdout.strip()
    tmpdir = tmp_path / "implement"

    result = ag.prepare_invariant_compose_assessment(implement_tmpdir=tmpdir, repo_root=repo, expected_head_sha=head_sha)
    assert result.status == "assessment-required"
    assert result.diff_path == tmpdir / ag.INVARIANT_MATERIALIZED_DIFF
    assert (tmpdir / ag.INVARIANT_MATERIALIZE_ENV).is_file()

    ag.write_invariant_compose_assessment(
        implement_tmpdir=tmpdir,
        assessment_text=ag.CLEAN_INVARIANT_PRESENTATION_NOTE,
        repo_root=repo,
    )

    assert (tmpdir / ag.INVARIANT_DURABLE_NOTE).read_text(encoding="utf-8") == ag.CLEAN_INVARIANT_PRESENTATION_NOTE + "\n"
    assert ag.invariant_note_consumable(implement_tmpdir=tmpdir, head_sha=head_sha)
    assert ag.invariant_durable_note_metadata(tmpdir)["ASSESSMENT_KIND"] == "clean"


def test_validate_invariant_ship_outcome_record_accepts_violation() -> None:
    reason = ag.validate_invariant_ship_outcome_record(
        {
            "schema_version": "1",
            "phase": "implement",
            "step": "8",
            "outcome": "violation",
            "reason": "violation-note",
            "detail": "I-Test-1 violated",
            "invariants_status": "present",
            "head_sha": "abc123",
            "base_ref": "origin/main",
            "assessment_kind": "violation",
        }
    )

    assert reason is None


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("larch-logs/run/log.txt", True),
        ("docs/guide.md", True),
        ("docs/nested/guide.md", True),
        ("docs/guide.txt", False),
        ("README.md", False),
        ("ARCHITECTURAL_GUIDELINES.md", False),
        ("python/larch/core/config.py", False),
        ("../docs/guide.md", False),
        ("/docs/guide.md", False),
        ("", False),
    ],
)
def test_path_out_of_scope_is_conservative(path: str, expected: bool) -> None:
    assert ag._path_out_of_scope(path) is expected


def test_deterministic_clean_note_records_distinct_identities(tmp_path: Path) -> None:
    tmpdir = tmp_path / "implement"
    diff_text = "diff --git a/docs/a.md b/docs/a.md\n"

    ag.write_deterministic_clean_note(
        implement_tmpdir=tmpdir,
        head_sha="head-a",
        base_ref="origin/main",
        diff_text=diff_text,
    )

    metadata = ag.durable_note_metadata(tmpdir)
    fingerprint = ag.diff_fingerprint(diff_text)
    assert metadata["NOTE_STATE"] == ag.config.NOTE_STATE_DETERMINISTIC_CLEAN
    assert metadata["AUTHORED_DIFF_FINGERPRINT"] == fingerprint
    assert metadata["COVERED_DIFF_FINGERPRINT"] == fingerprint
    assert metadata["DIFF_FINGERPRINT"] == fingerprint
    assert ag.note_consumable(implement_tmpdir=tmpdir, head_sha="head-a")


def test_unavailable_note_is_head_pinned_and_has_no_synthetic_identity(tmp_path: Path) -> None:
    tmpdir = tmp_path / "implement"
    ag.write_unavailable_note(
        implement_tmpdir=tmpdir,
        head_sha="head-a",
        base_ref="origin/main",
        invariant=True,
    )

    metadata = ag.invariant_durable_note_metadata(tmpdir)
    assert metadata["NOTE_STATE"] == ag.config.NOTE_STATE_UNAVAILABLE
    assert metadata["AUTHORED_DIFF_FINGERPRINT"] == ""
    assert metadata["COVERED_DIFF_FINGERPRINT"] == ""
    assert ag.invariant_note_consumable(implement_tmpdir=tmpdir, head_sha="head-a")
    assert not ag.invariant_note_consumable(implement_tmpdir=tmpdir, head_sha="head-b")


@pytest.mark.parametrize(
    ("validator", "record"),
    [
        (
            ag.validate_guideline_ship_outcome_record,
            {
                "schema_version": "1", "phase": "implement", "step": "8",
                "outcome": "clean", "reason": "deterministic-clean", "detail": "",
                "guidelines_status": "present", "head_sha": "abc", "base_ref": "origin/main",
                "assessment_kind": "clean",
            },
        ),
        (
            ag.validate_invariant_ship_outcome_record,
            {
                "schema_version": "1", "phase": "implement", "step": "8",
                "outcome": "dropped", "reason": "unavailable", "detail": "",
                "invariants_status": "present", "head_sha": "abc", "base_ref": "origin/main",
                "assessment_kind": "",
            },
        ),
    ],
)
def test_ship_outcome_validators_accept_new_state_reasons(
    validator: object,
    record: dict[str, str],
) -> None:
    assert callable(validator)
    assert validator(record) is None


def _git_head(repo: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    ).stdout.strip()


def test_incremental_paths_out_of_scope_docs_md_is_safe(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    base_sha = _git_head(repo)
    (repo / "docs").mkdir(parents=True, exist_ok=True)
    (repo / "docs" / "guide.md").write_text("guide\n", encoding="utf-8")
    _git(repo, "add", "docs/guide.md")
    _git(repo, "commit", "-m", "add docs")
    new_sha = _git_head(repo)
    assert ag._incremental_paths_out_of_scope(repo_root=repo, old_head=base_sha, new_head=new_sha)


def test_incremental_paths_out_of_scope_larch_logs_is_safe(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    base_sha = _git_head(repo)
    (repo / "larch-logs" / "run").mkdir(parents=True, exist_ok=True)
    (repo / "larch-logs" / "run" / "log.txt").write_text("log\n", encoding="utf-8")
    _git(repo, "add", "larch-logs/run/log.txt")
    _git(repo, "commit", "-m", "add log")
    new_sha = _git_head(repo)
    assert ag._incremental_paths_out_of_scope(repo_root=repo, old_head=base_sha, new_head=new_sha)


def test_incremental_paths_out_of_scope_code_file_intersects(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    base_sha = _git_head(repo)
    (repo / "python").mkdir(parents=True, exist_ok=True)
    (repo / "python" / "foo.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "python/foo.py")
    _git(repo, "commit", "-m", "add code")
    new_sha = _git_head(repo)
    assert not ag._incremental_paths_out_of_scope(repo_root=repo, old_head=base_sha, new_head=new_sha)


def test_incremental_paths_out_of_scope_mixed_path_intersects(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    base_sha = _git_head(repo)
    (repo / "docs").mkdir(parents=True, exist_ok=True)
    (repo / "docs" / "guide.md").write_text("guide\n", encoding="utf-8")
    (repo / "python").mkdir(parents=True, exist_ok=True)
    (repo / "python" / "foo.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "docs/guide.md", "python/foo.py")
    _git(repo, "commit", "-m", "add mixed")
    new_sha = _git_head(repo)
    assert not ag._incremental_paths_out_of_scope(repo_root=repo, old_head=base_sha, new_head=new_sha)


def test_incremental_paths_out_of_scope_rename_source_intersects(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "python").mkdir(parents=True, exist_ok=True)
    (repo / "python" / "impl.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "python/impl.py")
    _git(repo, "commit", "-m", "add impl")
    h1 = _git_head(repo)
    _git(repo, "rm", "python/impl.py")
    (repo / "docs").mkdir(parents=True, exist_ok=True)
    (repo / "docs" / "guide.md").write_text("guide\n", encoding="utf-8")
    _git(repo, "add", "docs/guide.md")
    _git(repo, "commit", "-m", "rename to docs")
    h2 = _git_head(repo)
    assert not ag._incremental_paths_out_of_scope(repo_root=repo, old_head=h1, new_head=h2)


def test_incremental_paths_out_of_scope_invalid_revision_fails_closed(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    base_sha = _git_head(repo)
    assert not ag._incremental_paths_out_of_scope(repo_root=repo, old_head="notarevision", new_head=base_sha)


def test_incremental_paths_out_of_scope_same_revision_fails_closed(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    sha = _git_head(repo)
    assert not ag._incremental_paths_out_of_scope(repo_root=repo, old_head=sha, new_head=sha)


def test_coverage_advancement_docs_only_note_remains_consumable(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    tmpdir = tmp_path / "implement"
    (repo / "python").mkdir(parents=True, exist_ok=True)
    (repo / "python" / "impl.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "python/impl.py")
    _git(repo, "commit", "-m", "add impl")
    h1 = _git_head(repo)

    diff_text = ag.materialize_implementation_diff(repo, base_remote="origin", base_ref="main")
    ag.write_deterministic_clean_note(
        implement_tmpdir=tmpdir,
        head_sha=h1,
        base_ref="origin/main",
        diff_text=diff_text,
    )
    authored_fp = ag.diff_fingerprint(diff_text)
    assert ag.note_consumable(implement_tmpdir=tmpdir, head_sha=h1, base_ref="origin/main", repo_root=repo)

    (repo / "docs").mkdir(parents=True, exist_ok=True)
    (repo / "docs" / "guide.md").write_text("guide\n", encoding="utf-8")
    _git(repo, "add", "docs/guide.md")
    _git(repo, "commit", "-m", "add docs")
    h2 = _git_head(repo)

    assert ag.note_consumable(implement_tmpdir=tmpdir, head_sha=h2, base_ref="origin/main", repo_root=repo)
    metadata = ag.durable_note_metadata(tmpdir)
    assert metadata["HEAD_SHA"] == h2
    assert metadata["AUTHORED_DIFF_FINGERPRINT"] == authored_fp
    assert metadata["COVERED_DIFF_FINGERPRINT"] != authored_fp
    assert (
        ag.diff_fingerprint(ag.materialize_implementation_diff(repo, base_remote="origin", base_ref="main"))
        == metadata["COVERED_DIFF_FINGERPRINT"]
    )


def test_coverage_advancement_chained_advances_preserve_authored_fingerprint(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    tmpdir = tmp_path / "implement"
    (repo / "python").mkdir(parents=True, exist_ok=True)
    (repo / "python" / "impl.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "python/impl.py")
    _git(repo, "commit", "-m", "add impl")
    h1 = _git_head(repo)

    diff_text = ag.materialize_implementation_diff(repo, base_remote="origin", base_ref="main")
    ag.write_deterministic_clean_note(
        implement_tmpdir=tmpdir,
        head_sha=h1,
        base_ref="origin/main",
        diff_text=diff_text,
    )
    authored_fp = ag.diff_fingerprint(diff_text)

    (repo / "docs").mkdir(parents=True, exist_ok=True)
    (repo / "docs" / "guide.md").write_text("guide\n", encoding="utf-8")
    _git(repo, "add", "docs/guide.md")
    _git(repo, "commit", "-m", "add docs")
    h2 = _git_head(repo)
    assert ag.note_consumable(implement_tmpdir=tmpdir, head_sha=h2, base_ref="origin/main", repo_root=repo)
    covered_after_h2 = ag.durable_note_metadata(tmpdir)["COVERED_DIFF_FINGERPRINT"]

    (repo / "docs" / "extra.md").write_text("extra\n", encoding="utf-8")
    _git(repo, "add", "docs/extra.md")
    _git(repo, "commit", "-m", "add extra docs")
    h3 = _git_head(repo)
    assert ag.note_consumable(implement_tmpdir=tmpdir, head_sha=h3, base_ref="origin/main", repo_root=repo)
    metadata_h3 = ag.durable_note_metadata(tmpdir)
    assert metadata_h3["HEAD_SHA"] == h3
    assert metadata_h3["AUTHORED_DIFF_FINGERPRINT"] == authored_fp
    assert metadata_h3["COVERED_DIFF_FINGERPRINT"] != covered_after_h2


def test_coverage_advancement_code_commit_requires_reassessment(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    tmpdir = tmp_path / "implement"
    (repo / "python").mkdir(parents=True, exist_ok=True)
    (repo / "python" / "impl.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "python/impl.py")
    _git(repo, "commit", "-m", "add impl")
    h1 = _git_head(repo)

    diff_text = ag.materialize_implementation_diff(repo, base_remote="origin", base_ref="main")
    ag.write_deterministic_clean_note(
        implement_tmpdir=tmpdir,
        head_sha=h1,
        base_ref="origin/main",
        diff_text=diff_text,
    )

    (repo / "python" / "bar.py").write_text("y = 2\n", encoding="utf-8")
    _git(repo, "add", "python/bar.py")
    _git(repo, "commit", "-m", "add more code")
    h2 = _git_head(repo)
    assert not ag.note_consumable(implement_tmpdir=tmpdir, head_sha=h2, base_ref="origin/main", repo_root=repo)


def test_consumption_rejects_note_with_no_covered_identity(tmp_path: Path) -> None:
    tmpdir = tmp_path / "implement"
    tmpdir.mkdir(parents=True)
    ag.durable_note_path(tmpdir).write_text("some note\n", encoding="utf-8")
    (tmpdir / ag.DURABLE_NOTE_ENV).write_text(
        "STATUS=present\n"
        "HEAD_SHA=abc\n"
        "NOTE_STATE=authored\n"
        "AUTHORED_DIFF_FINGERPRINT=\n"
        "COVERED_DIFF_FINGERPRINT=\n"
        "DIFF_FINGERPRINT=\n"
        "BASE_REF=origin/main\n"
        "DIFF_SNAPSHOT=\n"
        "GUIDELINES_STATUS=present\n"
        "ASSESSMENT_KIND=\n"
        "WRITTEN_AT=2024-01-01T00:00:00Z\n",
        encoding="utf-8",
    )
    assert not ag.note_consumable(implement_tmpdir=tmpdir, head_sha="abc", base_ref="origin/main")


def test_consumption_accepts_prior_format_metadata(tmp_path: Path) -> None:
    tmpdir = tmp_path / "implement"
    tmpdir.mkdir(parents=True)
    ag.durable_note_path(tmpdir).write_text("some note\n", encoding="utf-8")
    (tmpdir / ag.DURABLE_NOTE_ENV).write_text(
        "STATUS=present\n"
        "HEAD_SHA=abc\n"
        "DIFF_FINGERPRINT=somefingerprint\n"
        "BASE_REF=origin/main\n"
        "GUIDELINES_STATUS=present\n"
        "ASSESSMENT_KIND=clean\n"
        "WRITTEN_AT=2024-01-01T00:00:00Z\n",
        encoding="utf-8",
    )
    assert ag.note_consumable(implement_tmpdir=tmpdir, head_sha="abc")


def test_consumption_rejects_fingerprint_mismatched_snapshot(tmp_path: Path) -> None:
    tmpdir = tmp_path / "implement"
    diff_text = "diff --git a/docs/a.md b/docs/a.md\n"
    ag.write_deterministic_clean_note(
        implement_tmpdir=tmpdir,
        head_sha="head-a",
        base_ref="origin/main",
        diff_text=diff_text,
    )
    snapshot_path = tmpdir / ag.MATERIALIZED_DIFF
    snapshot_path.write_text("tampered diff content\n", encoding="utf-8")
    assert not ag.note_consumable(implement_tmpdir=tmpdir, head_sha="head-a")


def test_consumption_rejects_symlinked_snapshot(tmp_path: Path) -> None:
    tmpdir = tmp_path / "implement"
    diff_text = "diff --git a/docs/a.md b/docs/a.md\n"
    ag.write_deterministic_clean_note(
        implement_tmpdir=tmpdir,
        head_sha="head-a",
        base_ref="origin/main",
        diff_text=diff_text,
    )
    snapshot_path = tmpdir / ag.MATERIALIZED_DIFF
    target = tmp_path / "linked.txt"
    target.write_text(diff_text, encoding="utf-8")
    snapshot_path.unlink()
    snapshot_path.symlink_to(target)
    assert not ag.note_consumable(implement_tmpdir=tmpdir, head_sha="head-a")
