"""Tests for ARCHITECTURAL_GUIDELINES.md helper surfaces."""
# pyright: reportUnusedCallResult=false, reportPrivateUsage=false, reportAttributeAccessIssue=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
# pylint: disable=no-member

from __future__ import annotations

import subprocess
from dataclasses import fields
from pathlib import Path
import pytest

from larch.core import architectural_guidelines as ag
from larch.core.assessment_kind import GUIDELINES, INVARIANTS, AssessmentKind


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


def _seed_durable_note(
    implement_tmpdir: Path,
    *,
    head_sha: str,
    diff_text: str = "diff",
    kind: AssessmentKind = GUIDELINES,
    base_ref: str = "origin/main",
) -> None:
    """Seed Rust-owned durable state for retained Python read tests."""
    fingerprint = ag.diff_fingerprint(diff_text)
    implement_tmpdir.mkdir(parents=True, exist_ok=True)
    diff_path = implement_tmpdir / kind.materialized_diff
    diff_path.write_text(diff_text, encoding="utf-8")
    (implement_tmpdir / kind.durable_note).write_text(
        kind.clean_presentation_note + "\n",
        encoding="utf-8",
    )
    (implement_tmpdir / kind.durable_note_env).write_text(
        "\n".join(
            [
                "STATUS=present",
                "NOTE_STATE=deterministic-clean",
                f"AUTHORED_DIFF_FINGERPRINT={fingerprint}",
                f"COVERED_DIFF_FINGERPRINT={fingerprint}",
                f"HEAD_SHA={head_sha}",
                f"ASSESSED_HEAD_SHA={head_sha}",
                f"BASE_REF={base_ref}",
                f"DIFF_FINGERPRINT={fingerprint}",
                f"DIFF_SNAPSHOT={diff_path}",
                f"{kind.status_env_key}=present",
                "ASSESSMENT_KIND=clean",
                "WRITTEN_AT=2026-08-21T00:00:00Z",
                "",
            ]
        ),
        encoding="utf-8",
    )


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
        "materialize_env", "heading_re", "identifier_re",
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

    assert GUIDELINES.design_requires_nonempty is False
    assert INVARIANTS.design_requires_nonempty is True
    assert GUIDELINES.ship_present_empty is False
    assert INVARIANTS.ship_present_empty is True
    assert GUIDELINES.flush_outcome is True
    assert INVARIANTS.flush_outcome is False


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


@pytest.mark.parametrize("head_sha", ["", " \t"])
def test_validate_guideline_ship_outcome_record_rejects_empty_head_sha(head_sha: str) -> None:
    reason = ag.validate_guideline_ship_outcome_record(
        _valid_guideline_ship_outcome_record(head_sha=head_sha),
    )

    assert reason == "guideline outcome head_sha is empty"


