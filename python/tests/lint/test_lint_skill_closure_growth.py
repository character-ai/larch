from __future__ import annotations

import json
from pathlib import Path

import pytest

from larch.lint import lint_skill_closure_growth as scg
from larch.lint.lint_skill_closure_growth import ScanError


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(text, encoding="utf-8")


def write_roots(root: Path, *, design: str = "", implement: str = "", review: str = "") -> None:
    write(root, "skills/design/SKILL.md", design or "Design root\n")
    write(root, "skills/implement/SKILL.md", implement or "Implement root\n")
    write(root, "skills/review/SKILL.md", review or "Review root\n")


def write_panel_tier(root: Path) -> None:
    write(root, "agents/reviewer-a.md", "reviewer a\n")
    write(root, "skills/shared/reviewer-templates.md", "templates\n")
    write(root, "skills/shared/voting-protocol.md", "voting\n")


def fixture_project(root: Path) -> None:
    write_roots(
        root,
        design=(
            "Design root\n"
            "**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/flags.md` completely.\n"
        ),
        implement=(
            "Implement root\n"
            "**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/self-review.md` completely.\n"
        ),
        review=(
            "Review root\n"
            "**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/review/references/domain-rules.md` completely.\n"
            "If heavy, **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/review/references/heavy-worker.md` completely.\n"
        ),
    )
    write(root, "skills/design/references/flags.md", "flag one\nflag two\n")
    write(root, "skills/implement/references/self-review.md", "review one\n")
    write(root, "skills/review/references/domain-rules.md", "domain\n")
    write(root, "skills/review/references/heavy-worker.md", "heavy\n")
    write_panel_tier(root)


def write_baseline_from_live(root: Path) -> list[scg.SkillClosureResult]:
    results = scg.scan_all(root)
    scg.write_baseline(root / "python/skill-closure-baseline.json", results)
    return results


def test_ratcheted_targets_are_scanned_separately(tmp_path: Path) -> None:
    fixture_project(tmp_path)

    results = {result.skill: result for result in scg.scan_all(tmp_path)}

    assert results["design"].files == (
        "skills/design/SKILL.md",
        "skills/design/references/flags.md",
    )
    assert results["implement"].files == (
        "skills/implement/SKILL.md",
        "skills/implement/references/self-review.md",
    )
    assert results["review"].files == (
        "skills/review/SKILL.md",
        "skills/review/references/domain-rules.md",
    )
    assert results["panel-tier"].files == (
        "agents/reviewer-a.md",
        "skills/shared/reviewer-templates.md",
        "skills/shared/voting-protocol.md",
    )


def test_direct_mandatory_markdown_references_are_counted(tmp_path: Path) -> None:
    write_roots(
        tmp_path,
        design=(
            "root\n"
            "**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/a.md` and `${CLAUDE_PLUGIN_ROOT}/skills/design/references/b.md` completely.\n"
        ),
    )
    write(tmp_path, "skills/design/references/a.md", "a\n")
    write(tmp_path, "skills/design/references/b.md", "b\n")

    result = scg.scan_skill(tmp_path, "design")

    assert result.files == (
        "skills/design/SKILL.md",
        "skills/design/references/a.md",
        "skills/design/references/b.md",
    )


def test_conditional_references_are_reported_by_text_rules(tmp_path: Path) -> None:
    write_roots(
        tmp_path,
        design=(
            "root\n"
            "If `MODE=extra`: **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/conditional.md` completely.\n"
            "- When `MODE=extra`, **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/bullet.md` completely.\n"
            "**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/always.md` completely.\n"
        ),
    )
    write(tmp_path, "skills/design/references/conditional.md", "conditional\n")
    write(tmp_path, "skills/design/references/bullet.md", "bullet\n")
    write(tmp_path, "skills/design/references/always.md", "always\n")

    result = scg.scan_skill(tmp_path, "design")

    assert result.files == ("skills/design/SKILL.md", "skills/design/references/always.md")
    assert result.conditional_files == (
        "skills/design/references/conditional.md",
        "skills/design/references/bullet.md",
    )


def test_background_reference_is_reported_conditional(tmp_path: Path) -> None:
    write_roots(
        tmp_path,
        design="root\nSee `references/flags.md` only for background.\n",
    )
    write(tmp_path, "skills/design/references/flags.md", "flags\n")

    result = scg.scan_skill(tmp_path, "design")

    assert result.files == ("skills/design/SKILL.md",)
    assert result.conditional_files == ("skills/design/references/flags.md",)


def test_background_table_row_without_when_is_forced_conditional(tmp_path: Path) -> None:
    write_roots(
        tmp_path,
        design=(
            "root\n"
            "| `--partition` | `false` | Route directly to split path "
            "(persisted in `run-params.json`; see `references/flags.md` only for background) |\n"
        ),
    )
    write(tmp_path, "skills/design/references/flags.md", "flags\n")

    result = scg.scan_skill(tmp_path, "design")

    assert result.files == ("skills/design/SKILL.md",)
    assert result.conditional_files == ("skills/design/references/flags.md",)


def test_background_reference_collects_multiple_paths(tmp_path: Path) -> None:
    write_roots(
        tmp_path,
        design=(
            "root\n"
            "See `references/flags.md` and `references/brainstorm.md` only for background.\n"
        ),
    )
    write(tmp_path, "skills/design/references/flags.md", "flags\n")
    write(tmp_path, "skills/design/references/brainstorm.md", "brainstorm\n")

    result = scg.scan_skill(tmp_path, "design")

    assert result.files == ("skills/design/SKILL.md",)
    assert result.conditional_files == (
        "skills/design/references/flags.md",
        "skills/design/references/brainstorm.md",
    )


