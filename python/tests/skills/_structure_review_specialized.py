"""Complete port of test-review-structure.sh."""
# pylint: disable=multiple-statements,subprocess-run-check
from __future__ import annotations

import re
import subprocess
from pathlib import Path


LEGACY_LABELS: frozenset[str] = frozenset(
    {
        "(1)", "(1b)", "(1c)", "(1d)", "(2)", "(3)", "(4)", "(5a)", "(5d)",
        "(6)", "(7)", "(8)", "(9)", "(10)", "(11)", "(12)", "(13)", "(14)",
        "(15)", "(16)", "(17)", "(18)", "(19)", "(20)", "(20a)", "(20b)",
        "(20c)", "(20d)", "(20e)", "(3119)",
    }
)


def run(repo_root: Path) -> list[str]:
    """Return failure labels from the legacy review structure harness."""
    failures: list[str] = []

    def file(name: str) -> Path:
        return repo_root / name

    def read(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return ""

    def require(path: Path, needle: str, label: str) -> None:
        if needle not in read(path):
            failures.append(label)

    skill = file("skills/review/SKILL.md")
    refs = file("skills/review/references")
    scripts = file("skills/review/scripts")
    cli = file("python/larch/cli.py")
    if not skill.is_file(): failures.append(f"(1) skills/review/SKILL.md missing: {skill}")
    if not refs.is_dir(): failures.append(f"(1) skills/review/references/ missing: {refs}")
    if not scripts.is_dir(): failures.append(f"(1) skills/review/scripts/ missing: {scripts}")
    if not skill.is_file() or not refs.is_dir():
        return failures
    skill_text = read(skill)
    lines = skill_text.splitlines()
    if len(lines) > 200:
        failures.append(f"(1) skills/review/SKILL.md must stay <= 200 lines after script extraction (found {len(lines)})")

    review_verbs = (
        "gather-context", "core", "dispatch-panel", "collect-findings",
        "tally-code-votes", "emit-tally", "log-phase",
        "check-reviewer-failure-threshold", "reviewer-prune",
    )
    if len(review_verbs) != 9:
        failures.append("(1) internal harness error: expected review verb list must contain 9 entries")
    for verb in review_verbs:
        require(cli, f'("review", "{verb}")', "(1) missing python/cli.py review " + verb + " registry entry")

    review_and_fix = file("skills/review-and-fix")
    if not (review_and_fix / "SKILL.md").is_file(): failures.append("(1b) missing skills/review-and-fix/SKILL.md")
    if not file("python/larch/review/review_and_fix.py").is_file(): failures.append("(1b) missing python/review_and_fix.py")
    if not cli.is_file(): failures.append("(1b) missing python/cli.py")
    for needle, label in (
        ('("review-and-fix", "apply-findings")', "(1b) missing python/cli.py review-and-fix apply-findings registry entry"),
        ('("review-and-fix", "step5")', "(1b) missing python/cli.py review-and-fix step5 registry entry"),
        ('("redact", "scrub-submodule-paths")', "(1b) missing python/cli.py redact scrub-submodule-paths registry entry"),
    ):
        require(cli, needle, label)
    raf, coder = file("python/larch/review/review_and_fix.py"), file("python/larch/review/coder_runner.py")
    if not ("launch-codex-exec" in read(raf) or "launch-codex-exec" in read(coder)):
        failures.append("(1b) review-and-fix CLI must dispatch Codex coder")
    if not ('"--tool", "cursor"' in read(raf) or '"--tool", "cursor"' in read(coder)):
        failures.append("(1b) review-and-fix CLI must dispatch Cursor coder")
    if "launch-claude-subprocess" in read(raf):
        failures.append("(1b) review-and-fix CLI must not dispatch a Claude subagent fallback")

    aggregator = file("agents/orchestrator-aggregator.md")
    if not aggregator.is_file(): failures.append("(1c) missing agents/orchestrator-aggregator.md")
    require(aggregator, "HAND-MAINTAINED", "(1c) agents/orchestrator-aggregator.md lacks HAND-MAINTAINED annotation")
    if aggregator.name.startswith("reviewer-"): failures.append("(1c) agents/orchestrator-aggregator.md unexpectedly matches reviewer-* glob")
    for name, label in (
        ("agents/reviewer-aggregator.md", "(1d) agents/reviewer-aggregator.md must not exist; use orchestrator-aggregator.md"),
        ("agents/orchestrator-judge.md", "(1d) agents/orchestrator-judge.md must not exist; the code-review panel is launched by python/cli.py agent dispatch-voters"),
        ("skills/review/references/voting.md", "(1d) skills/review/references/voting.md must not exist; code-review voting is now owned by python/cli.py agent dispatch-voters + python/cli.py review tally-code-votes"),
    ):
        if file(name).exists(): failures.append(label)

    expected = ("domain-rules.md",)
    for name in expected:
        if not (refs / name).is_file():
            failures.append(f"(2) expected reference file missing: skills/review/references/{name}")
    mandatory = [line for line in lines if "MANDATORY: READ ENTIRE FILE" in line]
    if not mandatory:
        failures.append("(3) SKILL.md contains zero 'MANDATORY: READ ENTIRE FILE' lines")
    ref_files = sorted(refs.glob("*.md"))
    if not ref_files:
        failures.append(f"(3) no .md files found under {refs} — cannot validate orphan-reference invariant")
    def referenced(name: str) -> bool:
        pattern = re.compile(rf"references/{re.escape(name)}([^A-Za-z0-9._-]|$)")
        return any(pattern.search(line) for line in mandatory)
    for ref in ref_files:
        if not referenced(ref.name):
            failures.append(f"(3) no 'MANDATORY: READ ENTIRE FILE' line in SKILL.md references 'references/{ref.name}' — orphan reference under skills/review/references/")
    for name in expected:
        if not referenced(name):
            failures.append(f"(4) no 'MANDATORY: READ ENTIRE FILE' line in SKILL.md references 'references/{name}' — baseline step-to-reference binding broken")

    domain_pattern = re.compile(r"references/domain-rules\.md([^A-Za-z0-9._-]|$)")
    if not any("MANDATORY: READ ENTIRE FILE" in line and re.search(r"Step 3([^0-9A-Za-z]|$)", line) and domain_pattern.search(line) for line in lines):
        failures.append("(5a) no single SKILL.md line carries 'MANDATORY: READ ENTIRE FILE', 'Step 3' (boundary-anchored), and 'references/domain-rules.md' together — Step 3 entry callsite pin for domain-rules.md is broken")
    require(skill, "agent dispatch-voters", "(5d) SKILL.md must reference python/cli.py agent dispatch-voters — code-review judge panel dispatch contract is broken")
    require(skill, "review tally-code-votes", "(5d) SKILL.md must reference python/cli.py review tally-code-votes — code-review vote tally contract is broken")

    enum = "code-quality / risk-integration / correctness / architecture"
    enum_lines = [line for line in lines if enum in line]
    if not enum_lines:
        failures.append("(6) SKILL.md lacks the unquoted slash-separated focus-area enum ('code-quality / risk-integration / correctness / architecture') — CI's agent-sync UNQUOTED_FILES guard would fail")
    for line in enum_lines:
        if "security" not in line:
            failures.append("(6) focus-area enum line lacks 'security' on same line — CI's agent-sync UNQUOTED_FILES guard would fail: " + line)
    require(skill, "**Anti-halt continuation reminder.**", "(7) SKILL.md lacks anti-halt banner substring '**Anti-halt continuation reminder.**'")
    require(skill, "Continue after child returns", "(8) SKILL.md lacks micro-reminder substring 'Continue after child returns'")
    for ref in ref_files:
        opening = "\n".join(read(ref).splitlines()[:20])
        for header in ("**Consumer**:", "**Binding convention**:"):
            if header not in opening:
                failures.append(f"(9) references/{ref.name} must open with '{header}' header in the first 20 lines")
    if not any("--diff" in line and "positional description" in line.lower() for line in lines):
        failures.append("(10) no single SKILL.md line carries '--diff' and 'positional description' together — mode activation contract pin is broken")
    require(skill, "**⚠ --diff cannot be combined with a description. Use --diff alone for branch diff review, or provide a description without --diff. Aborting.**", "(11) SKILL.md is missing the verbatim --diff+description mutual-exclusion abort message")
    require(skill, "**⚠ /review requires either --diff (branch diff review) or a description of what to review.", "(12) SKILL.md is missing the verbatim no-args error abort message")

    collect = file("python/larch/review/review_collect.py")
    if not any(all(token in line for token in ("agent collect-results", "--timeout 1860", "--substantive-validation", "--validation-mode")) for line in read(collect).splitlines()):
        failures.append("(13) no review collect-findings implementation line carries 'agent collect-results', '--timeout 1860', '--substantive-validation', and '--validation-mode' together — issue #661 substantive-validation contract pin is broken")
    require(skill, "python/cli.py render specialist", "(14) SKILL.md does not reference 'python/cli.py render specialist' — specialist prompt rendering is not wired")
    require(file("python/larch/rendering/rendering.py"), "--mode", "(14) python/rendering.py does not accept '--mode' — diff/description mode handling is missing")
    renderer = file("python/larch/rendering/rendering.py")
    if not renderer.is_file(): failures.append("(15) python/rendering.py does not exist — specialist prompt rendering is broken")
    for name in ("reviewer-structure", "reviewer-correctness", "reviewer-testing", "reviewer-security", "reviewer-edge-cases"):
        agent = file(f"agents/{name}.md")
        if not agent.is_file():
            failures.append(f"(15) agents/{name}.md does not exist — specialist agent definition is missing")
        require(agent, "### In-Scope Findings", f"(15) agents/{name}.md is missing '### In-Scope Findings' section header — dual-list output contract is broken")
        require(agent, "### Out-of-Scope Observations", f"(15) agents/{name}.md is missing '### Out-of-Scope Observations' section header — dual-list output contract is broken")
    collect_lines = read(collect).splitlines()
    if not any(all(token in line for token in ("In description mode", "dual-list output", "### In-Scope Findings", "### Out-of-Scope Observations")) for line in collect_lines):
        failures.append("(16) no review collect-findings implementation line carries 'In description mode', 'dual-list output', '### In-Scope Findings', AND '### Out-of-Scope Observations' together — Step 3a description-mode dual-list parsing contract is broken")
    if not any(all(token in line for token in ("In diff mode", "single-list output", "entire output")) for line in collect_lines):
        failures.append("(17) no review collect-findings implementation line carries 'In diff mode', 'single-list output', AND 'entire output' together — Step 3a diff-mode single-list preservation is broken")
    for needle, label in (
        ("> **🔶 /review 4: final summary**", "(18) SKILL.md missing Step 4 progress pin — final summary step drifted"),
        ("If `RUN_ID` is non-empty, write flat review larch-log batches", "(18) SKILL.md missing Step 4 larch-log batch opener — filing semantics drifted"),
        ("`review-context`", "(18) SKILL.md missing review-context batch token — Step 4 filing list drifted"),
        ("review log-phase", "(18) SKILL.md must reference review log-phase in Step 4 — filing wiring drifted"),
    ): require(skill, needle, label)
    if "/umbrella" in skill_text: failures.append("(19) SKILL.md must not reference '/umbrella' — removed umbrella composition must not return")

    protocol, voting, types = file("skills/shared/voting-protocol.md"), file("python/larch/review/voting.py"), file("python/larch/review/review_types.py")
    if not protocol.is_file(): failures.append("(20) skills/shared/voting-protocol.md missing")
    for needle, label in (
        ("security-tagged findings (focus-area=security) are held locally and NEVER filed publicly", "(20a) voting-protocol.md security guard prose drifted"),
        ("Match discrimination (false-positive guard)", "(20b) voting-protocol.md missing Match discrimination procedure"),
        ("Security counter-invariant", "(20c) voting-protocol.md missing Security counter-invariant clause"),
    ): require(protocol, needle, label)
    if not voting.is_file(): failures.append("(20) python/larch/review/voting.py missing")
    if not types.is_file(): failures.append("(20) python/larch/review/review_types.py missing")
    require(types, "_SECURITY_FIELD_RE", "(20d) review_types.py must carry _SECURITY_FIELD_RE for is_security_block_text")
    require(voting, "is_security_block_text", "(20e) voting.py::is_security_block must delegate to review_types.is_security_block_text")

    for check, label in (
        (file("skills/review/references/heavy-worker.md"), "(3119) heavy-worker.md still has removed Family-B fence tokens"),
        (file("skills/shared/external-reviewers.md"), "(3119) external-reviewers.md still has removed Family-B fence tokens"),
        (protocol, "(3119) voting-protocol.md still has removed Family-B fence tokens"),
    ):
        result = subprocess.run(["python3", str(file("python/cli.py")), "lint", "p3119-fence-absence", str(check), check.name], cwd=repo_root, capture_output=True, text=True)
        if result.returncode: failures.append(label)
    return failures
