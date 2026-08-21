"""Tests for ARCHITECTURAL_GUIDELINES.md helper surfaces."""
# pyright: reportUnusedCallResult=false, reportPrivateUsage=false, reportAttributeAccessIssue=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
# pylint: disable=no-member

from __future__ import annotations

import json
import subprocess
from dataclasses import fields
from pathlib import Path
from unittest.mock import Mock

import pytest

from larch.core import architectural_guidelines as ag
from larch.core.assessment_kind import GUIDELINES, INVARIANTS, AssessmentKind
from larch.implement import ship_guidelines


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


def test_assessment_kind_descriptors_cover_distinct_lifecycle_contracts() -> None:
    required_fields = {
        "key", "singular", "filename", "env_prefix", "status_field",
        "status_env_key", "path_env_key", "clean_presentation_note",
        "assessment_required_line", "design_assessment", "staged_assessment",
        "staged_assessment_env", "materialized_diff", "durable_note",
        "durable_note_env", "dropped_note_artifact", "ship_outcome_sidecar",
        "materialize_env", "heading_re", "identifier_re", "parse_entries",
        "authored_outcomes", "non_clean_authored_outcome", "ship_outcomes",
        "non_clean_ship_outcome", "absent_reason", "invalid_reason",
        "empty_reason", "non_clean_note_reason", "ship_reason_tokens",
        "ship_present_empty", "design_requires_nonempty", "design_empty_removes",
        "flush_outcome",
    }
    assert {field.name for field in fields(AssessmentKind)} == required_fields
    for kind in (GUIDELINES, INVARIANTS):
        assert kind.filename
        assert kind.env_prefix
        assert kind.status_field
        assert kind.status_env_key
        assert kind.path_env_key
        assert kind.authored_outcomes
        assert kind.ship_outcomes
        assert kind.ship_reason_tokens

    assert GUIDELINES.parse_entries is not INVARIANTS.parse_entries
    assert GUIDELINES.design_requires_nonempty is False
    assert INVARIANTS.design_requires_nonempty is True
    assert GUIDELINES.ship_present_empty is False
    assert INVARIANTS.ship_present_empty is True
    assert GUIDELINES.flush_outcome is True
    assert INVARIANTS.flush_outcome is False


def test_assessment_kind_entry_policies_preserve_the_kind_specific_bodies() -> None:
    raw = """### G-Test-1: Filter details
- Why: retained detail.
- Mechanized: retained ratchet.
- Extra: omitted detail.

### I-Test-1: Preserve details
- Why: retained detail.
- Extra: retained invariant detail.
"""

    assert GUIDELINES.parse_entries(raw) == (
        "### G-Test-1: Filter details\n- Mechanized: retained ratchet."
    )
    assert INVARIANTS.parse_entries(raw) == (
        "### I-Test-1: Preserve details\n"
        "- Why: retained detail.\n"
        "- Extra: retained invariant detail."
    )


def test_ship_outcome_operator_waiver_marker_is_additive_and_constrained() -> None:
    unavailable = _valid_guideline_ship_outcome_record(
        outcome="dropped",
        reason="unavailable",
        assessment_kind="",
        operator_waived=True,
    )
    assert ag.validate_guideline_ship_outcome_record(unavailable) is None
    assert (
        ag.validate_guideline_ship_outcome_record(
            _valid_guideline_ship_outcome_record()
        )
        is None
    )
    assert "boolean" in str(
        ag.validate_guideline_ship_outcome_record(
            unavailable | {"operator_waived": "true"}
        ),
    )
    assert "requires unavailable" in str(
        ag.validate_guideline_ship_outcome_record(
            _valid_guideline_ship_outcome_record(operator_waived=True)
        ),
    )

    invariant = {
        "schema_version": "1",
        "phase": "implement",
        "step": "8",
        "outcome": "dropped",
        "reason": "unavailable",
        "detail": "",
        "invariants_status": "present",
        "head_sha": "abc123",
        "base_ref": "origin/main",
        "assessment_kind": "",
        "operator_waived": True,
    }
    assert ag.validate_invariant_ship_outcome_record(invariant) is None
    assert "boolean" in str(
        ag.validate_invariant_ship_outcome_record(invariant | {"operator_waived": 1}),
    )


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


def test_parse_invariant_entries_ignores_headings_inside_fenced_block() -> None:
    parsed = ag.parse_invariant_entries(
        "### I-Fence-1: Real invariant\n"
        "Body before fence.\n"
        "\n"
        "```\n"
        "### I-Fake-9: Heading inside a code fence\n"
        "```\n"
        "\n"
        "Body after fence.\n"
    )

    assert parsed == (
        "### I-Fence-1: Real invariant\n"
        "Body before fence.\n"
        "\n"
        "```\n"
        "### I-Fake-9: Heading inside a code fence\n"
        "```\n"
        "\n"
        "Body after fence."
    )