def test_conditional_reference_verbs_and_qualifiers_are_reported(tmp_path: Path) -> None:
    write_roots(
        tmp_path,
        design=(
            "root\n"
            "Load `references/load.md` only when editing mappings; later `references/other.md` is prose.\n"
            "Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/read.md` only after the driver exits.\n"
            "See `./skills/design/references/see.md` only before launch.\n"
            "Follow `references/follow.md` only on cancel routes.\n"
            "load `references/upon.md` and run the retained path only; this token is valid only upon exit.\n"
            "Read `references/for.md` only for shared flag semantics.\n"
        ),
    )
    for name in ("load", "read", "see", "follow", "upon", "for", "other"):
        write(tmp_path, f"skills/design/references/{name}.md", f"{name}\n")

    result = scg.scan_skill(tmp_path, "design")

    assert result.files == ("skills/design/SKILL.md",)
    assert result.conditional_files == (
        "skills/design/references/load.md",
        "skills/design/references/read.md",
        "skills/design/references/see.md",
        "skills/design/references/follow.md",
        "skills/design/references/upon.md",
        "skills/design/references/for.md",
    )
    assert "skills/design/references/other.md" not in result.conditional_files


def test_branch_only_routing_table_rows_are_excluded(tmp_path: Path) -> None:
    write_roots(
        tmp_path,
        implement=(
            "root\n"
            "| `ROUTE=repair` | **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/repair.md` completely. |\n"
            "| general | **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/general.md` completely. |\n"
        ),
    )
    write(tmp_path, "skills/implement/references/repair.md", "repair\n")
    write(tmp_path, "skills/implement/references/general.md", "general\n")

    result = scg.scan_skill(tmp_path, "implement")

    assert result.files == ("skills/implement/SKILL.md", "skills/implement/references/general.md")
    assert result.conditional_files == ("skills/implement/references/repair.md",)


def test_branch_context_bullets_are_excluded(tmp_path: Path) -> None:
    write_roots(
        tmp_path,
        implement=(
            "root\n"
            "- **`stall`**: **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/stall.md` completely.\n"
            "**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/always.md` completely.\n"
        ),
    )
    write(tmp_path, "skills/implement/references/stall.md", "stall\n")
    write(tmp_path, "skills/implement/references/always.md", "always\n")

    result = scg.scan_skill(tmp_path, "implement")

    assert result.files == ("skills/implement/SKILL.md", "skills/implement/references/always.md")
    assert result.conditional_files == ("skills/implement/references/stall.md",)


def test_design_split_path_section_closes_at_step_comment(tmp_path: Path) -> None:
    write_roots(
        tmp_path,
        design=(
            "root\n"
            "### Step 2b.5 — Plan-size threshold check\n"
            "#### Split-path (decomposition panel)\n"
            "**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/decompose-panel.md` completely.\n"
            "##### Nested split heading\n"
            "**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/nested.md` completely.\n"
            "<!-- step:3 — Plan Review -->\n"
            "**MANDATORY — READ ENTIRE FILE before launching reviewers**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/plan-review.md` completely.\n"
        ),
    )
    write(tmp_path, "skills/design/references/decompose-panel.md", "decompose\n")
    write(tmp_path, "skills/design/references/nested.md", "nested\n")
    write(tmp_path, "skills/design/references/plan-review.md", "plan\n")

    result = scg.scan_skill(tmp_path, "design")

    assert result.files == ("skills/design/SKILL.md", "skills/design/references/plan-review.md")
    assert result.conditional_files == (
        "skills/design/references/decompose-panel.md",
        "skills/design/references/nested.md",
    )


def test_design_validator_failure_section_is_conditional_until_next_peer_heading(tmp_path: Path) -> None:
    write_roots(
        tmp_path,
        design=(
            "root\n"
            "### Plan command validator failure (shared)\n"
            "**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/validator-failure.md` completely.\n"
            "### Plan helper contracts\n"
            "**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/always.md` completely.\n"
        ),
    )
    write(tmp_path, "skills/design/references/validator-failure.md", "validator\n")
    write(tmp_path, "skills/design/references/always.md", "always\n")

    result = scg.scan_skill(tmp_path, "design")

    assert result.files == ("skills/design/SKILL.md", "skills/design/references/always.md")
    assert result.conditional_files == ("skills/design/references/validator-failure.md",)


def test_suffix_condition_marks_settle_dispatch_conditional(tmp_path: Path) -> None:
    write_roots(
        tmp_path,
        design=(
            "root\n"
            "1. **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/settle-rc-dispatch.md` completely (if not already loaded at discussion-round2).\n"
        ),
    )
    write(tmp_path, "skills/design/references/settle-rc-dispatch.md", "settle\n")

    result = scg.scan_skill(tmp_path, "design")

    assert result.files == ("skills/design/SKILL.md",)
    assert result.conditional_files == ("skills/design/references/settle-rc-dispatch.md",)


def test_retained_prefix_marks_step2b5_rc_handling_conditional(tmp_path: Path) -> None:
    write_roots(
        tmp_path,
        design=(
            "root\n"
            "3. **Retained callers that ran items 1-2 in this turn**: **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/step2b5-rc-handling.md` completely.\n"
        ),
    )
    write(tmp_path, "skills/design/references/step2b5-rc-handling.md", "rc\n")

    result = scg.scan_skill(tmp_path, "design")

    assert result.files == ("skills/design/SKILL.md",)
    assert result.conditional_files == ("skills/design/references/step2b5-rc-handling.md",)


def test_session_start_registry_tsv_references_are_counted(tmp_path: Path) -> None:
    write_roots(
        tmp_path,
        design=(
            "root\n"
            "**MANDATORY at session start**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/step-name-registry.tsv` to get names.\n"
            "**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/flags.md` completely.\n"
        ),
    )
    write(tmp_path, "skills/design/scripts/step-name-registry.tsv", "1\tone\n")
    write(tmp_path, "skills/design/references/flags.md", "flags\n")

    result = scg.scan_skill(tmp_path, "design")

    assert result.files == (
        "skills/design/SKILL.md",
        "skills/design/scripts/step-name-registry.tsv",
        "skills/design/references/flags.md",
    )