def test_skip_approve_guideline_prompt_contracts_bind_repo_root() -> None:
    root = Path(__file__).resolve().parents[3]
    approval = (root / "skills" / "design" / "references" / "approval-gates-gate-c.md").read_text(encoding="utf-8")
    skill = (root / "skills" / "design" / "SKILL.md").read_text(encoding="utf-8")
    outline = (root / "skills" / "design" / "references" / "design-outline.md").read_text(encoding="utf-8")

    assert '. "$DESIGN_TMPDIR/source-env.sh"' in approval
    assert 'present-note --repo-root "$REPO_ROOT"' in approval
    assert 'persist-design-assessment --repo-root "$REPO_ROOT"' in approval
    assert (
        'architectural-invariants persist-design-assessment --repo-root "$REPO_ROOT"'
        in approval
    )
    assert approval.index(
        'architectural-invariants persist-design-assessment --repo-root "$REPO_ROOT"'
    ) < approval.index(
        'architectural-guidelines persist-design-assessment --repo-root "$REPO_ROOT"'
    )
    assert (
        "**Absent, invalid, or present-but-empty**: when the `read` command does not report `ARCHITECTURAL_INVARIANTS_STATUS=present` or emits no parsed `I-*` entries."
        in approval
    )
    assert (
        "**Clean**: only when invariants are `present` with parsed non-empty content and no violation assessment was required (no `INVARIANTS_VIOLATION_ASSESSMENT_REQUIRED=true` path and no remediated-violations sidecar)."
        in approval
    )
    assert (
        "**Remediated-violations**: when violations were identified and the fix ladder produced a clean plan."
        in approval
    )
    assert (
        "If invariant present-note emits `INVARIANTS_VIOLATION_ASSESSMENT_REQUIRED=true`, consume the subagent's invariants verdict for the complete on-disk `$DESIGN_TMPDIR/plan.txt`, not the chat preview."
        in approval
    )
    assert approval.index(
        "INVARIANTS_VIOLATION_ASSESSMENT_REQUIRED=true"
    ) < approval.index("**Clean**: only when invariants are `present`")
    assert "reason=persist-design-assessment-failed" in approval
    assert approval.index("reason=persist-design-assessment-failed") < approval.index(
        "Do not fire `AskUserQuestion`, approve, auto-approve, or transition to Step 5."
    )
    assert (
        "`architectural-invariants read` is for Step 2b plan drafting; Gate C requires `architectural-invariants present-note` followed by `persist-design-assessment`"
        in approval
    )
    assert "Using `read` here is insufficient" in approval
    assert "**Step 5c missing-invariant-assessment.**" in skill
    assert skill.index("**Step 5c missing-invariant-assessment.**") < skill.index(
        "**Step 5c missing-guideline-assessment.**"
    )
    assert (
        "run `architectural-invariants present-note` + `persist-design-assessment`"
        in skill
    )
    assert (
        "run `architectural-guidelines present-note` + `persist-design-assessment`"
        in skill
    )
    assert "Use Gate C `present-note` (not Step 2b `read`) for both kinds" in skill
    assert skill.index(
        "run `architectural-invariants present-note` + `persist-design-assessment`"
    ) < skill.index(
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
    assert "invoke `scripts/larch.sh design step35-settle --site gate-c`" in approval
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


def test_durable_note_present_requires_regular_present_artifacts(tmp_path: Path) -> None:
    tmpdir = tmp_path / "implement"
    _seed_durable_note(tmpdir, head_sha="head")
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
    _seed_durable_note(tmpdir, head_sha="other")

    assert ag.note_readable_any_head(tmpdir)


def test_note_readable_any_head_rejects_non_present_status(tmp_path: Path) -> None:
    tmpdir = tmp_path / "implement"
    _seed_durable_note(tmpdir, head_sha="head")

    (tmpdir / ag.DURABLE_NOTE_ENV).write_text("STATUS=absent\nHEAD_SHA=other\n", encoding="utf-8")

    assert not ag.note_readable_any_head(tmpdir)


def test_note_readable_any_head_rejects_symlinked_durable_artifacts(tmp_path: Path) -> None:
    note_tmpdir = tmp_path / "note"
    _seed_durable_note(note_tmpdir, head_sha="head")
    note_target = tmp_path / "note-target.md"
    note_target.write_text("note\n", encoding="utf-8")
    (note_tmpdir / ag.DURABLE_NOTE).unlink()
    (note_tmpdir / ag.DURABLE_NOTE).symlink_to(note_target)

    meta_tmpdir = tmp_path / "meta"
    _seed_durable_note(meta_tmpdir, head_sha="head")
    meta_target = tmp_path / "meta-target.env"
    meta_target.write_text("STATUS=present\nHEAD_SHA=head\n", encoding="utf-8")
    (meta_tmpdir / ag.DURABLE_NOTE_ENV).unlink()
    (meta_tmpdir / ag.DURABLE_NOTE_ENV).symlink_to(meta_target)

    assert not ag.note_readable_any_head(note_tmpdir)
    assert not ag.note_readable_any_head(meta_tmpdir)


def test_note_fingerprint_stale_returns_true_when_git_diff_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tmpdir = tmp_path / "implement"
    _seed_durable_note(tmpdir, head_sha="head-b")
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
    _seed_durable_note(tmpdir, head_sha=head_sha, diff_text=diff_text)
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


def test_materialize_diff_accepts_upstream_base(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "README.md").write_text("base\nchange\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "change")
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
    _seed_durable_note(tmpdir, head_sha=assessed_head, diff_text=diff_text)

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
    _seed_durable_note(
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


def test_invariant_coverage_advancement_logs_only_reuses_compose_assessment(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    tmpdir = tmp_path / "implement"
    (repo / ag.INVARIANTS_FILENAME).write_text("### I-Test-1: Keep tests direct\n", encoding="utf-8")
    (repo / "python").mkdir(parents=True, exist_ok=True)
    (repo / "python" / "impl.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", ag.INVARIANTS_FILENAME, "python/impl.py")
    _git(repo, "commit", "-m", "add invariant and impl")
    h1 = _git_head(repo)
    _seed_durable_note(
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
    _seed_durable_note(
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
    _seed_durable_note(
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


def test_coverage_advancement_rejects_snapshot_not_matching_stored_head(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    tmpdir = tmp_path / "implement"
    (repo / "python").mkdir(parents=True, exist_ok=True)
    (repo / "python" / "impl.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "python/impl.py")
    _git(repo, "commit", "-m", "add impl")
    h1 = _git_head(repo)
    diff_text = ag.materialize_implementation_diff(repo, base_remote="origin", base_ref="main")
    _seed_durable_note(implement_tmpdir=tmpdir, head_sha=h1, base_ref="origin/main", diff_text=diff_text)

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
    _seed_durable_note(
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
    _seed_durable_note(
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
    _seed_durable_note(
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
    _seed_durable_note(
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
    _seed_durable_note(
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
    _seed_durable_note(
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


def test_explicit_outcome_allows_identifier_free_violation_and_rejects_clean_mismatch() -> None:
    assert ag._validate_authored_outcome(
        note="The changed recovery path can mutate a closed PR.\n",
        outcome="violation",
        kind=INVARIANTS,
    ) == "violation"

    with pytest.raises(ag.AssessmentReauthorRequired, match=ag.config.ASSESSMENT_REAUTHOR_REASON_CLEAN_MISMATCH):
        ag._validate_authored_outcome(
            note="G-Py-4: the path swallows an error.\n",
            outcome="clean",
            kind=GUIDELINES,
        )


def test_explicit_clean_accepts_canonical_lead_with_identifier_rationale() -> None:
    note = ag.CLEAN_PRESENTATION_NOTE + "\nThis implementation follows G-Py-4."
    assert ag._validate_authored_outcome(
        note=note,
        outcome="clean",
        kind=GUIDELINES,
    ) == "clean"


def test_explicit_clean_accepts_inline_clean_lead_with_invariant_id() -> None:
    # Issue #6955: a clean verdict phrased inline with a supporting I-* reference must
    # not be rejected as a clean/prose mismatch and forced back into re-authoring.
    note = "No invariant violations identified. The change is consistent with I-Gate-1."
    assert ag._validate_authored_outcome(
        note=note,
        outcome="clean",
        kind=INVARIANTS,
    ) == "clean"
