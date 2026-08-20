"""Non-pin assertions ported from test-design-structure.sh."""
# pylint: disable=multiple-statements
from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

from ._structure_label_inventory import assertion_labels


LEGACY_LABELS: frozenset[str] = assertion_labels(__file__)
LEGACY_ASSERTION_LABEL_COUNT = 16


def run(repo_root: Path) -> list[str]:
    """Return failures for assertions not represented by simple structure pins."""
    failures: list[str] = []

    def p(name: str) -> Path:
        return repo_root / name

    def read(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return ""

    def missing(path: Path, label: str) -> bool:
        if not path.exists():
            failures.append(label)
            return True
        return False

    skill = p("skills/design/SKILL.md")
    migrated = p("python/migrated-scripts.tsv")

    def lines_before(file: Path, anchor: str, count: int, *, predicate: Callable[[str], bool] | None = None) -> str:
        lines = read(file).splitlines()
        for index, line in enumerate(lines):
            if anchor in line and (predicate is None or predicate(line)):
                return "\n".join(lines[max(0, index - count):index])
        return ""

    step3_launch = 'design-run-$PPID.sh" design-step3-review.sh'
    launch_predicate: Callable[[str], bool] = lambda line: "--starting-round" not in line
    for label, count, needle in (
        ("/design Step 3 launch loads bgjob-wait contract", 20, "shared bgjob wait contract"),
        ("/design Step 3 launch pins BGJOB_RC gate", 35, "BGJOB_RC=0"),
        ("/design Step 3 launch names bgjob result env", 35, "bgjob/design-step3-review.result.env"),
    ):
        if needle not in lines_before(skill, step3_launch, count, predicate=launch_predicate):
            failures.append(label)
    step5_anchor = '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step5c.sh'
    for label, needle in (
        ("/design Step 5c uses the bgjob wait contract", "shared bgjob wait contract"),
        ("/design Step 5c names bgjob result env", "bgjob/design-step5c.result.env"),
    ):
        if needle not in lines_before(skill, step5_anchor, 18):
            failures.append(label)
    resume_anchor = '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step3-review.sh --starting-round'
    resume_literal = "Use the same Step 3 bgjob start/rejoin, chunked `bgjob wait`, `BGJOB_RC=0`, and result-env contract as the first-time Step 3 review fence above."
    if resume_literal not in lines_before(skill, resume_anchor, 20):
        failures.append("/design Step 3 resume back-reference precedes its bgjob fence")

    retired = ["design-step0-parse.sh", "design-step0-session.sh", "design-step0-route.sh", "design-step0-clarify-hard-halt.sh", "design-step0-init.sh", "design-step0-abort-cleanup.sh", "design-step0-ap-continue.sh", "design-step0c.sh", "design-step1d5.sh", "design-step1d7.sh", "design-step1e-reentry.sh", "test-design-step0-init.sh", "test-design-step1d5.sh"]
    skill_text, migrated_text = read(skill), read(migrated)
    for name in retired:
        if name in skill_text: failures.append(f"SKILL.md still references retired {name}")
        if (p("skills/design/scripts") / name).exists(): failures.append(f"retired script still exists: {name}")
        if f"skills/design/scripts/{name}" not in migrated_text: failures.append(f"migrated-scripts.tsv missing {name}")

    # The Step 2b post-plan body and the Step 5b.5 diagram classifier moved to
    # Rust (#8583); their structure is guarded by the design_step2b parity and
    # unit tests in crates/larch-cli, not by these Python-source pins.

    gate_c = p("skills/design/references/approval-gates-gate-c.md")
    gate_lines = read(gate_c).splitlines()
    def line_number(needle: str) -> int | None:
        return next((n for n, line in enumerate(gate_lines, 1) if needle in line), None)
    invariant_persist = line_number("architectural-invariants persist-design-assessment --repo-root")
    guideline_persist = line_number("architectural-guidelines persist-design-assessment --repo-root")
    if invariant_persist is None: failures.append("Gate C missing invariant persist text")
    if guideline_persist is None: failures.append("Gate C missing guideline persist text")
    if invariant_persist is not None and guideline_persist is not None and invariant_persist >= guideline_persist:
        failures.append("Gate C invariant persist must precede guideline persist")
    flow = line_number("INVARIANTS_VIOLATION_ASSESSMENT_REQUIRED=true")
    branch = line_number("**Clean**: only when invariants are `present`")
    if flow is None: failures.append("Gate C missing invariant assessment flow marker")
    if branch is None: failures.append("Gate C missing invariant persist branch marker")
    if flow is not None and branch is not None and flow >= branch:
        failures.append("Gate C invariant assessment flow must precede persist branches")

    skill_lines = skill_text.splitlines()
    def skill_line(needle: str) -> int | None:
        return next((n for n, line in enumerate(skill_lines, 1) if needle in line), None)
    inv_case, guide_case = skill_line("**Step 5c missing-invariant-assessment.**"), skill_line("**Step 5c missing-guideline-assessment.**")
    if inv_case is None: failures.append("SKILL missing invariant assessment special case")
    if guide_case is None: failures.append("SKILL missing guideline assessment special case")
    if inv_case is not None and guide_case is not None and inv_case >= guide_case:
        failures.append("SKILL invariant assessment special case must precede guideline case")

    terminal_retired = ["design-stage-terminal-state.sh", "design-stage-terminal-state.md", "test-design-stage-terminal-state.sh", "test-design-stage-terminal-state.md", "design-failure-report.sh", "design-failure-report.md", "test-design-failure-report.sh", "test-design-failure-report.md", "design-step-final-summary.sh", "design-step-final-summary.md", "_dbg-stage.sh", "_debug-step5c.sh"]
    for name in terminal_retired:
        if (p("skills/design/scripts") / name).exists(): failures.append(f"retired G6.2 script still exists: {name}")
        if f"skills/design/scripts/{name}" not in migrated_text: failures.append(f"migrated-scripts.tsv missing {name}")
    debug_once = "debug-step5c-once.sh"
    if (p("scripts") / debug_once).exists(): failures.append(f"retired G6.2 script still exists: scripts/{debug_once}")
    if f"scripts/{debug_once}" not in migrated_text: failures.append(f"migrated-scripts.tsv missing scripts/{debug_once}")

    step2_retired = ["design-step2a.sh", "design-step2a.md", "design-step2b-drafter.sh", "design-step2b-drafter.md", "design-step2b-postplan.sh", "design-step2b-postplan.md", "design-step2b5.sh", "design-step2b5.md", "design-step-validator-autofix.sh", "design-step-validator-autofix.md", "design-step2b-prelude.sh", "design-step2b-prelude.md", "test-design-step2b-drafter.sh", "test-design-step2b-drafter.md", "test-design-step-validator-autofix.sh", "test-design-step-validator-autofix.md"]
    for name in step2_retired:
        if (p("skills/design/scripts") / name).exists(): failures.append(f"retired Step 2 script still exists: {name}")
        if f"skills/design/scripts/{name}" not in migrated_text: failures.append(f"migrated-scripts.tsv missing {name}")
    step6_retired = ["design-step6.sh", "design-step6.md", "design-step6-prelude.sh", "design-step6-prelude.md", "design-step6-cleanup.sh", "design-step6-cleanup.md", "test-design-step6.sh", "_dbg-validator.sh", "_dbg5c2.sh"]
    for name in step6_retired:
        if (p("skills/design/scripts") / name).exists(): failures.append(f"retired Step 6 script still exists: {name}")
        if f"skills/design/scripts/{name}" not in migrated_text: failures.append(f"migrated-scripts.tsv missing {name}")
        if name in skill_text: failures.append(f"SKILL.md still references retired {name}")

    finalize = p("skills/design/references/finalize-step5.md")
    if missing(finalize, "finalize-step5 reference missing"):
        pass
    else:
        for header in ("Consumer", "Contract", "When to load"):
            if not re.search(rf"^\*\*{re.escape(header)}\*\*:", read(finalize), re.MULTILINE):
                failures.append(f"finalize-step5 must anchor {header} header")
        count = read(finalize).count("readability-style.md")
        if count != 1: failures.append(f"finalize-step5 must reference readability-style.md once, found {count}")
    entry_count = skill_text.count('"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step3-entry.sh')
    if entry_count != 1: failures.append(f"SKILL must retain exactly one Step 3 entry launcher fence, found {entry_count}")
    bypass_count = skill_text.count("plan-review step3-gate-b-bypass")
    if bypass_count != 1: failures.append(f"SKILL must directly invoke the Gate-B-bypass entry point once before routing rows, found {bypass_count}")

    attic = p("docs/attic/dialectic-legacy.md")
    if not attic.is_file(): failures.append("dialectic legacy attic doc missing")
    if p("skills/design/references/dialectic-legacy.md").exists(): failures.append("retired dialectic-legacy runtime reference still exists")
    oos = p("skills/design/references/oos-step5b-dispatch.md")
    if not oos.is_file(): failures.append("oos step5b dispatch reference missing")
    elif not re.search(r"^\*\*When to load\*\*:", read(oos), re.MULTILINE): failures.append("oos step5b dispatch must anchor When to load header")
    settle = p("skills/design/references/settle-rc-dispatch.md")
    if not settle.is_file(): failures.append("settle rc dispatch reference missing")
    elif not re.search(r"^\*\*When to load\*\*:", read(settle), re.MULTILINE): failures.append("settle rc dispatch must anchor When to load header")

    return failures