def test_arbitrary_non_markdown_references_are_ignored(tmp_path: Path) -> None:
    write_roots(
        tmp_path,
        design=(
            "root\n"
            "**MANDATORY at session start**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/helper.py` to get names.\n"
            "**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/flags.md` completely.\n"
        ),
    )
    write(tmp_path, "skills/design/scripts/helper.py", "print('helper')\n")
    write(tmp_path, "skills/design/references/flags.md", "flags\n")

    result = scg.scan_skill(tmp_path, "design")

    assert result.files == ("skills/design/SKILL.md", "skills/design/references/flags.md")


def test_referenced_file_references_are_not_recursed_into(tmp_path: Path) -> None:
    write_roots(
        tmp_path,
        design="**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/a.md` completely.\n",
    )
    write(
        tmp_path,
        "skills/design/references/a.md",
        "**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/nested.md` completely.\n",
    )
    write(tmp_path, "skills/design/references/nested.md", "nested\n")

    result = scg.scan_skill(tmp_path, "design")

    assert result.files == ("skills/design/SKILL.md", "skills/design/references/a.md")


def test_only_directive_read_clause_is_harvested(tmp_path: Path) -> None:
    write_roots(
        tmp_path,
        design=(
            "**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/primary.md` completely. Harness `${CLAUDE_PLUGIN_ROOT}/skills/design/references/harness.md`.\n"
        ),
    )
    write(tmp_path, "skills/design/references/primary.md", "primary\n")
    write(tmp_path, "skills/design/references/harness.md", "harness\n")

    result = scg.scan_skill(tmp_path, "design")

    assert result.files == ("skills/design/SKILL.md", "skills/design/references/primary.md")


def test_missing_referenced_markdown_fails_closed(tmp_path: Path) -> None:
    write_roots(
        tmp_path,
        design="**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/missing.md` completely.\n",
    )

    with pytest.raises(ScanError):
        _ = scg.scan_skill(tmp_path, "design")


def test_conditional_runtime_markdown_operands_are_skipped(tmp_path: Path) -> None:
    write_roots(
        tmp_path,
        implement=(
            "root\n"
            "If main agent finds a pre-existing code issue, **MANDATORY — READ ENTIRE FILE** before dual-writing to `$IMPLEMENT_TMPDIR/oos-accepted-main-agent.md`: `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/execution-issues-tracking.md`.\n"
        ),
    )
    write(tmp_path, "skills/implement/references/execution-issues-tracking.md", "tracking\n")

    result = scg.scan_skill(tmp_path, "implement")

    assert result.files == ("skills/implement/SKILL.md",)
    assert result.conditional_files == ("skills/implement/references/execution-issues-tracking.md",)
    assert "$IMPLEMENT_TMPDIR/oos-accepted-main-agent.md" not in result.files
    assert "$IMPLEMENT_TMPDIR/oos-accepted-main-agent.md" not in result.conditional_files


def test_conditional_runtime_only_markdown_operand_does_not_fail(tmp_path: Path) -> None:
    write_roots(
        tmp_path,
        implement=(
            "root\n"
            "If needed, **MANDATORY — READ ENTIRE FILE** before continuing: `$IMPLEMENT_TMPDIR/runtime-only.md`.\n"
        ),
    )

    result = scg.scan_skill(tmp_path, "implement")

    assert result.files == ("skills/implement/SKILL.md",)
    assert not result.conditional_files


def test_eager_runtime_only_markdown_operand_fails_closed(tmp_path: Path) -> None:
    write_roots(
        tmp_path,
        implement=(
            "root\n"
            "**MANDATORY — READ ENTIRE FILE** before continuing: `$IMPLEMENT_TMPDIR/runtime-only.md`.\n"
        ),
    )

    with pytest.raises(ScanError):
        _ = scg.scan_skill(tmp_path, "implement")


def test_oos_pipeline_runtime_operand_branch_collects_only_repo_reference(tmp_path: Path) -> None:
    write_roots(
        tmp_path,
        implement=(
            "root\n"
            "- **`oos-pipeline`**: Read `$IMPLEMENT_TMPDIR/security-oos-observations.md`. **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/ship-pr-oos-checkpoint-router.md` completely.\n"
        ),
    )
    write(tmp_path, "skills/implement/references/ship-pr-oos-checkpoint-router.md", "router\n")

    result = scg.scan_skill(tmp_path, "implement")

    assert result.files == ("skills/implement/SKILL.md",)
    assert result.conditional_files == ("skills/implement/references/ship-pr-oos-checkpoint-router.md",)
    assert "$IMPLEMENT_TMPDIR/security-oos-observations.md" not in result.files
    assert "$IMPLEMENT_TMPDIR/security-oos-observations.md" not in result.conditional_files


def test_oos_pipeline_line_671_does_not_harvest_security_md(tmp_path: Path) -> None:
    """Regression for implement SKILL.md line 671 oos-pipeline bullet."""
    write_roots(
        tmp_path,
        implement=(
            "root\n"
            "- **`oos-pipeline`**: security sidecar disposition only. Read "
            "`$IMPLEMENT_TMPDIR/security-oos-observations.md`, follow `SECURITY.md` "
            "`## Security Findings in OOS Workflows` privately. "
            "**MANDATORY — READ ENTIRE FILE**: Read "
            "`${CLAUDE_PLUGIN_ROOT}/skills/implement/references/ship-pr-oos-checkpoint-router.md` "
            "completely before the `step-8-oos-checkpoint.sh` fence.\n"
        ),
    )
    write(tmp_path, "skills/implement/references/ship-pr-oos-checkpoint-router.md", "router\n")
    write(tmp_path, "SECURITY.md", "# security\n")

    result = scg.scan_skill(tmp_path, "implement")

    assert result.files == ("skills/implement/SKILL.md",)
    assert result.conditional_files == ("skills/implement/references/ship-pr-oos-checkpoint-router.md",)
    assert "SECURITY.md" not in result.conditional_files