def test_parse_invariant_entries_honors_longer_closing_fence() -> None:
    parsed = ag.parse_invariant_entries(
        "### I-Long-1: Real invariant\n"
        "Body.\n"
        "\n"
        "```\n"
        "### I-Fenced-9: Inside fence\n"
        "`````\n"
        "\n"
        "### I-Long-2: Second real invariant\n"
        "Second body.\n"
    )

    assert parsed == (
        "### I-Long-1: Real invariant\n"
        "Body.\n"
        "\n"
        "```\n"
        "### I-Fenced-9: Inside fence\n"
        "`````\n"
        "\n"
        "### I-Long-2: Second real invariant\n"
        "Second body."
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
`crates/larch-cli/src/design_pause_commands.rs` cover `.completed/` inclusion;
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
regression tests in `crates/larch-cli/tests/run_log_flush.rs`.

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
backing: the pinned `agent-lint` release rules A012 and A013 over agent
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
    assert "**Remediated-violations**: when violations were identified and the fix ladder produced a clean plan." in approval
    assert "If invariant present-note emits `INVARIANTS_VIOLATION_ASSESSMENT_REQUIRED=true`, consume the subagent's invariants verdict for the complete on-disk `$DESIGN_TMPDIR/plan.txt`, not the chat preview." in approval
    assert approval.index("INVARIANTS_VIOLATION_ASSESSMENT_REQUIRED=true") < approval.index("**Clean**: only when invariants are `present`")
    assert "reason=persist-design-assessment-failed" in approval
    assert approval.index("reason=persist-design-assessment-failed") < approval.index("Do not fire `AskUserQuestion`, approve, auto-approve, or transition to Step 5.")
    assert "`architectural-invariants read` is for Step 2b plan drafting; Gate C requires `architectural-invariants present-note` followed by `persist-design-assessment`" in approval
    assert "Using `read` here is insufficient" in approval
    assert "**Step 5c missing-invariant-assessment.**" in skill
    assert skill.index("**Step 5c missing-invariant-assessment.**") < skill.index("**Step 5c missing-guideline-assessment.**")
    assert "run `architectural-invariants present-note` + `persist-design-assessment`" in skill
    assert "run `architectural-guidelines present-note` + `persist-design-assessment`" in skill
    assert "Use Gate C `present-note` (not Step 2b `read`) for both kinds" in skill
    assert skill.index("run `architectural-invariants present-note` + `persist-design-assessment`") < skill.index(
        "run `architectural-guidelines present-note` + `persist-design-assessment`"
    )
    assert '. "$DESIGN_TMPDIR/source-env.sh"' in outline
    assert 'present-note --repo-root "$REPO_ROOT"' in outline
    assert "auto-approved (--skip-approve)" in outline


def test_gate_c_fix_ladder_prompt_contracts() -> None:
    root = Path(__file__).resolve().parents[3]
    approval = (root / "skills" / "design" / "references" / "approval-gates-gate-c.md").read_text(encoding="utf-8")

    # Two-tier ladder with per-kind counters and atomic tier-2 consumption.
    assert (
        "Persist per-kind tier-1 and tier-2 counters under `$DESIGN_TMPDIR`: "
        "`architectural-<kind>-gatec-tier1.count` and `architectural-<kind>-gatec-tier2.count`"
    ) in approval
    assert (
        "atomically mark the tier-2 round consumed (increment "
        "`architectural-<kind>-gatec-tier2.count` to 1) before the main agent begins an "
        "invariant repair, a guideline repair, or a guideline decline"
    ) in approval
    # Tier-1 reviser is the MODE=plan-revise claude-implementer.
    assert (
        "spawn exactly one `larch:claude-implementer` subagent with `MODE=plan-revise`"
    ) in approval
    # Gate C settle + fresh-assessor re-entry.
    assert "invoke `python/cli.py design step35-settle --site gate-c`" in approval
    assert "re-enter `resume@4b` only on the clean `gate-c-return` action" in approval
    assert "the reviser never judges its own revision" in approval
    # Invariant cancellation and guideline documented exception.
    assert (
        "Gate C does not approve: skip approval, Step 5, publication, and any waiver, "
        "and end through the existing cancellation outcome with nothing published"
    ) in approval
    assert "append exactly one active `Exception: <rationale> (author: main-agent, date: YYYY-MM-DD)` line" in approval
    assert '--assessment-file "$DESIGN_TMPDIR/architectural-guideline-assessment.input.sidecar" --allow-exception' in approval


def test_generated_implementer_prompts_include_plan_revise_contract() -> None:
    root = Path(__file__).resolve().parents[3]
    base = (root / "agents" / "_implementer-base.md").read_text(encoding="utf-8")
    codex = (root / "skills" / "implement" / "prompts" / "codex-implementer.md").read_text(encoding="utf-8")
    cursor = (root / "skills" / "implement" / "prompts" / "cursor-implementer.md").read_text(encoding="utf-8")
    claude = (root / "agents" / "claude-implementer.md").read_text(encoding="utf-8")

    assert "MODE=plan-revise" in claude
    assert "## Mode boundary" in base
    # Codex and Cursor are regenerated from the shared base, so the plan-revise
    # boundary note stays synchronized in both generated prompts.
    for generated in (codex, cursor):
        assert "## Mode boundary" in generated
        assert "MODE=plan-revise" in generated


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


@pytest.mark.parametrize(
    "note",
    [
        pytest.param("clean\nException: pragmatic for this PR (author: main-agent, date: 2026-07-13)", id="valid"),
        pytest.param(
            "Deviation on G-Py-4.\n"
            "Exception: pragmatic for this PR (author: main-agent, date: 2026-07-13)",
            id="valid-body",
        ),
    ],
)
def test_persist_design_assessment_allow_exception_persists_valid_note(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, note: str
) -> None:
    repo = _repo(tmp_path)
    _write_guidelines(repo)
    design_tmpdir = _design_tmpdir(tmp_path, monkeypatch)
    sidecar = tmp_path / "assessment.input.sidecar"
    sidecar.write_text(note + "\n", encoding="utf-8")

    rc = ag.persist_design_assessment_main(
        ["--repo-root", str(repo), "--design-tmpdir", str(design_tmpdir), "--assessment-file", str(sidecar), "--allow-exception"]
    )

    assert rc == 0
    assert (design_tmpdir / ag.DESIGN_ASSESSMENT).read_text(encoding="utf-8") == note + "\n"


@pytest.mark.parametrize(
    "note",
    [
        pytest.param("Deviation with no exception block.", id="missing"),
        pytest.param("Exception: see the override policy elsewhere", id="malformed"),
        pytest.param("Exception:  (author: main-agent, date: 2026-07-13)", id="empty-rationale"),
        pytest.param("Exception: pragmatic (author: subagent, date: 2026-07-13)", id="wrong-author"),
        pytest.param("Exception: pragmatic (author: main-agent, date: 2026-02-30)", id="impossible-date"),
        pytest.param(
            "Exception: a (author: main-agent, date: 2026-07-13)\n"
            "Exception: b (author: main-agent, date: 2026-07-14)",
            id="duplicate",
        ),
        pytest.param(
            "Deviation.\n```\nException: fenced (author: main-agent, date: 2026-07-13)\n```",
            id="fenced-only",
        ),
    ],
)
def test_persist_design_assessment_allow_exception_rejects_invalid_note(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], note: str
) -> None:
    repo = _repo(tmp_path)
    _write_guidelines(repo)
    design_tmpdir = _design_tmpdir(tmp_path, monkeypatch)
    sidecar = tmp_path / "assessment.input.sidecar"
    sidecar.write_text(note + "\n", encoding="utf-8")

    rc = ag.persist_design_assessment_main(
        ["--repo-root", str(repo), "--design-tmpdir", str(design_tmpdir), "--assessment-file", str(sidecar), "--allow-exception"]
    )

    out = capsys.readouterr().out
    assert rc == 1
    assert "ARCHITECTURAL_GUIDELINE_ASSESSMENT_PERSIST_REASON=invalid-exception" in out
    assert not (design_tmpdir / ag.DESIGN_ASSESSMENT).exists()


