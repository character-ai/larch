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


def write_roots(root: Path, *, design: str = "", implement: str = "") -> None:
    write(root, "skills/design/SKILL.md", design or "Design root\n")
    write(root, "skills/implement/SKILL.md", implement or "Implement root\n")


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
    )
    write(root, "skills/design/references/flags.md", "flag one\nflag two\n")
    write(root, "skills/implement/references/self-review.md", "review one\n")


def write_baseline_from_live(root: Path) -> list[scg.SkillClosureResult]:
    results = scg.scan_all(root)
    scg.write_baseline(root / "python/skill-closure-baseline.json", results)
    return results


def test_design_and_implement_roots_are_scanned_separately(tmp_path: Path) -> None:
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


def test_non_markdown_references_are_ignored(tmp_path: Path) -> None:
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
    write_roots(tmp_path, design="a\n" + ("\n" * 100))
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
    assert [row["skill"] for row in payload] == ["design", "implement"]
    assert all(set(row.keys()) == set(scg.BASELINE_KEYS) for row in payload)
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


def test_report_mode_prints_design_and_implement(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
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
    )
    write(tmp_path, "skills/design/references/flags.md", "flag one\nflag two\n")
    write(tmp_path, "skills/design/references/conditional.md", "conditional\n")
    write(tmp_path, "skills/implement/references/self-review.md", "review one\n")

    assert scg.report_main(["--root", str(tmp_path)]) == 0

    out = capsys.readouterr().out
    assert "Eager closure (ratcheted)" in out
    assert "Conditional closure (reported only)" in out
    assert "skill_content_tokens" in out
    assert "closure_content_tokens" in out
    assert "conditional_content_tokens" in out
    assert "design" in out
    assert "implement" in out
    assert "skills/design/SKILL.md" in out
    assert "skills/implement/SKILL.md" in out
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


def test_implement_failure_only_macro_sections_are_excluded_until_next_heading(tmp_path: Path) -> None:
    write_roots(
        tmp_path,
        implement=(
            "root\n"
            "## Checks Failure Entry Macro\n"
            "2. **MANDATORY — READ ENTIRE FILE**: `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/checks-repair-loop.md`.\n"
            "## Durable Bail to Step 18 Macro\n"
            "**MANDATORY — READ ENTIRE FILE**: `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/step5-review-branches.md`; follow durable bail.\n"
            "## Step 5\n"
            "**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/self-review.md` completely.\n"
        ),
    )
    write(tmp_path, "skills/implement/references/checks-repair-loop.md", "checks\n")
    write(tmp_path, "skills/implement/references/step5-review-branches.md", "branches\n")
    write(tmp_path, "skills/implement/references/self-review.md", "review\n")

    result = scg.scan_skill(tmp_path, "implement")

    assert result.files == ("skills/implement/SKILL.md", "skills/implement/references/self-review.md")
    assert not result.conditional_files


def test_real_design_scan_keeps_plan_review_eager_and_branch_refs_conditional() -> None:
    repo_root = Path(__file__).resolve().parents[3]

    result = scg.scan_skill(repo_root, "design")

    assert "skills/design/references/plan-review.md" in result.files
    assert "skills/design/references/plan-review.md" not in result.conditional_files
    assert "skills/design/references/decompose-panel.md" not in result.files
    assert "skills/design/references/validator-failure.md" not in result.files
    assert "skills/design/references/settle-rc-dispatch.md" not in result.files
    assert "skills/design/references/step2b5-rc-handling.md" not in result.files
    assert "skills/design/references/decompose-panel.md" in result.conditional_files
    assert "skills/design/references/validator-failure.md" in result.conditional_files
    assert "skills/design/references/settle-rc-dispatch.md" in result.conditional_files
    assert "skills/design/references/step2b5-rc-handling.md" in result.conditional_files


def test_real_implement_scan_keeps_eager_baseline_unchanged() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    result = scg.scan_skill(repo_root, "implement")
    baseline = next(row for row in scg.load_baseline(repo_root / scg.BASELINE_RELPATH) if row.skill == "implement")

    assert result.files == baseline.files
    assert result.closure_lines == baseline.closure_lines
    assert result.closure_estimated_tokens == baseline.closure_estimated_tokens
    assert "$IMPLEMENT_TMPDIR/oos-accepted-main-agent.md" not in result.files
    assert "$IMPLEMENT_TMPDIR/oos-accepted-main-agent.md" not in result.conditional_files
    assert "$IMPLEMENT_TMPDIR/security-oos-observations.md" not in result.files
    assert "$IMPLEMENT_TMPDIR/security-oos-observations.md" not in result.conditional_files


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