def test_invalid_utf8_referenced_markdown_reports_scan_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    fixture_project(tmp_path)
    _ = (tmp_path / "skills/design/references/flags.md").write_bytes(b"\xff\xfe")

    assert scg.main(["--root", str(tmp_path)]) == 2
    err = capsys.readouterr().err
    assert "lint skill-closure-growth: cannot read" in err


def test_invalid_utf8_baseline_reports_scan_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    fixture_project(tmp_path)
    _ = write_baseline_from_live(tmp_path)
    _ = (tmp_path / "python/skill-closure-baseline.json").write_bytes(b"\xff\xfe")

    assert scg.main(["--root", str(tmp_path)]) == 2
    err = capsys.readouterr().err
    assert "lint skill-closure-growth: cannot read baseline" in err


def test_baseline_check_passes_when_live_metrics_match(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    fixture_project(tmp_path)
    _ = write_baseline_from_live(tmp_path)

    assert scg.main(["--root", str(tmp_path)]) == 0, capsys.readouterr().err


def test_baseline_check_fails_when_skill_md_lines_grow(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    fixture_project(tmp_path)
    _ = write_baseline_from_live(tmp_path)
    with (tmp_path / "skills/design/SKILL.md").open("a", encoding="utf-8") as handle:
        _ = handle.write("extra line\n")

    assert scg.main(["--root", str(tmp_path)]) == 1
    assert "design: skill_md_lines" in capsys.readouterr().err


def test_baseline_check_fails_when_closure_lines_grow(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    fixture_project(tmp_path)
    _ = write_baseline_from_live(tmp_path)
    with (tmp_path / "skills/design/references/flags.md").open("a", encoding="utf-8") as handle:
        _ = handle.write("extra line\n")

    assert scg.main(["--root", str(tmp_path)]) == 1
    assert "design: closure_lines" in capsys.readouterr().err


def test_baseline_check_fails_when_estimated_tokens_grow(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    fixture_project(tmp_path)
    _ = write_baseline_from_live(tmp_path)
    with (tmp_path / "skills/design/references/flags.md").open("a", encoding="utf-8") as handle:
        _ = handle.write(" more characters")

    assert scg.main(["--root", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert "design: closure_estimated_tokens" in err or "design: skill_md_estimated_tokens" in err


def test_blank_line_only_deletion_leaves_content_tokens_unchanged(tmp_path: Path) -> None:
    write_roots(tmp_path, design="alpha\n\nbeta\n")
    baseline = scg.scan_skill(tmp_path, "design")

    write(tmp_path, "skills/design/SKILL.md", "alpha\nbeta\n")
    live = scg.scan_skill(tmp_path, "design")

    assert live.skill_md_lines < baseline.skill_md_lines
    assert live.skill_md_content_estimated_tokens == baseline.skill_md_content_estimated_tokens
    assert live.closure_content_estimated_tokens == baseline.closure_content_estimated_tokens


def test_content_growth_fails_even_when_line_count_drops(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fixture_project(tmp_path)
    write(tmp_path, "skills/design/SKILL.md", "a\n" + ("\n" * 100))
    _ = write_baseline_from_live(tmp_path)
    write(tmp_path, "skills/design/SKILL.md", "a" + ("b" * 80) + "\n")

    assert scg.main(["--root", str(tmp_path)]) == 1

    err = capsys.readouterr().err
    assert "design: skill_md_content_estimated_tokens" in err


def test_skill_filter_ignores_other_skill_growth(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    fixture_project(tmp_path)
    _ = write_baseline_from_live(tmp_path)
    with (tmp_path / "skills/implement/SKILL.md").open("a", encoding="utf-8") as handle:
        _ = handle.write("extra implement growth\n")

    assert scg.main(["--root", str(tmp_path), "--skill", "design"]) == 0, capsys.readouterr().err
    assert scg.main(["--root", str(tmp_path)]) == 1
    assert "implement:" in capsys.readouterr().err


def test_baseline_tracked_file_may_move_from_eager_to_conditional(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fixture_project(tmp_path)
    _ = write_baseline_from_live(tmp_path)
    write(
        tmp_path,
        "skills/design/SKILL.md",
        "root\nSee `${CLAUDE_PLUGIN_ROOT}/skills/design/references/flags.md` only for background.\n",
    )

    assert scg.main(["--root", str(tmp_path), "--skill", "design"]) == 0, capsys.readouterr().err


def test_review_baseline_tracked_file_may_move_from_eager_to_conditional(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fixture_project(tmp_path)
    write(
        tmp_path,
        "skills/review/SKILL.md",
        (
            "Review root with enough padding for a later conditional demotion\n"
            "**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/review/references/domain-rules.md` completely.\n"
            "If heavy, **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/review/references/heavy-worker.md` completely.\n"
        ),
    )
    _ = write_baseline_from_live(tmp_path)
    write(
        tmp_path,
        "skills/review/SKILL.md",
        (
            "Review root\n"
            "If needed, **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/review/references/domain-rules.md` completely.\n"
            "If heavy, **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/review/references/heavy-worker.md` completely.\n"
        ),
    )

    assert scg.main(["--root", str(tmp_path), "--skill", "review"]) == 0, capsys.readouterr().err


def test_baseline_tracked_file_removed_from_both_tiers_fails(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fixture_project(tmp_path)
    _ = write_baseline_from_live(tmp_path)
    write(tmp_path, "skills/design/SKILL.md", "root\n")

    assert scg.main(["--root", str(tmp_path), "--skill", "design"]) == 1

    err = capsys.readouterr().err
    assert "design: baseline-tracked file dropped skills/design/references/flags.md" in err


def test_skill_filter_scopes_baseline_tracked_file_drops(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fixture_project(tmp_path)
    _ = write_baseline_from_live(tmp_path)
    write(tmp_path, "skills/implement/SKILL.md", "root\n")

    assert scg.main(["--root", str(tmp_path), "--skill", "design"]) == 0, capsys.readouterr().err
    assert scg.main(["--root", str(tmp_path), "--skill", "implement"]) == 1
    assert "implement: baseline-tracked file dropped" in capsys.readouterr().err


def test_unknown_skill_filter_exits_tool_failure(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    fixture_project(tmp_path)
    _ = write_baseline_from_live(tmp_path)

    assert scg.main(["--root", str(tmp_path), "--skill", "unknown"]) == 2
    assert "invalid choice" in capsys.readouterr().err


def test_write_rejects_skill_filter_without_rewriting(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fixture_project(tmp_path)
    _ = write_baseline_from_live(tmp_path)
    baseline_path = tmp_path / "python/skill-closure-baseline.json"
    original = baseline_path.read_text(encoding="utf-8")
    with (tmp_path / "skills/design/SKILL.md").open("a", encoding="utf-8") as handle:
        _ = handle.write("changed after baseline\n")

    assert scg.main(["--root", str(tmp_path), "--write", "--skill", "design"]) == 2

    assert baseline_path.read_text(encoding="utf-8") == original
    assert "--skill is check-only" in capsys.readouterr().err


def test_write_regenerates_canonical_json(tmp_path: Path) -> None:
    fixture_project(tmp_path)

    assert scg.main(["--root", str(tmp_path), "--write"]) == 0

    baseline_path = tmp_path / "python/skill-closure-baseline.json"
    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert [row["skill"] for row in payload] == ["design", "implement", "panel-tier", "review"]
    assert all(set(row.keys()) == set(scg.BASELINE_KEYS) for row in payload)
    assert all("conditional_files" in row for row in payload)
    panel_row = next(row for row in payload if row["skill"] == "panel-tier")
    assert panel_row["skill_md_lines"] == 0
    assert panel_row["conditional_lines"] == 0
    assert panel_row["conditional_files"] == []
    assert baseline_path.read_text(encoding="utf-8").endswith("\n")


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("skill_md_content_estimated_tokens", None),
        ("closure_content_estimated_tokens", True),
    ],
)
def test_baseline_rejects_missing_or_malformed_content_metrics(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    field: str,
    replacement: object,
) -> None:
    fixture_project(tmp_path)
    _ = write_baseline_from_live(tmp_path)
    baseline_path = tmp_path / "python/skill-closure-baseline.json"
    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    if replacement is None:
        del payload[0][field]
    else:
        payload[0][field] = replacement
    _ = baseline_path.write_text(json.dumps(payload), encoding="utf-8")

    assert scg.main(["--root", str(tmp_path)]) == 2
    assert field in capsys.readouterr().err


def test_report_mode_prints_all_ratcheted_targets(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_roots(
        tmp_path,
        design=(
            "Design root\n"
            "**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/flags.md` completely.\n"
            "If extra, **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/conditional.md` completely.\n"
        ),
        implement=(
            "Implement root\n"
            "**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/self-review.md` completely.\n"
        ),
        review=(
            "Review root\n"
            "**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/review/references/domain-rules.md` completely.\n"
        ),
    )
    write(tmp_path, "skills/design/references/flags.md", "flag one\nflag two\n")
    write(tmp_path, "skills/design/references/conditional.md", "conditional\n")
    write(tmp_path, "skills/implement/references/self-review.md", "review one\n")
    write(tmp_path, "skills/review/references/domain-rules.md", "domain\n")
    write_panel_tier(tmp_path)

    assert scg.report_main(["--root", str(tmp_path)]) == 0

    out = capsys.readouterr().out
    assert "Eager closure (ratcheted)" in out
    assert "Conditional closure (review ratcheted; design and implement reported only)" in out
    assert "skill_content_tokens" in out
    assert "closure_content_tokens" in out
    assert "conditional_content_tokens" in out
    assert "design" in out
    assert "implement" in out
    assert "review" in out
    assert "panel-tier" in out
    assert "skills/design/SKILL.md" in out
    assert "skills/implement/SKILL.md" in out
    assert "skills/review/SKILL.md" in out
    assert "agents/reviewer-a.md" in out
    assert out.index("skills/design/references/flags.md") < out.index("Conditional closure")
    assert out.index("Conditional closure") < out.index("skills/design/references/conditional.md")


def test_rebase_or_bootstrap_mandatory_reads_stay_excluded(tmp_path: Path) -> None:
    write_roots(
        tmp_path,
        implement=(
            "root\n"
            "**Conditional routing reference**: for absorbed checkpoint `1.r`, branch only on `BOOTSTRAP_NEXT=rebase-routing`. Missing KVs fail closed: **MANDATORY — READ ENTIRE FILE** `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/rebase-checkpoint-routing.md`.\n"
            "| `BOOTSTRAP_NEXT=degraded-prompt` | **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/bootstrap-recovery.md` completely. |\n"
            "**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/self-review.md` completely.\n"
        ),
    )
    write(tmp_path, "skills/implement/references/rebase-checkpoint-routing.md", "rebase\n")
    write(tmp_path, "skills/implement/references/bootstrap-recovery.md", "bootstrap\n")
    write(tmp_path, "skills/implement/references/self-review.md", "review\n")

    result = scg.scan_skill(tmp_path, "implement")

    assert result.files == ("skills/implement/SKILL.md", "skills/implement/references/self-review.md")
    assert result.conditional_files == (
        "skills/implement/references/rebase-checkpoint-routing.md",
        "skills/implement/references/bootstrap-recovery.md",
    )


def test_implement_macro_sections_are_conditional_until_next_peer_heading(tmp_path: Path) -> None:
    write_roots(
        tmp_path,
        implement=(
            "root\n"
            "## Checks Failure Entry Macro\n"
            "2. **MANDATORY — READ ENTIRE FILE**: `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/checks-repair-loop.md`.\n"
            "## Step 5\n"
            "**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/self-review.md` completely.\n"
        ),
    )
    write(tmp_path, "skills/implement/references/checks-repair-loop.md", "checks\n")
    write(tmp_path, "skills/implement/references/self-review.md", "review\n")

    result = scg.scan_skill(tmp_path, "implement")

    assert result.files == ("skills/implement/SKILL.md", "skills/implement/references/self-review.md")
    assert result.conditional_files == ("skills/implement/references/checks-repair-loop.md",)


def test_implement_macro_conditional_state_survives_nested_heading_only(tmp_path: Path) -> None:
    write_roots(
        tmp_path,
        implement=(
            "root\n"
            "## Durable Bail to Step 18 Macro\n"
            "**MANDATORY — READ ENTIRE FILE**: `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/step5-review-branches.md`; follow durable bail.\n"
            "### Nested macro detail\n"
            "**MANDATORY — READ ENTIRE FILE**: `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/nested.md`.\n"
            "## Step 18\n"
            "**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/self-review.md` completely.\n"
        ),
    )
    write(tmp_path, "skills/implement/references/step5-review-branches.md", "branches\n")
    write(tmp_path, "skills/implement/references/nested.md", "nested\n")
    write(tmp_path, "skills/implement/references/self-review.md", "review\n")

    result = scg.scan_skill(tmp_path, "implement")

    assert result.files == ("skills/implement/SKILL.md", "skills/implement/references/self-review.md")
    assert result.conditional_files == (
        "skills/implement/references/step5-review-branches.md",
        "skills/implement/references/nested.md",
    )


def test_review_step0_narrow_eager_patterns_are_counted(tmp_path: Path) -> None:
    write_roots(
        tmp_path,
        review=(
            "root\n"
            "Use `${CLAUDE_PLUGIN_ROOT}/skills/shared/session-setup-output.md` for setup KVs.\n"
            "Run the procedure in `${CLAUDE_PLUGIN_ROOT}/skills/shared/external-reviewers.md`: invoke gate.\n"
            "**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/review/references/domain-rules.md` completely.\n"
        ),
    )
    write(tmp_path, "skills/shared/session-setup-output.md", "setup\n")
    write(tmp_path, "skills/shared/external-reviewers.md", "external\n")
    write(tmp_path, "skills/review/references/domain-rules.md", "domain\n")

    result = scg.scan_skill(tmp_path, "review")

    assert result.files == (
        "skills/review/SKILL.md",
        "skills/shared/session-setup-output.md",
        "skills/shared/external-reviewers.md",
        "skills/review/references/domain-rules.md",
    )


def test_design_step0_shared_narrow_patterns_are_counted(tmp_path: Path) -> None:
    write_roots(
        tmp_path,
        design=(
            "root\n"
            "Use `${CLAUDE_PLUGIN_ROOT}/skills/shared/session-setup-output.md` for setup KVs.\n"
            "Run the procedure in `${CLAUDE_PLUGIN_ROOT}/skills/shared/external-reviewers.md` immediately.\n"
            "**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/flags.md` completely.\n"
        ),
    )
    write(tmp_path, "skills/shared/session-setup-output.md", "setup\n")
    write(tmp_path, "skills/shared/external-reviewers.md", "external\n")
    write(tmp_path, "skills/design/references/flags.md", "flags\n")

    result = scg.scan_skill(tmp_path, "design")

    assert result.files == (
        "skills/design/SKILL.md",
        "skills/shared/session-setup-output.md",
        "skills/shared/external-reviewers.md",
        "skills/design/references/flags.md",
    )


def test_narrow_pattern_after_read_completely_keeps_both_references(tmp_path: Path) -> None:
    write_roots(
        tmp_path,
        review=(
            "root\n"
            "Read `${CLAUDE_PLUGIN_ROOT}/skills/review/references/domain-rules.md` completely before setup. "
            "Use `${CLAUDE_PLUGIN_ROOT}/skills/shared/session-setup-output.md` for setup KVs.\n"
        ),
    )
    write(tmp_path, "skills/review/references/domain-rules.md", "domain\n")
    write(tmp_path, "skills/shared/session-setup-output.md", "setup\n")

    result = scg.scan_skill(tmp_path, "review")

    assert result.files == (
        "skills/review/SKILL.md",
        "skills/review/references/domain-rules.md",
        "skills/shared/session-setup-output.md",
    )


def test_mid_line_condition_before_narrow_pattern_marks_conditional(tmp_path: Path) -> None:
    write_roots(
        tmp_path,
        review=(
            "root\n"
            "Step 0 branch uses setup only when degraded: "
            "Use `${CLAUDE_PLUGIN_ROOT}/skills/shared/session-setup-output.md` for setup KVs.\n"
        ),
    )
    write(tmp_path, "skills/shared/session-setup-output.md", "setup\n")

    result = scg.scan_skill(tmp_path, "review")

    assert result.files == ("skills/review/SKILL.md",)
    assert result.conditional_files == ("skills/shared/session-setup-output.md",)


def test_sentence_clause_keeps_first_character_without_prior_boundary() -> None:
    line = "Follow `${CLAUDE_PLUGIN_ROOT}/skills/shared/final-summary-emit.md` marker-first profile."

    matches = scg._narrow_directive_matches(  # pyright: ignore[reportPrivateUsage]
        line,
        "implement",
    )

    assert matches[0].clause.startswith("Follow ")


def test_implement_final_summary_narrow_follow_pattern_is_counted(tmp_path: Path) -> None:
    write_roots(
        tmp_path,
        implement=(
            "root\n"
            "Follow `${CLAUDE_PLUGIN_ROOT}/skills/shared/final-summary-emit.md` marker-first profile. Later `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/extra.md`.\n"
        ),
    )
    write(tmp_path, "skills/shared/final-summary-emit.md", "summary\n")
    write(tmp_path, "skills/implement/references/extra.md", "extra\n")

    result = scg.scan_skill(tmp_path, "implement")

    assert result.files == ("skills/implement/SKILL.md", "skills/shared/final-summary-emit.md")


def test_unrelated_follow_citation_is_not_counted(tmp_path: Path) -> None:
    write_roots(
        tmp_path,
        implement=(
            "root\n"
            "Follow `${CLAUDE_PLUGIN_ROOT}/skills/shared/subskill-invocation.md` for anti-halt handling.\n"
        ),
    )
    write(tmp_path, "skills/shared/subskill-invocation.md", "subskill\n")

    result = scg.scan_skill(tmp_path, "implement")

    assert result.files == ("skills/implement/SKILL.md",)


def test_force_requested_false_preflight_audit_is_eager(tmp_path: Path) -> None:
    write_roots(
        tmp_path,
        implement=(
            "root\n"
            "**When `force_requested=false` (only)** — **MANDATORY — READ ENTIRE FILE** at Preflight item 4: `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/preflight-plan-audit.md`.\n"
        ),
    )
    write(tmp_path, "skills/implement/references/preflight-plan-audit.md", "audit\n")

    result = scg.scan_skill(tmp_path, "implement")

    assert result.files == ("skills/implement/SKILL.md", "skills/implement/references/preflight-plan-audit.md")
    assert not result.conditional_files


def test_force_requested_true_branch_stays_conditional(tmp_path: Path) -> None:
    write_roots(
        tmp_path,
        implement=(
            "root\n"
            "**When `force_requested=true` (only)** — **MANDATORY — READ ENTIRE FILE**: `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/force-mode.md`.\n"
        ),
    )
    write(tmp_path, "skills/implement/references/force-mode.md", "force\n")

    result = scg.scan_skill(tmp_path, "implement")

    assert result.files == ("skills/implement/SKILL.md",)
    assert result.conditional_files == ("skills/implement/references/force-mode.md",)


def test_panel_tier_scan_includes_agents_and_shared_files(tmp_path: Path) -> None:
    write_panel_tier(tmp_path)
    write(tmp_path, "agents/reviewer-b.md", "reviewer b\n")

    result = scg.scan_panel_tier(tmp_path)

    assert result.files == (
        "agents/reviewer-a.md",
        "agents/reviewer-b.md",
        "skills/shared/reviewer-templates.md",
        "skills/shared/voting-protocol.md",
    )
    assert result.skill_md_lines == 0
    assert result.conditional_lines == 0
    assert not result.conditional_files
    assert result.closure_lines == 4


def test_panel_tier_scan_fails_when_fixed_file_is_missing(tmp_path: Path) -> None:
    write(tmp_path, "agents/reviewer-a.md", "reviewer a\n")
    write(tmp_path, "skills/shared/reviewer-templates.md", "templates\n")

    with pytest.raises(ScanError):
        _ = scg.scan_panel_tier(tmp_path)


def test_panel_tier_scan_fails_when_agent_glob_is_empty(tmp_path: Path) -> None:
    write(tmp_path, "skills/shared/reviewer-templates.md", "templates\n")
    write(tmp_path, "skills/shared/voting-protocol.md", "voting\n")

    with pytest.raises(ScanError):
        _ = scg.scan_panel_tier(tmp_path)


def test_review_filter_checks_only_review_growth(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    fixture_project(tmp_path)
    _ = write_baseline_from_live(tmp_path)
    with (tmp_path / "skills/design/SKILL.md").open("a", encoding="utf-8") as handle:
        _ = handle.write("extra design growth\n")

    assert scg.main(["--root", str(tmp_path), "--skill", "review"]) == 0, capsys.readouterr().err


def test_panel_tier_filter_checks_only_panel_growth(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    fixture_project(tmp_path)
    _ = write_baseline_from_live(tmp_path)
    with (tmp_path / "skills/design/SKILL.md").open("a", encoding="utf-8") as handle:
        _ = handle.write("extra design growth\n")

    assert scg.main(["--root", str(tmp_path), "--skill", "panel-tier"]) == 0, capsys.readouterr().err


def test_baseline_requires_all_ratcheted_targets(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    fixture_project(tmp_path)
    _ = write_baseline_from_live(tmp_path)
    baseline_path = tmp_path / "python/skill-closure-baseline.json"
    payload = [
        row for row in json.loads(baseline_path.read_text(encoding="utf-8")) if row["skill"] != "panel-tier"
    ]
    _ = baseline_path.write_text(json.dumps(payload), encoding="utf-8")

    assert scg.main(["--root", str(tmp_path)]) == 2
    assert "one row per ratcheted target" in capsys.readouterr().err


def test_review_closure_growth_is_ratcheted(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    fixture_project(tmp_path)
    _ = write_baseline_from_live(tmp_path)
    with (tmp_path / "skills/review/references/domain-rules.md").open("a", encoding="utf-8") as handle:
        _ = handle.write("extra review growth\n")

    assert scg.main(["--root", str(tmp_path)]) == 1
    assert "review: closure_lines" in capsys.readouterr().err


def test_panel_tier_closure_growth_is_ratcheted(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    fixture_project(tmp_path)
    _ = write_baseline_from_live(tmp_path)
    with (tmp_path / "agents/reviewer-a.md").open("a", encoding="utf-8") as handle:
        _ = handle.write("extra panel growth\n")

    assert scg.main(["--root", str(tmp_path)]) == 1
    assert "panel-tier: closure_lines" in capsys.readouterr().err


def test_review_conditional_growth_is_ratcheted(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    fixture_project(tmp_path)
    _ = write_baseline_from_live(tmp_path)
    with (tmp_path / "skills/review/references/heavy-worker.md").open("a", encoding="utf-8") as handle:
        _ = handle.write("extra conditional growth\n")

    assert scg.main(["--root", str(tmp_path)]) == 1
    assert "review: conditional_lines" in capsys.readouterr().err


def test_design_conditional_growth_is_report_only(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    fixture_project(tmp_path)
    write(tmp_path, "skills/design/SKILL.md", "If extra, **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/conditional.md` completely.\n")
    write(tmp_path, "skills/design/references/conditional.md", "conditional\n")
    _ = write_baseline_from_live(tmp_path)
    with (tmp_path / "skills/design/references/conditional.md").open("a", encoding="utf-8") as handle:
        _ = handle.write("extra conditional growth\n")

    assert scg.main(["--root", str(tmp_path)]) == 0, capsys.readouterr().err


def test_real_design_scan_keeps_plan_review_eager_and_branch_refs_conditional() -> None:
    repo_root = Path(__file__).resolve().parents[3]

    result = scg.scan_skill(repo_root, "design")

    assert "skills/design/scripts/step-name-registry.tsv" in result.files
    assert "skills/shared/session-setup-output.md" in result.files
    assert "skills/shared/external-reviewers.md" in result.files
    assert "skills/design/references/plan-review.md" in result.files
    assert "skills/design/references/plan-review.md" not in result.conditional_files
    assert "skills/shared/session-setup-output.md" not in result.conditional_files
    assert "skills/shared/external-reviewers.md" not in result.conditional_files
    for rel in (
        "skills/design/references/decompose-panel.md",
        "skills/design/references/validator-failure.md",
        "skills/design/references/settle-rc-dispatch.md",
        "skills/design/references/step2b5-rc-handling.md",
        "skills/design/references/flags.md",
        "skills/design/references/sentinel-host-table.md",
        "skills/design/references/step2b-drafter-failsafe.md",
        "skills/design/references/dialectic-clarifier.md",
        "skills/shared/final-summary-emit.md",
    ):
        assert rel not in result.files
        assert rel in result.conditional_files


def test_real_implement_scan_tracks_macro_and_audit_refs_conditionally() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    result = scg.scan_skill(repo_root, "implement")

    assert "skills/implement/scripts/step-name-registry.tsv" in result.files
    assert "skills/shared/final-summary-emit.md" in result.files
    assert "skills/implement/references/preflight-plan-audit.md" in result.files
    assert "skills/implement/references/force-mode.md" not in result.files
    for rel in (
        "skills/implement/references/checks-repair-loop.md",
        "skills/implement/references/extracted-script-registry.md",
        "skills/implement/references/phantom-probe.md",
        "skills/shared/orchestrator-never.md",
    ):
        assert rel not in result.files
        assert rel in result.conditional_files
    assert "$IMPLEMENT_TMPDIR/oos-accepted-main-agent.md" not in result.files
    assert "$IMPLEMENT_TMPDIR/oos-accepted-main-agent.md" not in result.conditional_files
    assert "$IMPLEMENT_TMPDIR/security-oos-observations.md" not in result.files
    assert "$IMPLEMENT_TMPDIR/security-oos-observations.md" not in result.conditional_files


def test_real_review_scan_includes_eager_and_conditional_sources() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    result = scg.scan_skill(repo_root, "review")

    assert "skills/review/SKILL.md" in result.files
    assert "skills/shared/session-setup-output.md" in result.files
    assert "skills/shared/external-reviewers.md" in result.files
    assert "skills/review/references/domain-rules.md" in result.files
    assert "skills/shared/run-id-flag.md" not in result.files
    assert "skills/shared/run-id-flag.md" in result.conditional_files


def test_real_scan_keeps_deliberate_exclusions_untracked() -> None:
    repo_root = Path(__file__).resolve().parents[3]

    for result in scg.scan_all(repo_root):
        assert "SECURITY.md" not in result.files
        assert "SECURITY.md" not in result.conditional_files
        assert "skills/shared/oos-acceptance-rubric.md" not in result.files
        assert "skills/shared/oos-acceptance-rubric.md" not in result.conditional_files


def test_committed_baseline_matches_fresh_scan(tmp_path: Path) -> None:
    """STRICT freshness gate: committed baseline must equal a fresh ``--write``.

    The growth check in ``main`` is one-directional (``live > baseline``), so a
    closure *shrink* passes silently and never forces a re-baseline. This asserts
    byte-exact equality against the same serialization ``--write`` emits, in both
    directions, mirroring the regen-enforced complexity-baseline contract. When it
    fails, run ``make regen-skill-closure-baseline`` and commit the result (#5840).
    """
    repo_root = Path(__file__).resolve().parents[3]
    fresh_path = tmp_path / "fresh-skill-closure-baseline.json"
    scg.write_baseline(fresh_path, scg.scan_all(repo_root))

    committed = (repo_root / scg.BASELINE_RELPATH).read_text(encoding="utf-8")
    fresh = fresh_path.read_text(encoding="utf-8")
    assert committed == fresh, (
        "python/skill-closure-baseline.json is stale; run "
        "`make regen-skill-closure-baseline` and commit the refreshed data."
    )