def test_persist_design_assessment_rejects_active_exception_without_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _repo(tmp_path)
    _write_guidelines(repo)
    design_tmpdir = _design_tmpdir(tmp_path, monkeypatch)
    sidecar = tmp_path / "assessment.input.sidecar"
    sidecar.write_text(
        "Deviation on G-Py-4.\nException: pragmatic (author: main-agent, date: 2026-07-13)\n",
        encoding="utf-8",
    )

    rc = ag.persist_design_assessment_main(
        ["--repo-root", str(repo), "--design-tmpdir", str(design_tmpdir), "--assessment-file", str(sidecar)]
    )

    out = capsys.readouterr().out
    assert rc == 1
    assert "ARCHITECTURAL_GUIDELINE_ASSESSMENT_PERSIST_REASON=unexpected-exception" in out
    assert not (design_tmpdir / ag.DESIGN_ASSESSMENT).exists()


def test_persist_design_assessment_ordinary_deviation_without_exception_persists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    _write_guidelines(repo)
    design_tmpdir = _design_tmpdir(tmp_path, monkeypatch)
    sidecar = tmp_path / "assessment.input.sidecar"
    sidecar.write_text("Deviation on G-Py-4 with rationale but no exception block.\n", encoding="utf-8")

    rc = ag.persist_design_assessment_main(
        ["--repo-root", str(repo), "--design-tmpdir", str(design_tmpdir), "--assessment-file", str(sidecar)]
    )

    assert rc == 0
    assert (design_tmpdir / ag.DESIGN_ASSESSMENT).is_file()


def test_persist_design_assessment_allow_exception_rejected_for_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _repo(tmp_path)
    _write_guidelines(repo)
    design_tmpdir = _design_tmpdir(tmp_path, monkeypatch)

    rc = ag.persist_design_assessment_main(
        ["--repo-root", str(repo), "--design-tmpdir", str(design_tmpdir), "--assessment", "clean", "--allow-exception"]
    )

    out = capsys.readouterr().out
    assert rc == 1
    assert "ARCHITECTURAL_GUIDELINE_ASSESSMENT_PERSIST_REASON=allow-exception-requires-file" in out
    assert not (design_tmpdir / ag.DESIGN_ASSESSMENT).exists()


