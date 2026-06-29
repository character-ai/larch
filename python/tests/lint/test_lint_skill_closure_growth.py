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


def test_conditional_references_are_excluded_by_text_rules(tmp_path: Path) -> None:
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


def test_write_regenerates_canonical_json(tmp_path: Path) -> None:
    fixture_project(tmp_path)

    assert scg.main(["--root", str(tmp_path), "--write"]) == 0

    baseline_path = tmp_path / "python/skill-closure-baseline.json"
    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert [row["skill"] for row in payload] == ["design", "implement"]
    assert baseline_path.read_text(encoding="utf-8").endswith("\n")


def test_report_mode_prints_design_and_implement(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    fixture_project(tmp_path)

    assert scg.report_main(["--root", str(tmp_path)]) == 0

    out = capsys.readouterr().out
    assert "design" in out
    assert "implement" in out
    assert "skills/design/SKILL.md" in out
    assert "skills/implement/SKILL.md" in out


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
