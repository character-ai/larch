"""Complete port of scripts/test-research-structure.sh."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path


LEGACY_LABELS: frozenset[str] = frozenset(
    {
        "SKILL.md missing",
        "references/research-phase.md missing",
        "references/validation-phase.md missing",
        "references/citation-validation-phase.md missing",
        "references/critique-loop-phase.md missing",
        "references/adjudication-phase.md must be removed under the simplified shape",
        "[topology]",
        "[header triplet]",
        "[angle prompts]",
        "[reviewer wrappers]",
        "[fail-closed]",
        "[fail-closed recovery hint]",
        "[flag surface]",
        "(3119)",
        "[bgjob transport]",
        "[bgjob collision]",
        "[codex launcher]",
        "[codex telemetry]",
        "[validation sidecar]",
        "[python cli]",
        "[not-substantive]",
        "[synthesis gating]",
        "[activation]",
    }
)


def run(repo_root: Path) -> list[str]:
    """Return failure labels from the legacy research structure harness."""
    failures: list[str] = []

    def path(name: str) -> Path:
        return repo_root / name

    def text(file: Path) -> str:
        try:
            return file.read_text(encoding="utf-8")
        except OSError:
            return ""

    def contains(file: Path, literal: str, label: str) -> None:
        if literal not in text(file):
            failures.append(label)

    skill = path("skills/research/SKILL.md")
    research = path("skills/research/references/research-phase.md")
    validation = path("skills/research/references/validation-phase.md")
    citation = path("skills/research/references/citation-validation-phase.md")
    critique = path("skills/research/references/critique-loop-phase.md")
    refs = research.parent
    required = (
        (skill, "SKILL.md missing"),
        (research, "references/research-phase.md missing"),
        (validation, "references/validation-phase.md missing"),
        (citation, "references/citation-validation-phase.md missing"),
        (critique, "references/critique-loop-phase.md missing"),
    )
    for file, label in required:
        if not file.is_file():
            failures.append(f"{label}: {file}")
    if failures:
        return failures

    if (refs / "adjudication-phase.md").is_file():
        failures.append(
            "references/adjudication-phase.md must be removed under the simplified shape"
        )

    skill_text = text(skill)
    mandatory = [
        line for line in skill_text.splitlines() if "MANDATORY: READ ENTIRE FILE" in line
    ]
    topology = {
        "research-phase.md": (
            "validation-phase.md",
            "citation-validation-phase.md",
            "critique-loop-phase.md",
        ),
        "validation-phase.md": (
            "research-phase.md",
            "citation-validation-phase.md",
            "critique-loop-phase.md",
        ),
        "citation-validation-phase.md": (
            "research-phase.md",
            "validation-phase.md",
            "critique-loop-phase.md",
        ),
        "critique-loop-phase.md": (
            "research-phase.md",
            "validation-phase.md",
            "citation-validation-phase.md",
        ),
    }
    for target, others in topology.items():
        lines = [line for line in mandatory if target in line]
        if not lines:
            failures.append(
                f"[topology] no MANDATORY: READ ENTIRE FILE line in SKILL.md names '{target}'"
            )
            continue
        # Bash's command substitution can retain multiple matching lines; each
        # following grep searches the complete resulting text.
        selected = "\n".join(lines)
        for other in others:
            if "Do NOT load" not in selected or other not in selected:
                failures.append(
                    f"[topology] MANDATORY line for '{target}' does not carry "
                    f"'Do NOT load {other}' on the same line"
                )

    for ref in (research, validation, citation, critique):
        opening = "\n".join(text(ref).splitlines()[:20])
        for pattern in (r"^\*\*Consumer\*\*:", r"^\*\*Contract\*\*:", r"^\*\*When to load\*\*:"):
            if not re.search(pattern, opening, re.MULTILINE):
                failures.append(
                    f"[header triplet] {ref.name} must open with anchored header "
                    f"matching '{pattern}' in the first 20 lines"
                )

    for angle in ("ARCH", "EDGE", "EXT", "SEC"):
        contains(
            research,
            f"RESEARCH_PROMPT_{angle}",
            f"[angle prompts] research-phase.md lacks RESEARCH_PROMPT_{angle} identifier",
        )
    for tag in ("<reviewer_research_question>", "<reviewer_research_findings>"):
        contains(
            validation,
            tag,
            f"[reviewer wrappers] validation-phase.md lacks XML wrapper tag '{tag}'",
        )
    contains(skill, "Fail-closed unknown-flag guard", "[fail-closed] SKILL.md must contain 'Fail-closed unknown-flag guard' heading/marker")
    contains(skill, "unsupported flag", "[fail-closed] SKILL.md must contain 'unsupported flag' abort message")
    for category in ("scale", "plan", "interactive", "adjudicate", "token-budget", "keep-sidecar", "verbosity"):
        contains(skill, category, f"[fail-closed recovery hint] SKILL.md must mention removed-flag category '{category}' in the unknown-flag-guard recovery hint")
    contains(skill, "--no-issue", "[flag surface] SKILL.md must surface --no-issue")

    for file, display in ((skill, "SKILL.md"), (research, "research-phase.md"), (validation, "validation-phase.md")):
        result = subprocess.run(
            ["python3", str(path("python/cli.py")), "lint", "p3119-fence-absence", str(file), display],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            failures.append(f"(3119) {display} still has removed Family-B fence tokens")

    research_tree = path("skills/research")
    if any("run_in_background" in text(file) for file in research_tree.rglob("*") if file.is_file()):
        failures.append("[bgjob transport] skills/research must not retain run_in_background literals")
    for literal, label in (
        ("For Codex lanes, call `bgjob start` once per lane from foreground Bash with a unique `--step` slug.", "[bgjob transport] research-phase.md must require per-lane bgjob starts"),
        ('python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" bgjob start \\', "[bgjob transport] research-phase.md must invoke bgjob start"),
        ('python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" bgjob wait \\', "[bgjob transport] research-phase.md must invoke bgjob wait"),
        ("If stdout contains `BGJOB_STATUS=WAIT`, the next action is the same wait command for the same slot with no intervening prose, reads, monitors, probes, sleeps, or other tools.", "[bgjob transport] research-phase.md must pin immediate repeated wait"),
        ("continue the lane as passed when either the DONE stdout KV block or", "[bgjob transport] research-phase.md must gate continuation on stdout KV or result env"),
    ):
        contains(research, literal, label)
    for slug in ("research-arch", "research-edge", "research-ext", "research-sec"):
        contains(research, f"--step {slug}", f"[bgjob transport] research-phase.md missing --step {slug}")
        contains(research, f"$RESEARCH_TMPDIR/bgjob/{slug}.result.env", f"[bgjob transport] research-phase.md missing result env for {slug}")
        contains(research, f"$RESEARCH_TMPDIR/.{slug}-merge.env", f"[bgjob transport] research-phase.md missing merge env for {slug}")
    for literal, label in (
        ("Cursor and Codex use foreground `bgjob start` launches with unique per-lane step slugs.", "[bgjob transport] validation-phase.md must require external bgjob starts"),
        ('python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" bgjob start \\', "[bgjob transport] validation-phase.md must invoke bgjob start"),
        ('python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" bgjob wait \\', "[bgjob transport] validation-phase.md must invoke bgjob wait"),
        ("If stdout contains `BGJOB_STATUS=WAIT`, the next action is the same wait command for that lane with no intervening prose, reads, monitors, probes, sleeps, or other tools.", "[bgjob transport] validation-phase.md must pin immediate repeated wait"),
        ("continue the lane as passed when either the DONE stdout KV block or", "[bgjob transport] validation-phase.md must gate continuation on stdout KV or result env"),
        ("`validation-code`", "[bgjob transport] validation-phase.md must retain Code lane identity"),
    ):
        contains(validation, literal, label)
    for slug in ("validation-cursor", "validation-codex"):
        contains(validation, f"--step {slug}", f"[bgjob transport] validation-phase.md missing --step {slug}")
        contains(validation, f"$RESEARCH_TMPDIR/bgjob/{slug}.result.env", f"[bgjob transport] validation-phase.md missing result env for {slug}")
        contains(validation, f"$RESEARCH_TMPDIR/.{slug}-merge.env", f"[bgjob transport] validation-phase.md missing merge env for {slug}")
    result_paths = {
        f"$RESEARCH_TMPDIR/bgjob/{slug}.result.env"
        for slug in ("research-arch", "research-edge", "research-ext", "research-sec", "validation-cursor", "validation-codex")
    }
    if len(result_paths) != 6:
        failures.append("[bgjob collision] expected distinct result env paths for all bgjob lanes")

    for stem in ("codex-research-arch-output.txt", "codex-research-edge-output.txt", "codex-research-ext-output.txt", "codex-research-sec-output.txt"):
        contains(research, stem, f"[codex launcher] research-phase.md must pin expected output stem '{stem}'")
    launcher = 'python3 "${CLAUDE_PLUGIN_ROOT:?}/python/cli.py" agent launch-codex-exec'
    for file, stem in ((research, "codex-research-arch-output.txt"), (validation, "codex-validation-output.txt")):
        contains(file, launcher, f"[codex launcher] {file.name} must use python3 ${{CLAUDE_PLUGIN_ROOT:?}}/python/cli.py agent launch-codex-exec")
        contains(file, stem, f"[codex launcher] {file.name} must pin expected output stem '{stem}'")
    voting = path("skills/shared/voting-protocol.md")
    contains(voting, "${CLAUDE_PLUGIN_ROOT:?}/python/cli.py agent launch-codex-exec", "[codex launcher] voting-protocol.md must keep documentary Codex dispatch token")
    contains(voting, "codex-vote-output.txt", "[codex launcher] voting-protocol.md must pin expected output stem 'codex-vote-output.txt'")

    if not ("Non-fallback Codex lanes receive best-effort usage records" in text(research) and "${OUTPUT}.token-record" in text(research)):
        failures.append("[codex telemetry] research-phase.md must pin best-effort Codex usage records")
    if "codex telemetry is unmeasurable" in text(research).lower():
        failures.append("[codex telemetry] research-phase.md must not claim Codex telemetry is unmeasurable")

    for file in (research, validation):
        for literal in ("token append-record", "token record-vendor-sidecar", "env -u LARCH_TOKEN_LEDGER", "-u LARCH_TOKEN_SESSION_ID", 'RESEARCH_TMPDIR="$RESEARCH_TMPDIR"'):
            contains(file, literal, f"[{file.name} sidecar] missing {literal}")
    vlines = text(validation).splitlines()
    def first_line(needle: str) -> int | None:
        return next((index for index, line in enumerate(vlines, 1) if needle in line), None)
    indices = [first_line(needle) for needle in (
        'python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" agent collect-results --timeout 1860 --substantive-validation --validation-mode',
        "1. Parse the structured output for each reviewer's `STATUS` and `REVIEWER_FILE`.",
        "2. **Codex/Cursor validation sidecar ingestion after collection settles**",
        "3. **Runtime fallback replacement**",
    )]
    present = [item for item in indices if item is not None]
    if len(present) != len(indices) or present != sorted(present):
        failures.append("[validation sidecar] ingestion must follow collect/result parsing and precede status decisions")
    for literal, label in (
        ("REVIEWER_FILE", "[validation sidecar] candidate expansion must include REVIEWER_FILE"),
        ("-retry.txt", "[validation sidecar] candidate expansion must include -retry.txt"),
        ("No non-substantive retry artifacts are created", "[validation sidecar] must document no non-substantive retry artifacts"),
        ("Deduplicate candidate paths before ingestion.", "[validation sidecar] candidate expansion must dedupe paths"),
    ):
        contains(validation, literal, label)

    for file, literal, label in (
        (research, 'python/cli.py" research run-planner', "[python cli] research-phase.md must pin research run-planner in §1.1.b"),
        (research, "python/cli.py research run-planner", "[python cli] research-phase.md must pin research run-planner in §1.1.c edit loop"),
        (citation, 'python/cli.py" research validate-citations', "[python cli] citation-validation-phase.md must pin research validate-citations"),
        (skill, 'python/cli.py" research validate-citations', "[python cli] SKILL.md must pin research validate-citations at Step 2.5"),
        (research, 'python/cli.py" research banner', "[python cli] research-phase.md must pin research banner at Step 1.5"),
        (skill, "python/cli.py research render-findings-batch", "[python cli] SKILL.md must pin research render-findings-batch at Step 3"),
    ):
        contains(file, literal, label)
    for literal, label in (
        ("STATUS=NOT_SUBSTANTIVE", "[not-substantive] research-phase.md must pin terminal NOT_SUBSTANTIVE status"),
        ("do not launch a Claude replacement", "[not-substantive] research-phase.md must block Claude replacement"),
        ("do not pass the narrative file to synthesis", "[not-substantive] research-phase.md must exclude narrative output from synthesis"),
        ("No non-substantive retry artifacts are created", "[not-substantive] research-phase.md must pin absent retry artifacts"),
        ("Do NOT emit a `## Research Synthesis` header", "[synthesis gating] research-phase.md must pin orchestrator-owned synthesis header"),
        ("[lane dropped: collector NOT_SUBSTANTIVE]", "[synthesis gating] research-phase.md must pin NOT_SUBSTANTIVE dropped-lane marker"),
    ):
        contains(research, literal, label)
    for literal, label in (
        ('command: "${CLAUDE_PLUGIN_ROOT}/scripts/deny-edit-write.sh research"', "[activation] SKILL.md frontmatter must pass research token"),
        ('RESEARCH_DENY_ACTIVE_SENTINEL="$RESEARCH_DENY_ACTIVE_DIR/research-$PPID"', "[activation] SKILL.md must create research-$PPID sentinel"),
        ("**⚠ /research: failed to activate read-only Write/Edit hook. Aborting.**", "[activation] sentinel write failure must abort loudly"),
        ("A leaked hook registration without a fresh `research-*` sentinel allows with empty stdout.", "[activation] read-only contract must document inactive fail-open behavior"),
        ("any other active path outcome denies.", "[activation] read-only contract must keep active fail-closed path behavior"),
        ('Remove `"$RESEARCH_DENY_ACTIVE_SENTINEL"` before stopping.', "[activation] filing VERIFIED=false branch must remove sentinel"),
        ('Remove `"$RESEARCH_DENY_ACTIVE_SENTINEL"` before stopping. Research-result-filing semantics require all items to succeed', "[activation] filing ISSUES_FAILED branch must remove sentinel"),
        ('remove `"$RESEARCH_DENY_ACTIVE_SENTINEL"`, print `**⚠ 3.5: auto-issue: /issue failed (REASON=<token>). Research results were not archived to GitHub. Continuing.**`, and proceed to Step 4.', "[activation] auto-issue failure must remove sentinel"),
        ('rm -f "$RESEARCH_DENY_ACTIVE_SENTINEL"', "[activation] Step 4 cleanup must remove sentinel"),
    ):
        contains(skill, literal, label)
    contains(research, 'rm -f "$RESEARCH_DENY_ACTIVE_SENTINEL"', "[activation] research-phase abort branches must remove sentinel")
    slines = skill_text.splitlines()
    gate = activation = write = None
    for index, line in enumerate(slines, 1):
        if gate is None and "**Degraded-tools gate (#3207).**" in line: gate = index
        if activation is None and "### 0a.5: Activate read-only Write/Edit hook" in line: activation = index
        if write is None and "Write `$RESEARCH_TMPDIR/lane-status.txt`" in line: write = index
    if not (gate and activation and write and gate < activation < write):
        failures.append("[activation] sentinel creation must follow degraded-tools gate and precede first Write")
    return failures