def test_persist_design_assessment_allow_exception_rejected_for_absent_and_invalid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    design_tmpdir = _design_tmpdir(tmp_path, monkeypatch)
    sidecar = tmp_path / "assessment.input.sidecar"
    sidecar.write_text("Exception: x (author: main-agent, date: 2026-07-13)\n", encoding="utf-8")

    # Absent guidelines: source flags are rejected before the exception check.
    assert ag.persist_design_assessment_main(
        ["--repo-root", str(repo), "--design-tmpdir", str(design_tmpdir), "--assessment-file", str(sidecar), "--allow-exception"]
    ) == 1
    # No source with the flag is also rejected.
    assert ag.persist_design_assessment_main(
        ["--repo-root", str(repo), "--design-tmpdir", str(design_tmpdir), "--allow-exception"]
    ) == 1


def test_persist_invariant_design_assessment_rejects_allow_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    (repo / ag.INVARIANTS_FILENAME).write_text("### I-Test-1: Invariant\n- Why: needed.\n", encoding="utf-8")
    design_tmpdir = _design_tmpdir(tmp_path, monkeypatch)
    sidecar = tmp_path / "assessment.input.sidecar"
    sidecar.write_text("Consulted ARCHITECTURAL_INVARIANTS.md; no violations identified.\n", encoding="utf-8")

    rc = ag.invariants_persist_design_assessment_main(
        ["--repo-root", str(repo), "--design-tmpdir", str(design_tmpdir), "--assessment-file", str(sidecar), "--allow-exception"]
    )

    assert rc == 1
    assert not (design_tmpdir / ag.INVARIANT_DESIGN_ASSESSMENT).exists()


@pytest.mark.parametrize(
    ("note", "valid", "present"),
    [
        ("Exception: x (author: main-agent, date: 2026-07-13)", True, True),
        ("Exception:  (author: main-agent, date: 2026-07-13)", False, True),
        ("Exception: x (author: main-agent, date: 2026-02-30)", False, True),
        ("Exception: x (author: main-agent, date: 2026-13-01)", False, True),
        ("Exception: x (author: subagent, date: 2026-07-13)", False, True),
        ("> Exception: x (author: main-agent, date: 2026-07-13)", False, False),
        ("Exception: see policy elsewhere", False, True),
        ("no exception at all", False, False),
        (
            "Exception: a (author: main-agent, date: 2026-07-13)\n"
            "Exception: b (author: main-agent, date: 2026-07-14)",
            False,
            True,
        ),
        ("```\nException: x (author: main-agent, date: 2026-07-13)\n```", False, False),
        ("~~~\nException: x (author: main-agent, date: 2026-07-13)\n~~~", False, False),
    ],
)
def test_guideline_active_exception_classification(note: str, valid: bool, present: bool) -> None:
    assert ag.guideline_exception_valid(note) is valid
    assert ag.guideline_exception_present(note) is present
    assert (ag.guideline_active_exception(note) is not None) is valid


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
        """### G-Bash-3: Keep shell scripts portable
- Mechanized: `make agent-lint` covers Bash 3.2 constructs.
- Why: this must not appear.
- Deviate when: this carve-out must not appear.
"""
    )

    assert (
        parsed
        == """### G-Bash-3: Keep shell scripts portable
- Mechanized: `make agent-lint` covers Bash 3.2 constructs."""
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
- Mechanized: `make agent-lint` covers Bash 3.2 constructs.
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
- Mechanized: `make agent-lint` covers Bash 3.2 constructs.

### G-Obs-3: Record execution issues
- Why: tmpdir-only failures vanish.
- Deviate when: no committed log exists."""
    )


def test_pin_note_from_staged_rejects_fingerprint_mismatch(tmp_path: Path) -> None:
    tmpdir = tmp_path / "implement"
    ag.write_staged_assessment(
        outcome="clean",
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
        outcome="clean",
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
        outcome="clean",
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
        outcome="clean",
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
        outcome="clean",
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
        outcome="clean",
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
        outcome="clean",
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
        outcome="clean",
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
        outcome="clean",
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
        outcome="clean",
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
        outcome="clean",
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
        outcome="clean",
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
        outcome="clean",
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
        outcome="clean",
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


def test_pin_note_from_live_diff_returns_false_for_invalid_staged_outcome(tmp_path: Path) -> None:
    tmpdir = tmp_path / "implement"
    ag.write_staged_assessment(
        outcome="clean",
        implement_tmpdir=tmpdir,
        assessment_text="note\n",
        assessed_head_sha="head-a",
        diff_fingerprint_value=ag.diff_fingerprint("stale staged diff"),
        base_ref="origin/main",
        diff_text="stale staged diff",
    )
    sidecar = tmpdir / ag.STAGED_ASSESSMENT_ENV
    sidecar.write_text(
        sidecar.read_text(encoding="utf-8").replace("ASSESSMENT_KIND=clean", "ASSESSMENT_KIND="),
        encoding="utf-8",
    )

    assert not ag._pin_note_from_live_diff(
        implement_tmpdir=tmpdir,
        head_sha="head-b",
        resolved_base="origin/main",
        live_diff=("current live diff", ag.diff_fingerprint("current live diff")),
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


@pytest.mark.parametrize("outcome", ["", "unknown"])
def test_refresh_staged_assessment_for_current_head_returns_false_for_invalid_outcome(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    outcome: str,
) -> None:
    tmpdir = tmp_path / "implement"
    ag.write_staged_assessment(
        outcome="clean",
        implement_tmpdir=tmpdir,
        assessment_text="note\n",
        assessed_head_sha="head-a",
        diff_fingerprint_value=ag.diff_fingerprint("staged diff"),
        base_ref="origin/main",
        diff_text="staged diff",
    )
    sidecar = tmpdir / ag.STAGED_ASSESSMENT_ENV
    sidecar.write_text(
        sidecar.read_text(encoding="utf-8").replace("ASSESSMENT_KIND=clean", f"ASSESSMENT_KIND={outcome}"),
        encoding="utf-8",
    )
    def materialize_live_diff(*, repo_root: Path, resolved_base: str) -> tuple[str, str]:
        del repo_root, resolved_base
        return "live diff", ag.diff_fingerprint("live diff")

    monkeypatch.setattr(ag, "_materialize_live_diff", materialize_live_diff)

    assert not ag.refresh_staged_assessment_for_current_head(
        tmpdir,
        head_sha="head-b",
        base_ref="origin/main",
        repo_root=_repo(tmp_path / "git"),
    )


def test_refresh_staged_assessment_for_current_head_returns_false_when_live_diff_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmpdir = tmp_path / "implement"
    ag.write_staged_assessment(
        outcome="clean",
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
        outcome="clean",
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
        outcome="clean",
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
    ag.write_compose_assessment(implement_tmpdir=tmpdir, assessment_text="Compose assessment", repo_root=repo, outcome="clean")

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
        ag.write_compose_assessment(implement_tmpdir=tmpdir, assessment_text="Compose assessment", repo_root=repo, outcome="clean")


@pytest.mark.parametrize(
    ("kind", "main"),
    [
        (GUIDELINES, ag.write_compose_assessment_main),
        (INVARIANTS, ag.invariants_write_compose_assessment_main),
    ],
)
def test_write_compose_assessment_main_reads_absolute_assessment_file_verbatim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: AssessmentKind,
    main: object,
) -> None:
    implement_tmpdir = tmp_path / "implement"
    assessment_file = tmp_path / "assessment.md"
    assessment_file.write_text("Assessment from direct caller\n", encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_write_compose_assessment(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(ag, "_write_compose_assessment", fake_write_compose_assessment)

    assert callable(main)
    assert main([
        "--implement-tmpdir", str(implement_tmpdir),
        "--assessment-file", str(assessment_file),
    ]) == 0

    assert captured["assessment_text"] == "Assessment from direct caller\n"
    assert captured["kind"] is kind


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
        outcome="clean",
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
        outcome="clean",
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
        outcome="clean",
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
        outcome="clean",
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
    batch = batch_dir / "execution-issues.ndjson"
    _ = batch.write_text(
        json.dumps(
            {"category": "Warnings", "body": note, "phase": "implement", "step": "pre-push"},
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    batch_rows = [
        json.loads(line)
        for line in batch.read_text(encoding="utf-8").splitlines()
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
        outcome="clean",
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


def test_empty_design_persistence_remains_asymmetric_by_kind(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "git")
    (repo / ag.GUIDELINES_FILENAME).write_text("# No entries yet\n", encoding="utf-8")
    (repo / ag.INVARIANTS_FILENAME).write_text("# No entries yet\n", encoding="utf-8")
    design_tmpdir = tmp_path / "design"

    assert ag.persist_design_assessment(
        repo_root=repo,
        design_tmpdir=str(design_tmpdir),
        assessment="clean",
    ) == 0
    guideline_path = design_tmpdir / ag.DESIGN_ASSESSMENT
    assert guideline_path.read_text(encoding="utf-8") == ag.CLEAN_PRESENTATION_NOTE + "\n"

    invariant_path = design_tmpdir / ag.INVARIANT_DESIGN_ASSESSMENT
    invariant_path.write_text("stale\n", encoding="utf-8")
    assert ag.persist_invariant_design_assessment(
        repo_root=repo,
        design_tmpdir=str(design_tmpdir),
    ) == 0
    assert not invariant_path.exists()


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
    assert result.guidelines_status == "present"
    assert result.guidelines_path == str(repo / ag.INVARIANTS_FILENAME)
    assert (tmpdir / ag.INVARIANT_MATERIALIZE_ENV).is_file()

    ag.write_invariant_compose_assessment(
        outcome="clean",
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
    ("note", "expected"),
    [
        ("", ""),
        ("   \n  ", ""),
        (ag.CLEAN_INVARIANT_PRESENTATION_NOTE, "clean"),
        (ag.CLEAN_INVARIANT_PRESENTATION_NOTE + "\n", "clean"),
        # Issue #6882: a clean note may carry rationale beyond the exact line.
        (ag.CLEAN_INVARIANT_PRESENTATION_NOTE + "\nThe adapter realizes the invariant.", "clean"),
        # The reported case: rationale that even references an I-* entry stays clean
        # because the first line is the clean sentence.
        (ag.CLEAN_INVARIANT_PRESENTATION_NOTE + "\nThe adapter realizes I-Stale-1 by caching.", "clean"),
        # A clean first line with trailing whitespace still classifies as clean.
        (ag.CLEAN_INVARIANT_PRESENTATION_NOTE + "  \nextra rationale", "clean"),
        # A note that names a specific invariant, without leading with the clean line,
        # is the violation signal per the documented contract.
        ("I-Test-1: violated by the new cache", "violation"),
        ("- I-Stale-1: stale fingerprint slips through\n- I-Fresh-2: not refreshed", "violation"),
        # A note that neither leads with the clean line nor names an invariant leans
        # clean rather than blocking the ship on ambiguous prose.
        ("No specific invariant applies to this diff.", "clean"),
        # Issue #6955: a clean verdict that references a supporting I-* id in the same
        # sentence still leads clean; the id must not flip it to violation.
        ("No invariant violations identified. The change is consistent with I-Gate-1.", "clean"),
        ("No invariant violations identified.", "clean"),
        ("No violations found; the change respects I-Gate-1 and I-Gate-2.", "clean"),
        # A note that leads with a violation statement naming an invariant stays violation.
        ("I-Gate-1 is violated: the gate disarms on gated data.", "violation"),
    ],
)
def test_invariant_assessment_kind_tolerates_verbose_clean_notes(note: str, expected: str) -> None:
    assert ag.classify_note_for_kind(note, kind=ag.INVARIANTS) == expected


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


@pytest.mark.parametrize(
    "completed",
    [
        subprocess.CompletedProcess(["git"], 1, b"", b"git failure"),
        subprocess.CompletedProcess(["git"], 0, b"docs/guide.md", b""),
        subprocess.CompletedProcess(["git"], 0, b"docs/\xff.md\0", b""),
    ],
)
def test_incremental_paths_out_of_scope_rejects_bad_git_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    completed: subprocess.CompletedProcess[bytes],
) -> None:
    repo = _repo(tmp_path)
    sha = _git_head(repo)

    def fake_valid_commit(*, repo_root: Path, revision: str) -> bool:
        _ = repo_root, revision
        return True

    def fake_run(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[bytes]:
        _ = argv
        return completed

    monkeypatch.setattr(ag, "_valid_commit", fake_valid_commit)
    monkeypatch.setattr(ag.subprocess, "run", fake_run)

    assert not ag._incremental_paths_out_of_scope(repo_root=repo, old_head=sha, new_head="next")


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
    prepared = ag.prepare_compose_assessment(implement_tmpdir=tmpdir, repo_root=repo, expected_head_sha=h2)
    assert prepared.status == "current"
    loaded = ship_guidelines.load_or_prepare_guidelines_note(
        implement_tmpdir=str(tmpdir),
        head_sha=h2,
        base_ref="origin/main",
        repo_root=str(repo),
    )
    assert loaded.needs_assessment is False


def test_invariant_coverage_advancement_logs_only_reuses_compose_assessment(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    tmpdir = tmp_path / "implement"
    (repo / ag.INVARIANTS_FILENAME).write_text("### I-Test-1: Keep tests direct\n", encoding="utf-8")
    (repo / "python").mkdir(parents=True, exist_ok=True)
    (repo / "python" / "impl.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", ag.INVARIANTS_FILENAME, "python/impl.py")
    _git(repo, "commit", "-m", "add invariant and impl")
    h1 = _git_head(repo)
    ag.write_deterministic_clean_note(
        implement_tmpdir=tmpdir,
        head_sha=h1,
        base_ref="origin/main",
        diff_text=ag.materialize_implementation_diff(repo, base_remote="origin", base_ref="main"),
        kind=ag.INVARIANTS,
    )
    (repo / "larch-logs").mkdir()
    (repo / "larch-logs" / "run.log").write_text("log\n", encoding="utf-8")
    _git(repo, "add", "larch-logs/run.log")
    _git(repo, "commit", "-m", "logs only")
    h2 = _git_head(repo)

    prepared = ag.prepare_invariant_compose_assessment(implement_tmpdir=tmpdir, repo_root=repo, expected_head_sha=h2)
    assert prepared.status == "current"
    loaded = ship_guidelines.load_or_prepare_invariants_note(
        implement_tmpdir=str(tmpdir),
        head_sha=h2,
        base_ref="origin/main",
        repo_root=str(repo),
    )
    assert loaded.needs_assessment is False


def _symlinked_tmpdir_pair(tmp_path: Path) -> tuple[Path, Path]:
    """Return (unresolved, resolved) paths to the same implement tmpdir via a /tmp-style symlink."""
    real_parent = tmp_path / "private" / "tmp"
    real_parent.mkdir(parents=True)
    link_parent = tmp_path / "tmp"
    link_parent.symlink_to(real_parent, target_is_directory=True)
    unresolved = link_parent / "implement"
    unresolved.mkdir()
    resolved = unresolved.resolve()
    assert unresolved != resolved
    assert unresolved.resolve() == resolved
    return unresolved, resolved


def _rewrite_durable_diff_snapshot(tmpdir: Path, *, kind: AssessmentKind, snapshot: Path) -> None:
    meta_path = tmpdir / (ag.INVARIANT_DURABLE_NOTE_ENV if kind.is_invariant else ag.DURABLE_NOTE_ENV)
    lines = [
        f"DIFF_SNAPSHOT={snapshot}" if line.startswith("DIFF_SNAPSHOT=") else line
        for line in meta_path.read_text(encoding="utf-8").splitlines()
    ]
    meta_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_note_consumable_accepts_resolved_diff_snapshot_path_forms(tmp_path: Path) -> None:
    """Ship gate may record DIFF_SNAPSHOT unresolved while materialize checks resolved (#7404)."""
    unresolved, resolved = _symlinked_tmpdir_pair(tmp_path)
    repo = _repo(tmp_path)
    (repo / "python").mkdir(parents=True, exist_ok=True)
    (repo / "python" / "impl.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "python/impl.py")
    _git(repo, "commit", "-m", "add impl")
    head = _git_head(repo)
    diff_text = ag.materialize_implementation_diff(repo, base_remote="origin", base_ref="main")
    ag.write_deterministic_clean_note(
        implement_tmpdir=unresolved,
        head_sha=head,
        base_ref="origin/main",
        diff_text=diff_text,
    )
    declared = unresolved / ag.MATERIALIZED_DIFF
    assert Path(ag.durable_note_metadata(unresolved)["DIFF_SNAPSHOT"]) == declared
    assert Path(ag.durable_note_metadata(unresolved)["DIFF_SNAPSHOT"]) != resolved / ag.MATERIALIZED_DIFF

    assert ag.note_consumable(
        implement_tmpdir=resolved, head_sha=head, base_ref="origin/main", repo_root=repo
    )
    assert ag._validated_note_metadata(
        metadata=ag.durable_note_metadata(resolved),
        expected_snapshot=resolved / ag.MATERIALIZED_DIFF,
    ) is not None


def test_coverage_advancement_logs_only_survives_mixed_tmpdir_path_forms(tmp_path: Path) -> None:
    """Larch-log-only HEAD advance must reuse the note when checker and recorder disagree on tmpdir form."""
    unresolved, resolved = _symlinked_tmpdir_pair(tmp_path)
    repo = _repo(tmp_path)
    (repo / "python").mkdir(parents=True, exist_ok=True)
    (repo / "python" / "impl.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "python/impl.py")
    _git(repo, "commit", "-m", "add impl")
    h1 = _git_head(repo)
    ag.write_deterministic_clean_note(
        implement_tmpdir=unresolved,
        head_sha=h1,
        base_ref="origin/main",
        diff_text=ag.materialize_implementation_diff(repo, base_remote="origin", base_ref="main"),
    )
    # Simulate ship-gate recording the unresolved form while a later materialize
    # caller passes the resolved implement_tmpdir.
    _rewrite_durable_diff_snapshot(
        unresolved, kind=GUIDELINES, snapshot=unresolved / ag.MATERIALIZED_DIFF
    )

    (repo / "larch-logs").mkdir()
    (repo / "larch-logs" / "run.log").write_text("log\n", encoding="utf-8")
    _git(repo, "add", "larch-logs/run.log")
    _git(repo, "commit", "-m", "logs only")
    h2 = _git_head(repo)

    assert ag.note_consumable(
        implement_tmpdir=resolved, head_sha=h2, base_ref="origin/main", repo_root=repo
    )
    prepared = ag.prepare_compose_assessment(
        implement_tmpdir=resolved, repo_root=repo, expected_head_sha=h2
    )
    assert prepared.status == "current"
    loaded = ship_guidelines.load_or_prepare_guidelines_note(
        implement_tmpdir=str(resolved),
        head_sha=h2,
        base_ref="origin/main",
        repo_root=str(repo),
    )
    assert loaded.needs_assessment is False


def test_coverage_advancement_rejects_snapshot_not_matching_stored_head(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    tmpdir = tmp_path / "implement"
    (repo / "python").mkdir(parents=True, exist_ok=True)
    (repo / "python" / "impl.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "python/impl.py")
    _git(repo, "commit", "-m", "add impl")
    h1 = _git_head(repo)
    diff_text = ag.materialize_implementation_diff(repo, base_remote="origin", base_ref="main")
    ag.write_deterministic_clean_note(implement_tmpdir=tmpdir, head_sha=h1, base_ref="origin/main", diff_text=diff_text)

    forged_snapshot = "forged snapshot\n"
    (tmpdir / ag.MATERIALIZED_DIFF).write_text(forged_snapshot, encoding="utf-8")
    metadata_path = tmpdir / ag.DURABLE_NOTE_ENV
    forged_fingerprint = ag.diff_fingerprint(forged_snapshot)
    metadata_path.write_text(
        "\n".join(
        f"{key}={forged_fingerprint}" if key in {"COVERED_DIFF_FINGERPRINT", "DIFF_FINGERPRINT"} else line
        for line in metadata_path.read_text(encoding="utf-8").splitlines()
        for key, _, _value in [line.partition("=")]
        )
        + "\n",
        encoding="utf-8",
    )
    (repo / "docs").mkdir(parents=True, exist_ok=True)
    (repo / "docs" / "guide.md").write_text("guide\n", encoding="utf-8")
    _git(repo, "add", "docs/guide.md")
    _git(repo, "commit", "-m", "docs only")

    assert not ag.note_consumable(implement_tmpdir=tmpdir, head_sha=_git_head(repo), base_ref="origin/main", repo_root=repo)


def test_coverage_advancement_metadata_failure_restores_prior_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _repo(tmp_path)
    tmpdir = tmp_path / "implement"
    (repo / "python").mkdir(parents=True, exist_ok=True)
    (repo / "python" / "impl.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "python/impl.py")
    _git(repo, "commit", "-m", "add impl")
    h1 = _git_head(repo)
    ag.write_deterministic_clean_note(
        implement_tmpdir=tmpdir,
        head_sha=h1,
        base_ref="origin/main",
        diff_text=ag.materialize_implementation_diff(repo, base_remote="origin", base_ref="main"),
    )
    before_snapshot = (tmpdir / ag.MATERIALIZED_DIFF).read_text(encoding="utf-8")
    before_metadata = (tmpdir / ag.DURABLE_NOTE_ENV).read_text(encoding="utf-8")
    (repo / "docs").mkdir(parents=True, exist_ok=True)
    (repo / "docs" / "guide.md").write_text("guide\n", encoding="utf-8")
    _git(repo, "add", "docs/guide.md")
    _git(repo, "commit", "-m", "docs only")
    original_replace = Path.replace

    def fail_metadata_replace(path: Path, target: Path) -> Path:
        if target == tmpdir / ag.DURABLE_NOTE_ENV:
            raise OSError("metadata replace failed")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_metadata_replace)

    assert not ag.note_consumable(implement_tmpdir=tmpdir, head_sha=_git_head(repo), base_ref="origin/main", repo_root=repo)
    assert (tmpdir / ag.MATERIALIZED_DIFF).read_text(encoding="utf-8") == before_snapshot
    assert (tmpdir / ag.DURABLE_NOTE_ENV).read_text(encoding="utf-8") == before_metadata


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


def test_consumption_rejects_partial_new_format_metadata(tmp_path: Path) -> None:
    tmpdir = tmp_path / "implement"
    diff_text = "diff --git a/docs/a.md b/docs/a.md\n"
    ag.write_deterministic_clean_note(
        implement_tmpdir=tmpdir,
        head_sha="head-a",
        base_ref="origin/main",
        diff_text=diff_text,
    )
    metadata_path = tmpdir / ag.DURABLE_NOTE_ENV
    metadata_path.write_text(
        metadata_path.read_text(encoding="utf-8").replace("AUTHORED_DIFF_FINGERPRINT=", "AUTHORED_DIFF_FINGERPRINT=\n", 1),
        encoding="utf-8",
    )
    assert not ag.note_consumable(implement_tmpdir=tmpdir, head_sha="head-a", base_ref="origin/main")


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


def test_explicit_outcome_allows_identifier_free_violation_and_rejects_clean_mismatch(tmp_path: Path) -> None:
    violation_dir = tmp_path / "violation"
    ag.write_invariant_staged_assessment(
        implement_tmpdir=violation_dir,
        assessment_text="The changed recovery path can mutate a closed PR.\n",
        assessed_head_sha="head",
        diff_fingerprint_value=ag.diff_fingerprint("diff"),
        base_ref="origin/main",
        outcome="violation",
        diff_text="diff",
    )
    assert ag._read_env(violation_dir / ag.INVARIANT_STAGED_ASSESSMENT_ENV)["ASSESSMENT_KIND"] == "violation"

    mismatch_dir = tmp_path / "mismatch"
    with pytest.raises(ag.AssessmentReauthorRequired, match=ag.config.ASSESSMENT_REAUTHOR_REASON_CLEAN_MISMATCH):
        ag.write_staged_assessment(
            implement_tmpdir=mismatch_dir,
            assessment_text="G-Py-4: the path swallows an error.\n",
            assessed_head_sha="head",
            diff_fingerprint_value=ag.diff_fingerprint("diff"),
            base_ref="origin/main",
            outcome="clean",
            diff_text="diff",
        )
    assert not (mismatch_dir / ag.STAGED_ASSESSMENT).exists()
    assert not (mismatch_dir / ag.STAGED_ASSESSMENT_ENV).exists()


def test_explicit_clean_accepts_canonical_lead_with_identifier_rationale(tmp_path: Path) -> None:
    note = ag.CLEAN_PRESENTATION_NOTE + "\nThis implementation follows G-Py-4."
    ag.write_staged_assessment(
        implement_tmpdir=tmp_path,
        assessment_text=note,
        assessed_head_sha="head",
        diff_fingerprint_value=ag.diff_fingerprint("diff"),
        base_ref="origin/main",
        outcome="clean",
        diff_text="diff",
    )
    assert ag._read_env(tmp_path / ag.STAGED_ASSESSMENT_ENV)["ASSESSMENT_KIND"] == "clean"


def test_explicit_clean_accepts_inline_clean_lead_with_invariant_id(tmp_path: Path) -> None:
    # Issue #6955: a clean verdict phrased inline with a supporting I-* reference must
    # not be rejected as a clean/prose mismatch and forced back into re-authoring.
    note = "No invariant violations identified. The change is consistent with I-Gate-1."
    ag.write_invariant_staged_assessment(
        implement_tmpdir=tmp_path,
        assessment_text=note,
        assessed_head_sha="head",
        diff_fingerprint_value=ag.diff_fingerprint("diff"),
        base_ref="origin/main",
        outcome="clean",
        diff_text="diff",
    )
    assert ag._read_env(tmp_path / ag.INVARIANT_STAGED_ASSESSMENT_ENV)["ASSESSMENT_KIND"] == "clean"
