"""Immutable skill-structure pin tables.

Simple contains/absent/count/ordered/adjacent-pair contracts for design and
umbrella live here. Alias, file-bug, learn-from-bugs, implement, research, and review
structure contracts are covered by complete specialized ports in sibling modules
(executable loops, CLI lints, proximity windows, and regex-BRE semantics).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, Literal

PredicateKind = Literal[
    "contains",
    "absent",
    "exact_count",
    "count_at_least",
    "ordered",
    "same_line",
    "adjacent_pair_count_at_least",
    "cross_file_bound",
]
MatchKind = Literal["fixed", "regex"]
CountUnit = Literal["physical_line", "matching_line", "substring", "adjacent_pair"]
Comparator = Literal["exact", "at_least"]
MatchMode = Literal["exact_line", "contains"]


@dataclass(frozen=True, slots=True)
class StructurePin:
    """One legacy structure assertion expressed as data."""

    skill: str
    label: str
    path: str
    kind: PredicateKind
    needle: str = ""
    needle2: str = ""
    tokens: tuple[str, ...] = ()
    path2: str = ""
    expected: int | None = None
    bound: int | None = None
    match: MatchKind = "fixed"
    count_unit: CountUnit = "matching_line"
    comparator: Comparator = "exact"
    match_mode: MatchMode = "exact_line"

    @property
    def param_id(self) -> str:
        raw = f"{self.skill}-{self.label}"
        cleaned = re.sub(r"[^A-Za-z0-9]+", "-", raw).strip("-").lower()
        return cleaned or f"{self.skill}-unnamed"


ALIAS_PINS: Final[tuple[StructurePin, ...]] = ()
BUG_PINS: Final[tuple[StructurePin, ...]] = ()
LEARN_FROM_BUGS_PINS: Final[tuple[StructurePin, ...]] = ()
IMPLEMENT_PINS: Final[tuple[StructurePin, ...]] = ()
RESEARCH_PINS: Final[tuple[StructurePin, ...]] = ()
REVIEW_PINS: Final[tuple[StructurePin, ...]] = ()
UMBRELLA_PINS: Final[tuple[StructurePin, ...]] = (
    StructurePin(skill="umbrella", label="prepared handoff must require parent lifecycle context", path="skills/umbrella/SKILL.md", kind="contains", needle="Accept that group only with a leading `--lifecycle-parent-context`, `--skip-approve`, and one numeric issue."),
    StructurePin(skill="umbrella", label="umbrella must activate its token-scoped Write sentinel", path="skills/umbrella/SKILL.md", kind="contains", needle='UMBRELLA_DENY_ACTIVE_SENTINEL="$UMBRELLA_DENY_ACTIVE_DIR/umbrella-$PPID"'),
    StructurePin(skill="umbrella", label="prepared handoff must persist dependency copy through umbrella owner", path="skills/umbrella/SKILL.md", kind="contains", needle='--deps-output "$UMBRELLA_TMPDIR/prepared-deps.tsv"'),
    StructurePin(skill="umbrella", label="standard and adopted filing must pass drafted dependency edges", path="skills/umbrella/SKILL.md", kind="contains", needle='--intra-batch-deps-file "$UMBRELLA_TMPDIR/drafted-deps.tsv"'),
    StructurePin(skill="umbrella", label="degraded issue filing must recover every persisted dependency edge", path="skills/umbrella/SKILL.md", kind="contains", needle="apply every recorded edge directly with `issue add-blocked-by`"),
    StructurePin(skill="umbrella", label="prepared handoff must retain normal dedup", path="skills/umbrella/SKILL.md", kind="contains", needle="the exact persisted parent-approved edges are authoritative while normal duplicate detection remains enabled"),
    StructurePin(skill="umbrella", label="standard and adopted final verify must use only proposal and leaves", path="skills/umbrella/SKILL.md", kind="contains", needle="For standard and adopted sources, invoke final verification only with the persisted proposal and fresh leaves:"),
    StructurePin(skill="umbrella", label="final verify must compose fresh read-back leaves", path="skills/umbrella/SKILL.md", kind="contains", needle="as a JSON array of `number`, `title`, and `body` rows"),
    StructurePin(
        skill="umbrella",
        label="prepared completion sentinel must bind live inputs",
        path="skills/umbrella/SKILL.md",
        kind="contains",
        needle=(
            '--sentinel-file "$COMPLETION_SENTINEL" \\\n'
            '  --sentinel-root "$PREPARED_ROOT" \\\n'
            '  --prepared-input "$PREPARED_INPUT_FILE" \\\n'
            '  --prepared-deps "$PREPARED_DEPS_FILE"'
        ),
    ),
)

DESIGN_PINS: Final[tuple[StructurePin, ...]] = (
    StructurePin(skill="design", label="Split-path must invoke umbrella through Skill tool", path="skills/design/references/decompose-panel.md", kind="contains", needle="Invoke `/umbrella` via the Skill tool:"),
    StructurePin(skill="design", label="Split-path must pass exact prepared input", path="skills/design/references/decompose-panel.md", kind="contains", needle='--prepared-input-file "$DESIGN_TMPDIR/decompose/partition-input.txt"'),
    StructurePin(skill="design", label="Split-path must verify identity-bound umbrella completion", path="skills/design/references/decompose-panel.md", kind="contains", needle="umbrella verify-completion"),
    StructurePin(skill="design", label="Split-path must not directly invoke issue batch", path="skills/design/references/decompose-panel.md", kind="absent", needle="invoke `/larch:issue` in batch mode"),
    StructurePin(skill="design", label="Split-path must not call close-original", path="skills/design/references/decompose-panel.md", kind="absent", needle='python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" decompose close-original'),
    StructurePin(skill="design", label="Step 3 must load runtime slice before entry", path="skills/design/SKILL.md", kind="contains", needle="**MANDATORY: READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/plan-review-runtime.md` completely before invoking `design-step3-entry.sh`; the entry wrapper emits the preview internally."),
    StructurePin(skill="design", label="Gate B slice must load unconditionally", path="skills/design/SKILL.md", kind="contains", needle="approval-gates-gate-b.md` completely. This Gate B slice is unconditional"),
    StructurePin(skill="design", label="Gate C slice must load unconditionally", path="skills/design/SKILL.md", kind="contains", needle="approval-gates-gate-c.md` completely. This Gate C slice is unconditional"),
    StructurePin(skill="design", label="failure slice must load before failed final summary", path="skills/design/SKILL.md", kind="contains", needle="finalize-step5-failures.md` immediately before staging/export and before this fence"),
    StructurePin(skill="design", label="Gate A re-entry must load Step 3 runtime before entry", path="skills/design/references/approval-gates-gate-a.md", kind="contains", needle="plan-review-runtime.md` completely before invoking `design-step3-entry.sh --reentry`"),
    StructurePin(skill="design", label="Gate C re-entry must load Step 3 runtime before entry", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle="plan-review-runtime.md` completely before invoking `design-step3-entry.sh --reentry`"),
    StructurePin(skill="design", label="green finalize must exclude failure reporting", path="skills/design/references/finalize-step5.md", kind="absent", needle="## /design auto error reporting"),
    StructurePin(skill="design", label="failure slice must own error reporting", path="skills/design/references/finalize-step5-failures.md", kind="contains", needle="## /design auto error reporting"),
    StructurePin(skill="design", label="Step 1c sprawl must enter the unified Split-path directly", path="skills/design/references/discussion-rounds.md", kind="contains", needle="enter the unified **Split-path** directly"),
    StructurePin(skill="design", label="Step 1c sprawl must not ask a preliminary Split/Cancel question", path="skills/design/references/discussion-rounds.md", kind="absent", needle='exactly two options: **"Let my panel of agents split this feature for you"** / **"Cancel"**'),
    StructurePin(skill="design", label="Step 0 session fence must call the Rust-owned larch.sh verb", path="skills/design/SKILL.md", kind="contains", needle='"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" design step0-session'),
    StructurePin(skill="design", label="Step 0 title cancel routes must use the shared final summary terminalizer", path="skills/design/SKILL.md", kind="contains", needle="For `cancel-title-filter` / `cancel-reentry-guard`, set `SUMMARY_OUTCOME=cancelled-title-filter` / `cancelled-reentry-guard`, run the **Final summary block** through its Read/cache path"),
    StructurePin(skill="design", label="AGENTS.md must pin bgjob-owned long-helper waits", path="AGENTS.md", kind="contains", needle="Use larch bgjob daemons for long helpers"),
    StructurePin(skill="design", label="Design anti-patterns must retain Monitor ban stub", path="skills/design/SKILL.md", kind="contains", needle="NEVER use the `Monitor` tool anywhere within the `/design` orchestrator"),
    StructurePin(skill="design", label="Design anti-patterns must retain bgjob wait primary guidance", path="skills/design/SKILL.md", kind="contains", needle="Use the shared bgjob wait contract for migrated long helpers, not Bash polling loops."),
    StructurePin(skill="design", label="Design anti-patterns must retain background recovery waiter ban", path="skills/design/SKILL.md", kind="contains", needle="NEVER launch a background recovery waiter"),
    StructurePin(skill="design", label="Design anti-patterns must retain Monitor fallback ban", path="skills/design/SKILL.md", kind="contains", needle="Do NOT fall back to Monitor"),
    StructurePin(skill="design", label="Design anti-pattern #5 must pin WAIT repeat handling", path="skills/design/SKILL.md", kind="contains", needle="`BGJOB_STATUS=WAIT` means run the identical `bgjob wait` again with no intervening prose or tools."),
    StructurePin(skill="design", label="Design anti-pattern #5 must pin DONE result-env handling", path="skills/design/SKILL.md", kind="contains", needle="`BGJOB_STATUS=DONE` permits normal continuation only when `BGJOB_RC=0` and the required KVs are present in the bgjob result env."),
    StructurePin(skill="design", label="Design anti-patterns must not treat AskUserQuestion no-response as an answer", path="skills/design/SKILL.md", kind="contains", needle="NEVER treat an AskUserQuestion no-response fallback as an operator answer"),
    StructurePin(skill="design", label="Design anti-patterns must not retain wrong/correct probe fence", path="skills/design/SKILL.md", kind="absent", needle="WRONG — background sleep-loop recovery waiter"),
    StructurePin(skill="design", label="Design anti-patterns must not retain DESIGN_TMPDIR prefix prose", path="skills/design/SKILL.md", kind="absent", needle="prefix the foreground probe with a single `DESIGN_TMPDIR=<absolute-path>;` assignment"),
    StructurePin(skill="design", label="Shared orchestrator never must not claim session-start loading", path="skills/shared/orchestrator-never.md", kind="absent", needle="Load once per session"),
    StructurePin(skill="design", label="Implement anti-patterns must not retain routine orchestrator-never wait pointer", path="skills/implement/SKILL.md", kind="absent", needle="See `skills/implement/references/step2-dispatch.md` orchestrator wait contract and `skills/shared/orchestrator-never.md`."),
    StructurePin(skill="design", label="Shared orchestrator never must own bgjob wait rule", path="skills/shared/orchestrator-never.md", kind="contains", needle="NEVER wait on long helpers with task-output reads, Monitor, sleeps, or ad-hoc probes."),
    StructurePin(skill="design", label="Shared orchestrator never must document identical wait repeats", path="skills/shared/orchestrator-never.md", kind="contains", needle="After `BGJOB_STATUS=WAIT`, run the identical wait again with no intervening prose"),
    StructurePin(skill="design", label="Shared orchestrator never must reject non-result completion evidence", path="skills/shared/orchestrator-never.md", kind="contains", needle="Do not treat compatibility sentinels, launcher stdout, or wrapper stdout as completion evidence."),
    StructurePin(skill="design", label="Design Step 3 WAIT handling must be chunked and foreground-only", path="skills/design/SKILL.md", kind="contains", needle="Follow `${CLAUDE_PLUGIN_ROOT}/skills/shared/bgjob-wait.md` for Step 3 wait/`WAIT`/`DEAD`/`DONE`."),
    StructurePin(skill="design", label="Design Step 3 DONE handling must require BGJOB_RC=0", path="skills/design/SKILL.md", kind="contains", needle="Only after `BGJOB_STATUS=DONE` with `BGJOB_RC=0` may Step 3 parse the result env."),
    StructurePin(skill="design", label="Design Step 3 post-loop routing must reject non-result success signals", path="skills/design/SKILL.md", kind="contains", needle="Never continue from launcher stdout, `DONE` alone, `bgjob wait` shell exit 0, or wrapper stdout."),
    StructurePin(skill="design", label="Design Step 5c DONE handling must require BGJOB_RC=0", path="skills/design/SKILL.md", kind="contains", needle="Only after `DONE` with `BGJOB_RC=0` may Step 5c parse `$DESIGN_TMPDIR/bgjob/design-step5c.result.env`."),
    StructurePin(skill="design", label="Step 0 route fence must use bare launcher verb", path="skills/design/SKILL.md", kind="contains", needle='"$HOME/.cache/larch/sessions/design-run-$PPID.sh" step0-route --issue-number "${ISSUE_NUMBER:-}"'),
    StructurePin(skill="design", label="Step 1d.5 entry must use bare launcher verb", path="skills/design/SKILL.md", kind="contains", needle='"$HOME/.cache/larch/sessions/design-run-$PPID.sh" step1d5 --mode entry'),
    StructurePin(skill="design", label="Step 1e reentry must use bare launcher verb", path="skills/design/SKILL.md", kind="contains", needle='"$HOME/.cache/larch/sessions/design-run-$PPID.sh" step1e-reentry'),
    StructurePin(skill="design", label="Clarify must stay on .sh launcher branch", path="skills/design/SKILL.md", kind="contains", needle='"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-clarify.sh --phase fetch --issue "$ISSUE_NUMBER"'),
    StructurePin(skill="design", label="Step 2b drafter must stay on .sh launcher branch", path="skills/design/SKILL.md", kind="contains", needle='"$HOME/.cache/larch/sessions/design-run-$PPID.sh" step2b-drafter'),
    StructurePin(skill="design", label="launcher must dispatch ported verbs through scripts/larch.sh", path="crates/larch-core/src/session_env.rs", kind="contains", needle=r'exec \"$PLUGIN_ROOT/scripts/larch.sh\" design \"$script\" --session-env-path \"$SESSION_ENV_PATH\" --claude-pid \"$CLAUDE_PID\" \"$@\"'),
    StructurePin(skill="design", label="launcher must preserve .sh dispatch", path="crates/larch-core/src/session_env.rs", kind="contains", needle=r'exec \"$PLUGIN_ROOT/skills/design/scripts/$script\" --session-env-path \"$SESSION_ENV_PATH\" --claude-pid \"$CLAUDE_PID\" \"$@\"'),
    StructurePin(skill="design", label="launcher must reject unlisted non-.sh tokens", path="crates/larch-core/src/session_env.rs", kind="contains", needle="ERROR=unknown design wrapper verb"),
    StructurePin(skill="design", label="launcher must reject retired .sh token spellings", path="crates/larch-core/src/session_env.rs", kind="contains", needle="ERROR=ported design wrapper must use bare verb name, not .sh"),
    StructurePin(skill="design", label="launcher must map stage terminal basename to CLI", path="crates/larch-core/src/session_env.rs", kind="contains", needle=r'design stage-terminal-state \"$@\"'),
    StructurePin(skill="design", label="launcher must map failure report basename to CLI", path="crates/larch-core/src/session_env.rs", kind="contains", needle=r'design failure-report \"$@\"'),
    StructurePin(skill="design", label="launcher must map final summary basename to CLI", path="crates/larch-core/src/session_env.rs", kind="contains", needle=r'design step-final-summary --session-env-path \"$SESSION_ENV_PATH\" --claude-pid \"$CLAUDE_PID\" \"$@\"'),
    StructurePin(skill="design", label="Brainstorm collect docs must pin foreground Bash timeout", path="skills/design/references/brainstorm.md", kind="contains", needle="timeout: 1260000"),
    StructurePin(skill="design", label="Brainstorm collect must use launcher-owned collect verb", path="skills/design/references/brainstorm.md", kind="contains", needle='"$HOME/.cache/larch/sessions/design-run-$PPID.sh" step1d5 --mode collect --'),
    StructurePin(skill="design", label="Brainstorm docs must not call collect-results directly", path="skills/design/references/brainstorm.md", kind="absent", needle='python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" agent collect-results --timeout 1260'),
    StructurePin(skill="design", label="Brainstorm docs must drop standalone dirty-tree checkpoint section", path="skills/design/references/brainstorm.md", kind="absent", needle="## Post-collection dirty-tree checkpoint"),
    StructurePin(skill="design", label="Step 0 route must stop on PAUSE_OK before route continuation parsing", path="skills/design/SKILL.md", kind="contains", needle="If the fence output contains a whole-line `PAUSE_OK=true` row, treat Step 0b as a terminal pause-save boundary."),
    StructurePin(skill="design", label="Sub-step 6 must skip when folded route init completed", path="skills/design/SKILL.md", kind="contains", needle="Dominant proceed-path guard: when `ROUTE=proceed` and the `step0-route` fence stdout contains whole-line `INIT_STATUS=ok` and `RUN_PARAMS_PATH=`, skip Sub-step 6 entirely."),
    StructurePin(skill="design", label="Sub-step 6 must not run step0-init on dominant proceed path", path="skills/design/SKILL.md", kind="contains", needle="Do not rewrite `feature-description.txt`, do not invoke `design init-runparams`, and do not run `step0-init`; folded init inside `step0-route` already produced those artifacts."),
    StructurePin(skill="design", label="Step 1d.5 must document run-params authority before entry fence elision", path="skills/design/SKILL.md", kind="contains", needle="Before running the entry fence, read `$DESIGN_TMPDIR/run-params.json` and apply `_step1d5_brainstorm_requested` semantics: only `brainstorm_requested: true` in a well-formed object means brainstorm-on; missing, malformed, symlinked, or non-`true` values mean brainstorm-off."),
    StructurePin(skill="design", label="Step 1d.5 elision must not trust stale mental brainstorm binding", path="skills/design/SKILL.md", kind="contains", needle="This run-params authority overrides mental Step 0-pre `brainstorm_requested` on `resume@*` paths where Sub-step 5 flag binding was skipped."),
    StructurePin(skill="design", label="Step 1d.5 must stop on PAUSE_OK before action parsing", path="skills/design/SKILL.md", kind="contains", needle="If the entry fence output contains a whole-line `PAUSE_OK=true` row, treat Step 1d.5 as a terminal pause-save boundary."),
    StructurePin(skill="design", label="Step 1d.5 must fail closed on missing action", path="skills/design/SKILL.md", kind="contains", needle="If `STEP1D5_ACTION` is missing or empty, print `**⚠ 1d.5: missing STEP1D5_ACTION from entry fence; aborting /design**` and abort `/design`"),
    StructurePin(skill="design", label="Step 1d.5 must branch on skip directive", path="skills/design/SKILL.md", kind="contains", needle="If `STEP1D5_ACTION=skip`:"),
    StructurePin(skill="design", label="Step 1d.5 must preserve already-complete breadcrumb", path="skills/design/SKILL.md", kind="contains", needle="If `STEP1D5_SKIP_KIND=already-complete`: print `⏩ 1d.5: brainstorm: skipped (already complete; .brainstorm-done present)`."),
    StructurePin(skill="design", label="Step 1d.5 must branch on run directive", path="skills/design/SKILL.md", kind="contains", needle="If `STEP1D5_ACTION=run`: **MANDATORY: READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/brainstorm.md` completely."),
    StructurePin(skill="design", label="Step 1d.7 must stop on PAUSE_OK before skip-approve and outline work", path="skills/design/SKILL.md", kind="contains", needle="If the fence output contains a whole-line `PAUSE_OK=true` row, treat Step 1d.7 as a terminal pause-save boundary. Stop `/design` for operator resume; do not parse `SKIP_APPROVE_REQUESTED`; do not read or execute `references/design-outline.md`."),
    StructurePin(skill="design", label="Step 1d.7 must fail closed on pause failure or missing skip-approve directive", path="skills/design/SKILL.md", kind="contains", needle="If the fence output contains a whole-line `PAUSE_OK=false` row or `SKIP_APPROVE_REQUESTED` is missing or empty, print `**⚠ 1d.7: missing SKIP_APPROVE_REQUESTED from step1d7 fence; aborting /design**` and abort `/design`"),
    StructurePin(skill="design", label="Step 1d.5 must not describe completion fence as after skip", path="skills/design/SKILL.md", kind="absent", needle="Run exactly once after skip or finish"),
    StructurePin(skill="design", label="Design outline must block skip-approve auto-approval until invariant remediation clears", path="skills/design/references/design-outline.md", kind="contains", needle='When `skip_approve_requested=true`: run Output, run Presentation via `present-note --repo-root "$REPO_ROOT"`, assess invariants before guidelines, and if invariant violations remain, enter the remediation loop instead of auto-approving.'),
    StructurePin(skill="design", label="Design outline must pin bounded remediation counter contract", path="skills/design/references/design-outline.md", kind="contains", needle="Bound the invariant outline remediation loop with a counter persisted at `$DESIGN_TMPDIR/architectural-invariant-outline-remediation.count`, read on Step 1d.7 invariant entry, incremented per rewrite, mirroring Gate C. Hard-stop after the bound and record a warning."),
    StructurePin(skill="design", label="Gate C must pin per-kind tier-1/tier-2 counters", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle="Persist per-kind tier-1 and tier-2 counters under `$DESIGN_TMPDIR`: `architectural-<kind>-gatec-tier1.count` and `architectural-<kind>-gatec-tier2.count`"),
    StructurePin(skill="design", label="Gate C must atomically consume tier 2 before the main-agent action", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle="atomically mark the tier-2 round consumed (increment `architectural-<kind>-gatec-tier2.count` to 1) before the main agent begins an invariant repair, a guideline repair, or a guideline decline"),
    StructurePin(skill="design", label="Gate C tier-1 reviser must be MODE=plan-revise", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle="spawn exactly one `larch:claude-implementer` subagent with `MODE=plan-revise`, the plan path `$DESIGN_TMPDIR/plan.txt`, the relevant assessment path"),
    StructurePin(skill="design", label="Gate C must settle via --site gate-c and re-enter resume@4b on clean", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle="invoke `scripts/larch.sh design step35-settle --site gate-c` (or the launcher fence `design-step35-settle.sh --site gate-c`), require its `SETTLE_NEXT_ACTION` contract per `settle-rc-dispatch.md`, and re-enter `resume@4b` only on the clean `gate-c-return` action"),
    StructurePin(skill="design", label="Gate C must require a fresh assessor and forbid self-judgment", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle="spawns a fresh `larch:arch-assessor` on the revised plan; the reviser never judges its own revision"),
    StructurePin(skill="design", label="Gate C must cancel on an unresolved invariant violation", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle="Gate C does not approve: skip approval, Step 5, publication, and any waiver, and end through the existing cancellation outcome with nothing published"),
    StructurePin(skill="design", label="Gate C guideline decline must append one documented exception", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle="append exactly one active `Exception: <rationale> (author: main-agent, date: YYYY-MM-DD)` line"),
    StructurePin(skill="design", label="Gate C must persist a guideline decline with --allow-exception", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle='--assessment-file "$DESIGN_TMPDIR/architectural-guideline-assessment.input.sidecar" --allow-exception'),
    StructurePin(skill="design", label="Gate C must redact the exception disclosure and reject malformed lines", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle="Show the persisted exception through the standard secret-redaction path in the Gate C presentation and, under `--skip-approve`, the terminal summary; reject malformed, fenced-only, or duplicated active exception lines."),
    StructurePin(skill="design", label="Gate C must persist clean invariant assessments", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle='scripts/larch.sh architectural-invariants persist-design-assessment --repo-root "$REPO_ROOT" --design-tmpdir "$DESIGN_TMPDIR" --assessment clean'),
    StructurePin(skill="design", label="Gate C must persist remediated invariant sidecar assessments", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle='scripts/larch.sh architectural-invariants persist-design-assessment --repo-root "$REPO_ROOT" --design-tmpdir "$DESIGN_TMPDIR" --assessment-file "$DESIGN_TMPDIR/architectural-invariant-assessment.input.sidecar"'),
    StructurePin(skill="design", label="Gate C must document no-flags invariant stale-artifact removal", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle='scripts/larch.sh architectural-invariants persist-design-assessment --repo-root "$REPO_ROOT" --design-tmpdir "$DESIGN_TMPDIR"` with no assessment flags so stale artifacts are removed.'),
    StructurePin(skill="design", label="Gate C must pin clean invariant persist dispatch condition", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle="**Clean**: only when invariants are `present` with parsed non-empty content and no violation assessment was required (no `INVARIANTS_VIOLATION_ASSESSMENT_REQUIRED=true` path and no remediated-violations sidecar)."),
    StructurePin(skill="design", label="Gate C must pin remediated invariant persist dispatch condition", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle="**Remediated-violations**: when violations were identified and the fix ladder produced a clean plan."),
    StructurePin(skill="design", label="Gate C must pin no-assessment invariant persist dispatch condition", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle="**Absent, invalid, or present-but-empty**: when the `read` command does not report `ARCHITECTURAL_INVARIANTS_STATUS=present` or emits no parsed `I-*` entries."),
    StructurePin(skill="design", label="Gate C must pin invariant violation assessment flow", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle="If invariant present-note emits `INVARIANTS_VIOLATION_ASSESSMENT_REQUIRED=true`, consume the subagent's invariants verdict for the complete on-disk `$DESIGN_TMPDIR/plan.txt`, not the chat preview."),
    StructurePin(skill="design", label="Gate C assessment authoring must run in the arch-assessor subagent", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle="spawn exactly one Agent-tool subagent with `subagent_type` `larch:arch-assessor` covering the required kind(s) in canonical order (invariants, then guidelines)"),
    StructurePin(skill="design", label="Gate C must forbid main-agent assessment authoring", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle="The main agent authors no architectural assessment prose at Gate C."),
    StructurePin(skill="design", label="Gate C must respawn once then fail closed on unparseable assessor", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle="An unparseable final message gets exactly one fresh `larch:arch-assessor` respawn"),
    StructurePin(skill="design", label="Gate C must keep distinct invariant persist failure message", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle="**⚠ 4b: architectural-invariant assessment persistence failed**"),
    StructurePin(skill="design", label="Gate C must fail closed for invariant and guideline persistence", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle="**Fail-closed persistence contract**: every invariant and guideline `persist-design-assessment` invocation must exit `0` before Gate C continues"),
    StructurePin(skill="design", label="Step 5c docs must pin invariant-before-guideline refusal order", path="skills/design/references/finalize-step5.md", kind="contains", needle="Missing invariant assessment is evaluated and surfaced before missing guideline assessment when both artifacts are missing."),
    StructurePin(skill="design", label="Step 5c docs must pin invariant return path", path="skills/design/references/finalize-step5.md", kind="contains", needle='Return: Step 4b (`resume@4b`) → `scripts/larch.sh architectural-invariants present-note --repo-root "$REPO_ROOT"` → `scripts/larch.sh architectural-invariants persist-design-assessment --repo-root "$REPO_ROOT" --design-tmpdir "$DESIGN_TMPDIR"` (clean, sidecar, or no-flags branch as appropriate) → `design-step5c.sh --fresh-attempt`'),
    StructurePin(skill="design", label="Step 5c docs must pin invariant refusal warning", path="skills/design/references/finalize-step5.md", kind="contains", needle="**⚠ 5c: publish refused: missing architectural-invariant-assessment.md; return to Gate C to persist the architectural-invariant assessment before publish.**"),
    StructurePin(skill="design", label="SKILL must document missing invariant assessment Step 5c special case", path="skills/design/SKILL.md", kind="contains", needle="**Step 5c missing-invariant-assessment.** With `--site design Step 5c` and `PUBLISH_REFUSE_REASON=missing-invariant-assessment`"),
    StructurePin(skill="design", label="SKILL must route Step 5c invariant-violation refusal to Gate C", path="skills/design/SKILL.md", kind="contains", needle="**Step 5c invariant-violation.** With `--site design Step 5c` and `PUBLISH_REFUSE_REASON=invariant-violation`"),
    StructurePin(skill="design", label="SKILL must route Step 5c invalid-guideline-deviation refusal to Gate C", path="skills/design/SKILL.md", kind="contains", needle="**Step 5c invalid-guideline-deviation.** With `--site design Step 5c` and `PUBLISH_REFUSE_REASON=invalid-guideline-deviation`"),
    StructurePin(skill="design", label="Step 5c docs must route invariant-violation refusal to Gate C", path="skills/design/references/finalize-step5.md", kind="contains", needle="`PUBLISH_REFUSE_REASON=invariant-violation` → publish precondition"),
    StructurePin(skill="design", label="Step 5c docs must route invalid-guideline-deviation refusal to Gate C", path="skills/design/references/finalize-step5.md", kind="contains", needle="`PUBLISH_REFUSE_REASON=invalid-guideline-deviation` → publish precondition"),
    StructurePin(skill="design", label="Make targets must route retired Python harnesses to Rust parity", path="Makefile", kind="contains", needle="cargo test --locked --package larch-cli --test design_step1_migrated_parity"),
    StructurePin(skill="design", label="cli registry must drop plan validator-autofix after Rust cutover", path="python/larch/cli.py", kind="absent", needle='("plan", "validator-autofix")'),
    StructurePin(skill="design", label="launcher must reject the retired step2b .sh names", path="crates/larch-core/src/session_env.rs", kind="contains", needle="design-step2b-drafter.sh|design-step2b-postplan.sh)"),
    StructurePin(skill="design", label="launcher must route step2b/step3b bare verbs to scripts/larch.sh", path="crates/larch-core/src/session_env.rs", kind="contains", needle="step2b-drafter|step2b-postplan|step3b-entry)"),
    StructurePin(skill="design", label="launcher must map design-step2b5.sh", path="crates/larch-core/src/session_env.rs", kind="contains", needle="design-step2b5.sh)"),
    StructurePin(skill="design", label="launcher must forward step2b5 to scripts/larch.sh", path="crates/larch-core/src/session_env.rs", kind="contains", needle=r'scripts/larch.sh\" design step2b5 --session-env-path \"$SESSION_ENV_PATH\" --claude-pid \"$CLAUDE_PID\" \"$@\"'),
    StructurePin(skill="design", label="launcher must map design-step-validator-autofix.sh", path="crates/larch-core/src/session_env.rs", kind="contains", needle="design-step-validator-autofix.sh)"),
    StructurePin(skill="design", label="launcher must forward validator-autofix to scripts/larch.sh", path="crates/larch-core/src/session_env.rs", kind="contains", needle=r'plan validator-autofix --session-env-path \"$SESSION_ENV_PATH\" --claude-pid \"$CLAUDE_PID\" \"$@\"'),
    StructurePin(skill="design", label="SKILL.md must route Step 2b through DRAFTER_NEXT_ACTION", path="skills/design/SKILL.md", kind="contains", needle="On exit 0 only, parse the final trusted `DRAFTER_NEXT_ACTION=` row after the final whole-line `STEP2B_DRAFTER_WRAPPER_ROWS_BEGIN=1` delimiter."),
    StructurePin(skill="design", label="SKILL.md must abort on non-zero drafter fence before parsing action", path="skills/design/SKILL.md", kind="contains", needle="If the `step2b-drafter` fence exits non-zero, abort loudly with captured stdout/stderr and do not parse `DRAFTER_NEXT_ACTION`, enter inline fallback, run fail-safe, or continue to Step 3."),
    StructurePin(skill="design", label="SKILL.md must scope failsafe-missing-rows to zero exit only", path="skills/design/SKILL.md", kind="contains", needle="`failsafe-missing-rows`: load `references/step2b-drafter-failsafe.md` and run the retained terminal postplan path only; this token is valid only after exit 0 without a trusted postplan action row."),
    StructurePin(skill="design", label="SKILL.md must not parse drafter outcomes from retired rows", path="skills/design/SKILL.md", kind="contains", needle="Do not reconstruct drafter routing from `POSTPLAN_RC`, `POSTPLAN_STATUS`, `DRAFTER_STATUS`, `PAUSE_OK`, preview text, or `.step2b-postplan-inline-retry-pending`."),
    StructurePin(skill="design", label="SKILL.md inline retry must not re-read fallback_used after apply", path="skills/design/SKILL.md", kind="contains", needle="Do not describe or perform a `fallback_used` disk re-read after postplan apply."),
    StructurePin(skill="design", label="SKILL.md resume@2a must route directly to Step 2b drafter", path="skills/design/SKILL.md", kind="contains", needle="When `ROUTE=resume@2a` or `RESUME_STEP=2a`, jump directly to the Step 2b drafter breadcrumb (`> **🔶 /design 2b: full plan**`) and `step2b-drafter`; folded sentinel prep runs inside that wrapper, so do not expect or invoke a standalone Step 2a fence."),
    StructurePin(skill="design", label="design anti-halt must cite shared anti-halt anchor", path="skills/design/SKILL.md", kind="contains", needle="${CLAUDE_PLUGIN_ROOT}/skills/shared/subskill-invocation.md#anti-halt"),
    StructurePin(skill="design", label="design anti-halt must retain visible-output continuation trigger", path="skills/design/SKILL.md", kind="contains", needle="after every visible output (plans, voting tallies, skip breadcrumbs), IMMEDIATELY continue"),
    StructurePin(skill="design", label="design anti-halt must retain operative no-recap trigger", path="skills/design/SKILL.md", kind="contains", needle="After Step 5c `scripts/larch.sh design step5c` returns with `_publish_rc` 0, 1, or 3, or after any cancellation outcome's Final summary block has written a non-empty summary file"),
    StructurePin(skill="design", label="design anti-halt must retain no-recap and no-cost paraphrase ban", path="skills/design/SKILL.md", kind="contains", needle='NEVER write a free-form natural-language recap summary: no "Design complete." line, no artifact bullet list, no parenthetical cost paraphrase such as `~$10.46`'),
    StructurePin(skill="design", label="design anti-halt must retain render-exit carve-out", path="skills/design/SKILL.md", kind="contains", needle="**Not** gated on `scripts/larch.sh design render-final-summary` exit 0"),
    StructurePin(skill="design", label="Step 5d must retain no-recap terminal ordering token", path="skills/design/SKILL.md", kind="contains", needle="No free-form recap may appear between or after terminal emission."),
    StructurePin(skill="design", label="design final-summary cancellation source must remain named", path="skills/design/SKILL.md", kind="contains", needle="design-step-final-summary.sh"),
    StructurePin(skill="design", label="Final summary block must pin Read/cache before deferred emit", path="skills/design/SKILL.md", kind="contains", needle="Read/cache happens before cleanup; plain-chat emit is deferred until after required operator/cancellation/partition lines, WARN replay, the Step 5 footer, and Step 6 cleanup when applicable."),
    StructurePin(skill="design", label="Step 5c must defer terminal summary until after cleanup or warning", path="skills/design/SKILL.md", kind="contains", needle="Apply terminal emit **after** the plan-write failure warning or success footer decisions below, and after Step 6 cleanup when cleanup runs."),
    StructurePin(skill="design", label="Step 6 must precede terminal summary emit", path="skills/design/SKILL.md", kind="contains", needle="After Step 6 completes or is intentionally skipped, emit the cached final-summary body (plus cached sidecars when allowed) as the final assistant text."),
    StructurePin(skill="design", label="already-planned cancel must put operator line before terminal summary", path="skills/design/SKILL.md", kind="contains", needle="run the Final summary block through its Read/cache step, print `**ℹ /design cancelled by operator.**`, emit the cached summary as terminal plain chat"),
    StructurePin(skill="design", label="design Step 5c final-summary source must remain named", path="skills/design/SKILL.md", kind="contains", needle="design-step5c.sh"),
    StructurePin(skill="design", label="Step 3 wrapper must delegate to adapter", path="skills/design/scripts/design-step3-review.sh", kind="contains", needle='bgjob adapt "${_adapt_args[@]}"'),
    StructurePin(skill="design", label="Step 3 wrapper must resolve trusted session env", path="skills/design/scripts/design-step3-review.sh", kind="contains", needle="--resolve-session-env --session-env-path"),
    StructurePin(skill="design", label="Step 3 wrapper must replace completed resume", path="skills/design/scripts/design-step3-review.sh", kind="contains", needle="--replace-completed-result"),
    StructurePin(skill="design", label="Step 3 wrapper must not use direct bgjob start", path="skills/design/scripts/design-step3-review.sh", kind="absent", needle="bgjob start"),
    StructurePin(skill="design", label="Step 4 tail wrapper must delegate to adapter", path="skills/design/scripts/design-step3b-tail.sh", kind="contains", needle='bgjob adapt "${_adapt_args[@]}"'),
    StructurePin(skill="design", label="Step 4 tail wrapper must resolve trusted session env", path="skills/design/scripts/design-step3b-tail.sh", kind="contains", needle="--resolve-session-env --session-env-path"),
    StructurePin(skill="design", label="Step 4 tail wrapper must not use direct bgjob start", path="skills/design/scripts/design-step3b-tail.sh", kind="absent", needle="bgjob start"),
    StructurePin(skill="design", label="Step 5c wrapper must delegate to adapter", path="skills/design/scripts/design-step5c.sh", kind="contains", needle='bgjob adapt "${_adapt_args[@]}"'),
    StructurePin(skill="design", label="Step 5c wrapper must resolve trusted session env", path="skills/design/scripts/design-step5c.sh", kind="contains", needle="--resolve-session-env --session-env-path"),
    StructurePin(skill="design", label="Step 5c wrapper must support explicit replacement", path="skills/design/scripts/design-step5c.sh", kind="contains", needle="--replace-completed-result"),
    StructurePin(skill="design", label="Step 5c wrapper must not use direct bgjob start", path="skills/design/scripts/design-step5c.sh", kind="absent", needle="bgjob start"),
    StructurePin(skill="design", label="design title cancellation must not bypass the final summary terminalizer", path="skills/design/SKILL.md", kind="absent", needle="follow the file-only profile in `${CLAUDE_PLUGIN_ROOT}/skills/shared/final-summary-emit.md` only on the `cancel-title-filter` / `cancel-reentry-guard` routes"),
    StructurePin(skill="design", label="design SKILL must not retain marker-body Binding restatement", path="skills/design/SKILL.md", kind="absent", needle="Binding: markers `LARCH_FINAL_SUMMARY_BEGIN` / `LARCH_FINAL_SUMMARY_END`"),
    StructurePin(skill="design", label="anti-halt chain must include Step 5b.5 before Step 5c", path="skills/design/SKILL.md", kind="contains", needle="1c→1d→1d.5→1d.7→2a(folded)→2b→2b.5→3→3.5→3b→4→4b→5→5b→5b.5→5c.1→5c.5→5c.7→5c.8→6"),
    StructurePin(skill="design", label="Step 3b must use finalize mode", path="skills/design/SKILL.md", kind="contains", needle="step3b-entry --mode finalize"),
    StructurePin(skill="design", label="Step 5b.5 must use diagram mode", path="skills/design/SKILL.md", kind="contains", needle="step3b-entry --mode diagram"),
    StructurePin(skill="design", label="Step 3 entry must document first-time empty reentry flag", path="skills/design/SKILL.md", kind="contains", needle='STEP3_REENTRY_FLAG=""'),
    StructurePin(skill="design", label="Step 3 entry must document caller-owned reentry flag", path="skills/design/SKILL.md", kind="contains", needle='STEP3_REENTRY_FLAG="--reentry"'),
    StructurePin(skill="design", label="Step 3 entry must use one parameterized launcher fence", path="skills/design/SKILL.md", kind="contains", needle="design-step3-entry.sh ${STEP3_REENTRY_FLAG}"),
    StructurePin(skill="design", label="SKILL must not retain standalone Step 3 reentry launcher fence", path="skills/design/SKILL.md", kind="absent", needle='"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step3-entry.sh --reentry'),
    StructurePin(skill="design", label="External reviewer setup must retain prompt-side plan.txt check", path="skills/design/SKILL.md", kind="contains", needle="Before launching external reviewers, verify the implementation plan exists at `$DESIGN_TMPDIR/plan.txt`"),
    StructurePin(skill="design", label="External reviewer setup must delegate focus areas", path="skills/design/SKILL.md", kind="contains", needle="Reviewer focus areas are delegated to `plan-review-runtime.md` and the rendered reviewer prompts."),
    StructurePin(skill="design", label="Step 4 must not self-compute debate may-run flag", path="skills/design/SKILL.md", kind="absent", needle="_step4_debate_may_run"),
    StructurePin(skill="design", label="Step 4 must not run prompt-side dialectic probe", path="skills/design/SKILL.md", kind="absent", needle='dialectic-gatec --design-tmpdir "$DESIGN_TMPDIR" --probe-only'),
    StructurePin(skill="design", label="Step 4 must route only on STEP4_MODE", path="skills/design/SKILL.md", kind="contains", needle="Step 4 routing authority is `STEP4_MODE` only."),
    StructurePin(skill="design", label="Step 4 must bind STEP4_MODE from finalize stdout", path="skills/design/SKILL.md", kind="contains", needle="bind `STEP4_MODE` from a whole-line `STEP4_MODE=foreground|background` row in the entry stdout"),
    StructurePin(skill="design", label="Step 4 must support STEP4_MODE sidecar fallback", path="skills/design/SKILL.md", kind="contains", needle="read `$DESIGN_TMPDIR/.step4-mode.env` and bind the same grammar from that sidecar"),
    StructurePin(skill="design", label="Step 4 must document foreground tail route", path="skills/design/SKILL.md", kind="contains", needle="If `STEP4_MODE=foreground`, run the tail bgjob starter."),
    StructurePin(skill="design", label="Step 4 must document background bgjob route", path="skills/design/SKILL.md", kind="contains", needle="If `STEP4_MODE=background`, run the same tail bgjob starter."),
    StructurePin(skill="design", label="Step 4 must fail closed on invalid STEP4_MODE", path="skills/design/SKILL.md", kind="contains", needle="Stop for repair if `STEP4_MODE` is absent or not `foreground|background`."),
    StructurePin(skill="design", label="Step 4 must name bgjob tail result env", path="skills/design/SKILL.md", kind="contains", needle="bgjob/design-step4-tail.result.env"),
    StructurePin(skill="design", label="Step 4b must parse skip approve from bgjob result env", path="skills/design/SKILL.md", kind="contains", needle="SKIP_APPROVE_REQUESTED_GATEC=true|false` from `$DESIGN_TMPDIR/bgjob/design-step4-tail.result.env`"),
    StructurePin(skill="design", label="SKILL must not retain inline Gate B optional trailer block", path="skills/design/SKILL.md", kind="absent", needle="**Optional trailer guard (Gate B post-apply)**"),
    StructurePin(skill="design", label="SKILL must not retain inline Gate B snapshot-trailers restatement", path="skills/design/SKILL.md", kind="absent", needle="Before any reviewer-finding `plan.txt` replacement, run"),
    StructurePin(skill="design", label="SKILL must not retain inline Gate B resume idempotency block", path="skills/design/SKILL.md", kind="absent", needle="**Gate B resume idempotency**"),
    StructurePin(skill="design", label="SKILL must not retain old Gate B idempotency probe wording", path="skills/design/SKILL.md", kind="absent", needle="do not probe the apply-ready marker"),
    StructurePin(skill="design", label="SKILL must point Gate B idempotency to approval-gates", path="skills/design/SKILL.md", kind="contains", needle="Apply the `approval-gates-gate-b.md` §Gate B **Resume idempotency guard** before executing Gate B."),
    StructurePin(skill="design", label="SKILL must keep invariant knowledge ahead of guidelines", path="skills/design/SKILL.md", kind="contains", needle="Consult `ARCHITECTURAL_INVARIANTS.md` before `ARCHITECTURAL_GUIDELINES.md`"),
    StructurePin(skill="design", label="SKILL must read invariants before guidelines", path="skills/design/SKILL.md", kind="contains", needle="Call `scripts/larch.sh architectural-invariants read` before `scripts/larch.sh architectural-guidelines read`."),
    StructurePin(skill="design", label="SKILL must fold invariant constraints first", path="skills/design/SKILL.md", kind="contains", needle="If invariants are `present` with parsed content, fold hard constraints from command output first;"),
    StructurePin(skill="design", label="Step 3b prose must document finalize ordering", path="skills/design/SKILL.md", kind="contains", needle="runs FINALIZE, runs probe-only dialectic eligibility, emits and persists `STEP4_MODE`, then writes `.completed/step-3b`"),
    StructurePin(skill="design", label="Step 2b.5 direct-entry must be action-row only", path="skills/design/SKILL.md", kind="contains", needle="Bind `STEP2B5_NEXT_ACTION` from `.design-postplan-emit-result.env` and branch on that action key."),
    StructurePin(skill="design", label="Step 2b.5 direct-entry must not mention Gate A fallback rc 12", path="skills/design/SKILL.md", kind="absent", needle="Gate A / discussion-round2 fallback rc `12`"),
    StructurePin(skill="design", label="Step 2b.5 direct-entry must not mention Gate B fallback rc 12", path="skills/design/SKILL.md", kind="absent", needle="Gate B fallback rc `12`"),
    StructurePin(skill="design", label="Gate-B-bypass row must retain cap-reached stale-findings rationale", path="skills/design/SKILL.md", kind="contains", needle="When `LOOP_STATUS=cap-reached` or `TALLY_PLAN_REVIEW_STATUS=skipped-cap-reached`, do not enter Gate B because stale accepted findings from an earlier round would re-surface."),
    StructurePin(skill="design", label="SKILL must not retain standalone cap-reached bypass paragraph", path="skills/design/SKILL.md", kind="absent", needle="If `NEXT_ACTION=step3b-bypass` with `LOOP_STATUS=cap-reached`"),
    StructurePin(skill="design", label="SKILL must not retain standalone degraded bypass paragraph", path="skills/design/SKILL.md", kind="absent", needle="If `NEXT_ACTION=step3b-bypass` with `LOOP_STATUS=tally-error`"),
    StructurePin(skill="design", label="SKILL must not retain duplicated Gate-B-bypass restatement", path="skills/design/SKILL.md", kind="absent", needle="Before every Gate-B-bypass jump, run the bypass helper so pause/resume lands at Step 3b"),
    StructurePin(skill="design", label="SKILL must not retain duplicated Gate-B-bypass launcher header", path="skills/design/SKILL.md", kind="absent", needle="Before every Gate-B-bypass jump to Step 3b, run:"),
    StructurePin(skill="design", label="launcher must route the Step 3b entry verb", path="crates/larch-core/src/session_env.rs", kind="contains", needle="step3b-entry)"),
    StructurePin(skill="design", label="Step 5b.5 generation failure must use bounded warning logging", path="skills/design/references/finalize-step5.md", kind="contains", needle="Log only a bounded generation warning through `design_diagram_log.write_bounded_diagram_failure_log`."),
    StructurePin(skill="design", label="SKILL must not retain diagram warning logging body", path="skills/design/SKILL.md", kind="absent", needle="design_diagram_log.write_bounded_diagram_failure_log"),
    StructurePin(skill="design", label="Step 5b.5 warning authority must be limited to generation failures", path="skills/design/references/finalize-step5.md", kind="contains", needle="Step 5b.5 must not warn or log sanitizer rejection."),
    StructurePin(skill="design", label="Step 5c must own diagram sanitize before publish", path="skills/design/references/finalize-step5.md", kind="contains", needle="Step 5c alone sanitizes the unchanged candidate, promotes or skips it, logs sanitizer rejection, and writes Step-5c-owned artifacts."),
    StructurePin(skill="design", label="SKILL must scope quiet authoring to the required diagram branch", path="skills/design/SKILL.md", kind="contains", needle="If true, quietly write only `architecture-diagram.candidate.md` per `finalize-step5.md`:"),
    StructurePin(skill="design", label="SKILL must distinguish harness-rendered tool lines from Claude-authored prose", path="skills/design/SKILL.md", kind="contains", needle="Harness tool lines, including `Write(...)`, `Wrote N lines`, and command counts, are outside this contract."),
    StructurePin(skill="design", label="finalize-step5 must prohibit Step 5b.5 authoring narration", path="skills/design/references/finalize-step5.md", kind="contains", needle="Emit no Claude-authored composition, safe-content reading, content/write/validation, success, or transition narration, and no diagram body."),
    StructurePin(skill="design", label="finalize-step5 must preserve the anti-halt blockquote and forbid sanitizer pre-checks", path="skills/design/references/finalize-step5.md", kind="contains", needle="Continue with `> **Continue to Step 5c IMMEDIATELY.**` without a pre-check or free-form recap."),
    StructurePin(skill="design", label="SKILL must preserve the Step 5c anti-halt blockquote without a free-form recap", path="skills/design/SKILL.md", kind="contains", needle="> **Continue to Step 5c IMMEDIATELY.** No sanitizer pre-check or free-form recap."),
    StructurePin(skill="design", label="SKILL must reserve sanitizer rejection logging for Step 5c", path="skills/design/SKILL.md", kind="contains", needle="Step 5c owns them and sanitizer-rejection logging."),
    StructurePin(skill="design", label="SKILL must forbid every pre-Step-5c sanitizer path", path="skills/design/SKILL.md", kind="contains", needle="Do not run `python3 python/cli.py mermaid sanitize` or another sanitizer"),
    StructurePin(skill="design", label="SKILL must forbid Step 5b.5 publish artifacts and candidate mutation", path="skills/design/SKILL.md", kind="contains", needle="promote/reject, move/delete the candidate; or write `.completed/step-5b.5`, `architecture-diagram.md`, or `architecture-diagram.skipped`"),
    StructurePin(skill="design", label="finalize-step5 must forbid every pre-Step-5c sanitizer path", path="skills/design/references/finalize-step5.md", kind="contains", needle="Do not invoke `python3 python/cli.py mermaid sanitize` or another sanitizer"),
    StructurePin(skill="design", label="finalize-step5 must forbid Step 5b.5 publish artifacts and candidate mutation", path="skills/design/references/finalize-step5.md", kind="contains", needle="promote/reject, move/delete the candidate; or write `.completed/step-5b.5`, `architecture-diagram.md`, or `architecture-diagram.skipped`"),
    StructurePin(skill="design", label="SKILL verbosity must not authorize architecture diagram chat emission", path="skills/design/SKILL.md", kind="contains", needle="architecture diagram content is issue-only via `larch:diagrams`"),
    StructurePin(skill="design", label="Step 5b must continue to Step 5b.5 before Step 5c", path="skills/design/SKILL.md", kind="contains", needle="Continue to Step 5b.5 IMMEDIATELY"),
    StructurePin(skill="design", label="finalize-step5 must require one Step 5 readability load", path="skills/design/references/finalize-step5.md", kind="contains", needle="**MANDATORY: READ ENTIRE FILE before Step 5 diagram, final plan, summary, or Gate C prose composition: `${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md`.**"),
    StructurePin(skill="design", label="SKILL must restore the Step 2b readability anchor", path="skills/design/SKILL.md", kind="contains", needle="**MANDATORY: READ ENTIRE FILE before drafting the implementation plan: `${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md`.**"),
    StructurePin(skill="design", label="Step 5b prose must branch on NEXT_ACTION", path="skills/design/SKILL.md", kind="contains", needle="Parse `NEXT_ACTION=` from `$DESIGN_TMPDIR/oos-filing-prepare.env`"),
    StructurePin(skill="design", label="Step 5b must special-case unknown-oos-status on non-zero prepare rc", path="skills/design/SKILL.md", kind="contains", needle="`unknown-oos-status`"),
    StructurePin(skill="design", label="Step 5b must stop for repair on unknown OOS status", path="skills/design/SKILL.md", kind="contains", needle="stop for repair"),
    StructurePin(skill="design", label="oos step5b dispatch must document unknown-oos-status repair stop", path="skills/design/references/oos-step5b-dispatch.md", kind="contains", needle="unknown-oos-status"),
    StructurePin(skill="design", label="skip-already-filed must retain stdout-non-empty annotate guard", path="skills/design/references/finalize-step5.md", kind="contains", needle="call `design-step5b-annotate.sh` only when `$DESIGN_TMPDIR/oos-issue.stdout.txt` exists and is non-empty"),
    StructurePin(skill="design", label="SKILL must not retain skip-already annotate guard body", path="skills/design/SKILL.md", kind="absent", needle="call `design-step5b-annotate.sh` only when"),
    StructurePin(skill="design", label="skip-already-filed must append WARN rows as warnings", path="skills/design/references/finalize-step5.md", kind="contains", needle="tool `scripts/larch.sh design file-oos-prepare`, category `Warnings`, exit code 0"),
    StructurePin(skill="design", label="SKILL must not retain skip-already WARN body", path="skills/design/SKILL.md", kind="absent", needle="tool `scripts/larch.sh design file-oos-prepare`, category `Warnings`, exit code 0"),
    StructurePin(skill="design", label="skip-already-filed without annotate must rely on prepare completion marker", path="skills/design/references/finalize-step5.md", kind="contains", needle="Prepare already wrote `.completed/step-5b` for `skip-already-filed-sentinel` without annotate."),
    StructurePin(skill="design", label="SKILL must not retain skip-already completion body", path="skills/design/SKILL.md", kind="absent", needle="skip-already-filed-sentinel` without annotate."),
    StructurePin(skill="design", label="Step 5b must not mandatory-read oos-step5b dispatch fallback", path="skills/design/SKILL.md", kind="absent", needle="skills/design/references/oos-step5b-dispatch.md"),
    StructurePin(skill="design", label="Step 5b must fail closed without prompt-side fallback derivation", path="skills/design/SKILL.md", kind="contains", needle="When `NEXT_ACTION` is missing, unknown, or `unknown-oos-status`, stop for repair. The prepare wrapper already checks `FILE_DESIGN_OOS_STATUS=` agreement."),
    StructurePin(skill="design", label="oos step5b dispatch must name current NEXT_ACTION contract", path="skills/design/references/oos-step5b-dispatch.md", kind="contains", needle="Current `scripts/larch.sh design step5b-prepare` must emit a whole-line `NEXT_ACTION=...` row in `oos-filing-prepare.env`."),
    StructurePin(skill="design", label="oos step5b dispatch must reject prompt-side fallback derivation", path="skills/design/references/oos-step5b-dispatch.md", kind="contains", needle="Do not derive a prompt-side route from `FILE_DESIGN_OOS_STATUS`."),
    StructurePin(skill="design", label="oos step5b dispatch must keep short legacy mapping note", path="skills/design/references/oos-step5b-dispatch.md", kind="contains", needle="The historical mapping was: `ready` to `file-issues`; `skip-sentinel`, `skip-already-filed-sentinel`, `skip-no-items`, and `skip-all-security` to `skip-pipeline`; every other status to `unknown-oos-status`."),
    StructurePin(skill="design", label="oos step5b dispatch must not own a live fallback table", path="skills/design/references/oos-step5b-dispatch.md", kind="absent", needle="## Fallback: branch on FILE_DESIGN_OOS_STATUS"),
    StructurePin(skill="design", label="finalize-step5 must own prepare-failed-continue branch", path="skills/design/references/finalize-step5.md", kind="contains", needle="STEP5B_STATUS=prepare-failed-continue"),
    StructurePin(skill="design", label="SKILL must not retain prepare-failed-continue body", path="skills/design/SKILL.md", kind="absent", needle="STEP5B_STATUS=prepare-failed-continue"),
    StructurePin(skill="design", label="finalize-step5 must own file-issues deps detail", path="skills/design/references/finalize-step5.md", kind="contains", needle="FILE_DESIGN_OOS_DEPS_AVAILABLE=true"),
    StructurePin(skill="design", label="SKILL must not retain file-issues deps body", path="skills/design/SKILL.md", kind="absent", needle="FILE_DESIGN_OOS_DEPS_AVAILABLE=true"),
    StructurePin(skill="design", label="file-issues must not ask confirmation before filing", path="skills/design/references/finalize-step5.md", kind="contains", needle="Accepted non-security OOS plus Gate C approval authorizes `/larch:issue`; no confirmation or `AskUserQuestion`, including retry."),
    StructurePin(skill="design", label="Step 5b file-issues skeleton must forbid confirmation prompt", path="skills/design/SKILL.md", kind="contains", needle="**`file-issues`**: invoke `/larch:issue` and annotate per `finalize-step5.md`; no confirmation."),
    StructurePin(skill="design", label="finalize-step5 must own manual OOS recovery", path="skills/design/references/finalize-step5.md", kind="contains", needle="Manual OOS recovery when annotate ran before"),
    StructurePin(skill="design", label="manual OOS recovery must not ask confirmation before filing", path="skills/design/references/finalize-step5.md", kind="contains", needle="Manual recovery files accepted non-security OOS; no confirmation/`AskUserQuestion`."),
    StructurePin(skill="design", label="SKILL must not retain manual OOS recovery", path="skills/design/SKILL.md", kind="absent", needle="Manual OOS recovery when annotate ran before"),
    StructurePin(skill="design", label="finalize-step5 must own Step 5c composition detail", path="skills/design/references/finalize-step5.md", kind="contains", needle="Compose `$DESIGN_TMPDIR/composed-plan.md`"),
    StructurePin(skill="design", label="SKILL must not retain Step 5c composition detail", path="skills/design/SKILL.md", kind="absent", needle="Compose `$DESIGN_TMPDIR/composed-plan.md`"),
    StructurePin(skill="design", label="finalize-step5 must own driver WARN replay detail", path="skills/design/references/finalize-step5.md", kind="contains", needle="Driver WARN replay (top chat)"),
    StructurePin(skill="design", label="SKILL must point normal publish rc handling to green finalize", path="skills/design/SKILL.md", kind="contains", needle="Follow `finalize-step5.md` for stdout fallback, validator-defect routing, and normal `PLAN_WRITE_OK` branches."),
    StructurePin(skill="design", label="SKILL must point abort handling to failure slice", path="skills/design/SKILL.md", kind="contains", needle="finalize-step5-failures.md` before staging the failed outcome"),
    StructurePin(skill="design", label="finalize-step5 must own rc2 and unexpected non-zero abort guidance", path="skills/design/references/finalize-step5-failures.md", kind="contains", needle="When `_publish_rc=2` or an unexpected non-zero value outside `{0,1,3,4}` appears, abort after best-effort `scripts/larch.sh design stage-terminal-state` staging as `failed-publish-tail`."),
    StructurePin(skill="design", label="finalize-step5 must own rc5 abort guidance", path="skills/design/references/finalize-step5-failures.md", kind="contains", needle="This includes `_publish_rc=5`."),
    StructurePin(skill="design", label="finalize-step5 must own rc3 stdout fallback guidance", path="skills/design/references/finalize-step5.md", kind="contains", needle="When `_publish_rc=3`, the publish tail may have completed but `.design-publish-result.env` could not be written."),
    StructurePin(skill="design", label="SKILL must not retain publish rc abort wall", path="skills/design/SKILL.md", kind="absent", needle="_publish_rc`=2 and unexpected non-zero values outside `{0,1,3,4}`"),
    StructurePin(skill="design", label="clarify fetch failure must load failure slice before staging", path="skills/design/SKILL.md", kind="contains", needle="finalize-step5-failures.md` immediately before staging `failed-clarify` or exporting `SUMMARY_OUTCOME=failed-clarify`"),
    StructurePin(skill="design", label="clarify plan-write failure must load failure slice before staging", path="skills/design/SKILL.md", kind="contains", needle="finalize-step5-failures.md` immediately before staging or exporting `SUMMARY_OUTCOME=failed-plan-write`"),
    StructurePin(skill="design", label="finalize-step5 must own Step 5d warning replay detail", path="skills/design/references/finalize-step5.md", kind="contains", needle="Step 5d warning replay and footer"),
    StructurePin(skill="design", label="Step 2b anti-halt must not promise pre-approval diagram generation", path="skills/design/SKILL.md", kind="contains", needle="architecture diagram work runs only at Step 5b.5 after Gate C approval"),
    StructurePin(skill="design", label="Step 5c sanitize fail-closed paths must touch skipped marker", path="crates/larch-cli/src/design_publish_commands.rs", kind="contains", needle="architecture-diagram.skipped"),
    StructurePin(skill="design", label="Step 5c sanitizer warning site must name Step 5b.5", path="crates/larch-cli/src/design_publish_commands.rs", kind="contains", needle="design Step 5b.5"),
    StructurePin(skill="design", label="Step 5c sanitizer must not emit chat diagram markers", path="crates/larch-cli/src/design_publish_commands.rs", kind="absent", needle="LARCH-DIAGRAM"),
    StructurePin(skill="design", label="SKILL must not instruct diagram body re-emission", path="skills/design/SKILL.md", kind="absent", needle="re-emit that exact body verbatim in chat"),
    StructurePin(skill="design", label="settle must map gate-b postplan site", path="crates/larch-cli/src/design_settle_commands.rs", kind="contains", needle='"gate-b" => "gate-b"'),
    StructurePin(skill="design", label="settle must map discussion postplan site", path="crates/larch-cli/src/design_settle_commands.rs", kind="contains", needle='"gate-a" | "discussion-round2" => "discussion-round2"'),
    StructurePin(skill="design", label="settle must map gate-c postplan site", path="crates/larch-cli/src/design_settle_commands.rs", kind="contains", needle='"gate-c" => "gate-c"'),
    StructurePin(skill="design", label="settle must dispatch settle-next-action through the Rust owner", path="crates/larch-cli/src/design_settle_commands.rs", kind="contains", needle='"settle-next-action".to_owned()'),
    StructurePin(skill="design", label="settle must not retain a Python runtime registration", path="python/larch/cli.py", kind="absent", needle='("design", "step35-settle")'),
    StructurePin(skill="design", label="settle dispatch must name primary SETTLE_NEXT_ACTION key", path="skills/design/references/settle-rc-dispatch.md", kind="contains", needle="Primary key: branch on the whole-line `SETTLE_NEXT_ACTION=...` row from `scripts/larch.sh design step35-settle` stdout."),
    StructurePin(skill="design", label="settle dispatch must fail closed when action row is absent", path="skills/design/references/settle-rc-dispatch.md", kind="contains", needle="If the `SETTLE_NEXT_ACTION` action row is absent, stop for operator repair. Do not route from the wrapper rc when the action row is missing."),
    StructurePin(skill="design", label="settle dispatch must stop on action rc disagreement", path="skills/design/references/settle-rc-dispatch.md", kind="contains", needle="If `SETTLE_NEXT_ACTION` and wrapper rc disagree, stop for repair rather than silently choosing one."),
    StructurePin(skill="design", label="settle dispatch must keep wrapper rc diagnostic-only", path="skills/design/references/settle-rc-dispatch.md", kind="contains", needle="Wrapper exit codes remain diagnostics and legacy process contracts only. The orchestrator must not use them as fallback routing authority."),
    StructurePin(skill="design", label="settle dispatch must delegate action derivation to the settle-next-action owner", path="skills/design/references/settle-rc-dispatch.md", kind="contains", needle='chooses the action through `"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" design settle-next-action`; this file does not derive actions from rc values.'),
    StructurePin(skill="design", label="settle rc dispatch must reject POSTPLAN_RC=1 wording", path="skills/design/references/settle-rc-dispatch.md", kind="contains", needle="There is no `POSTPLAN_RC=1` on the postplan path."),
    StructurePin(skill="design", label="settle dispatch must remove fallback key paragraph", path="skills/design/references/settle-rc-dispatch.md", kind="absent", needle="Fallback key: when the action row is missing"),
    StructurePin(skill="design", label="settle dispatch must remove wrapper rc fallback section", path="skills/design/references/settle-rc-dispatch.md", kind="absent", needle="## Fallback: branch on wrapper rc"),
    StructurePin(skill="design", label="settle dispatch must remove site variant fallback section", path="skills/design/references/settle-rc-dispatch.md", kind="absent", needle="## Site variants for fallback rc dispatch"),
    StructurePin(skill="design", label="settle dispatch must remove Gate B fallback variant row", path="skills/design/references/settle-rc-dispatch.md", kind="absent", needle="| **Gate B** |"),
    StructurePin(skill="design", label="settle dispatch must remove Gate A fallback variant row", path="skills/design/references/settle-rc-dispatch.md", kind="absent", needle="| **Gate A / discussion-round2** |"),
    StructurePin(skill="design", label="approval-gates must document render-gate invocation", path="skills/design/references/approval-gates.md", kind="contains", needle='Run renderer commands as `"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" design render-gate ...`.'),
    StructurePin(skill="design", label="Gate A must delegate prompt copy to render-gate", path="skills/design/references/approval-gates-gate-a.md", kind="contains", needle="**Shape 2: re-entry from Gate B(c) or Gate C(b) (post-plan)**: run `scripts/larch.sh design render-gate --gate A`. Pass the rendered `HEADER`, `QUESTION`, and option rows directly to `AskUserQuestion`."),
    StructurePin(skill="design", label="Gate B default must delegate auto-apply copy to render-gate", path="skills/design/references/approval-gates-gate-b.md", kind="contains", needle='Run `scripts/larch.sh design render-gate --gate B --accepted-count "$N" --approve-requested false`, print `AUTO_APPLY_MESSAGE`, then Execute `### Apply-all body` verbatim.'),
    StructurePin(skill="design", label="Gate C must delegate prompt copy to render-gate with accepted audit escalation", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle='Run `scripts/larch.sh design render-gate --gate C --design-tmpdir "$DESIGN_TMPDIR" --accepted-audit-escalation "${STRONG_AUDIT_DISSENT:-false}"` and pass the rendered `HEADER`, `QUESTION`, and option rows directly to `AskUserQuestion`.'),
    StructurePin(skill="design", label="approval-gates must still point explicit mode to approval-gates-explicit", path="skills/design/references/approval-gates-gate-b.md", kind="contains", needle="approval-gates-explicit.md"),
    StructurePin(skill="design", label="approval-gates must not retain inline Gate A question text", path="skills/design/references/approval-gates-gate-a.md", kind="absent", needle="All open design questions appear discussed. Ready to launch the design review, or would you like to discuss more first?"),
    StructurePin(skill="design", label="approval-gates must not retain inline Gate C below-cap question text", path="skills/design/references/approval-gates-gate-c.md", kind="absent", needle="Final design plan is ready. Approve, see the full plan, discuss further, or re-run the review panel against this plan?"),
    StructurePin(skill="design", label="cli registry must not re-register Rust-owned design render-gate", path="python/larch/cli.py", kind="absent", needle='("design", "render-gate")'),
    StructurePin(skill="design", label="accepted audit must name cumulative accepted corpus in read list", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle="accepted-plan-findings-all.md` when present (cumulative acceptance context)."),
    StructurePin(skill="design", label="accepted audit must name current-round accepted corpus in read list", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle="accepted-plan-findings.md` when present (current-round Gate B apply set; not the end-state fidelity authority)."),
    StructurePin(skill="design", label="accepted audit must name selected corpus fidelity source", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle="filtered accepted corpus selected above"),
    StructurePin(skill="design", label="accepted audit must read pre-review snapshot", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle="plan-before-review.txt` when present."),
    StructurePin(skill="design", label="accepted audit must read Round 1 refusals", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle="discussion-round1.md` when present (explicit Round 1 refusals)."),
    StructurePin(skill="design", label="accepted audit must read approved outline non-goals", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle="design-outline.md` when `.outline-approved` exists (approved non-goals)."),
    StructurePin(skill="design", label="accepted audit must mirror compose_review corpus precedence", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle="bind `_accepted_corpus` to non-empty `$DESIGN_TMPDIR/accepted-plan-findings-all.md` when that file exists and has non-zero size; else to non-empty `$DESIGN_TMPDIR/accepted-plan-findings.md`; else treat as no cumulative accepted findings."),
    StructurePin(skill="design", label="accepted audit must include filter-gate-b-skipped invocation", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle='"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" plan-review filter-gate-b-skipped \\'),
    StructurePin(skill="design", label="accepted audit filter invocation must pass selected corpus", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle='--accepted "${_accepted_corpus}"'),
    StructurePin(skill="design", label="accepted audit must fail closed on skip-filter failure", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle="On filter helper non-zero exit: print `**⚠ 4b: accepted-plan-findings skip-filter failed**`, append a bounded warning with `site=design Gate C Presentation` and `reason=filter-gate-b-skipped-failed`, and stop before persist, prompt, auto-approval, or Step 5."),
    StructurePin(skill="design", label="accepted audit strong dissent must override skip-approve", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle="Auto-approve only after accepted-findings audit persistence succeeds and binds `STRONG_AUDIT_DISSENT=false`; strong disagreement suppresses the auto-approve breadcrumb, requires `AskUserQuestion`, and passes `--accepted-audit-escalation true` to every Gate C `render-gate` invocation."),
    StructurePin(skill="design", label="accepted audit must rerun on every Gate C Presentation", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle="Run the full audit on every Gate C Presentation, including `resume@4b`, pause recovery, re-entry after discussion, re-run review, or postplan fixes."),
    StructurePin(skill="design", label="accepted audit must print mild digest before prompt or auto-approve", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle="mild-disagree or strong-disagree prints a compact audit digest immediately before either Gate C `AskUserQuestion` or the `--skip-approve` auto-approval breadcrumb."),
    StructurePin(skill="design", label="Gate C render-gate example must include accepted audit escalation", path="skills/design/references/approval-gates-gate-c.md", kind="contains", needle='--accepted-audit-escalation "${STRONG_AUDIT_DISSENT:-false}"'),
    StructurePin(skill="design", label="design-step3-entry must snapshot pre-review plan", path="skills/design/scripts/design-step3-entry.sh", kind="contains", needle="plan-review snapshot-pre-review"),
    StructurePin(skill="design", label="plan-review reference must document pre-review snapshot", path="skills/design/references/plan-review-runtime.md", kind="contains", needle="plan-before-review.txt` is written once per Step 3 entry"),
    StructurePin(skill="design", label="approval-gates must not retain inline settle rc branch table", path="skills/design/references/approval-gates-gate-b.md", kind="absent", needle="Branch on the settle wrapper rc"),
    StructurePin(skill="design", label="approval-gates must not retain inline wrapper rc branch table", path="skills/design/references/approval-gates-gate-b.md", kind="absent", needle="Branch on wrapper rc"),
    StructurePin(skill="design", label="approval-gates must not retain Gate B fallback-row prose", path="skills/design/references/approval-gates-gate-b.md", kind="absent", needle="fallback row"),
    StructurePin(skill="design", label="discussion-rounds must not retain inline settle rc branch table", path="skills/design/references/discussion-rounds.md", kind="absent", needle="Branch on the settle wrapper rc"),
    StructurePin(skill="design", label="discussion-rounds must not retain inline wrapper rc branch table", path="skills/design/references/discussion-rounds.md", kind="absent", needle="Branch on wrapper rc"),
    StructurePin(skill="design", label="discussion-rounds must not retain fallback-row prose", path="skills/design/references/discussion-rounds.md", kind="absent", needle="fallback row"),
    StructurePin(skill="design", label="SKILL must not retain inline settle rc branch table", path="skills/design/SKILL.md", kind="absent", needle="Branch on the settle wrapper rc"),
    StructurePin(skill="design", label="SKILL must not retain inline wrapper rc branch table", path="skills/design/SKILL.md", kind="absent", needle="Branch on wrapper rc"),
    StructurePin(skill="design", label="SKILL must not retain settle fallback-row prose", path="skills/design/SKILL.md", kind="absent", needle="fallback row"),
    StructurePin(skill="design", label="step2b5 rc handling must keep gate-a-hard-size direct-entry trigger", path="skills/design/references/step2b5-rc-handling.md", kind="contains", needle="settle action `SETTLE_NEXT_ACTION=gate-a-hard-size`"),
    StructurePin(skill="design", label="step2b5 rc handling must reject prompt-side action derivation", path="skills/design/references/step2b5-rc-handling.md", kind="contains", needle="Do not recompute the action from check-size rc, `SIZE_TRIGGER_FIRED`, `DRIFT_TRIGGER_FIRED`, or `partition_requested` in prompt prose."),
    StructurePin(skill="design", label="step2b5 rc handling must reject process-rc fallback routing", path="skills/design/references/step2b5-rc-handling.md", kind="contains", needle="If `STEP2B5_NEXT_ACTION` is absent, stop for repair. Do not route from process rc or raw trigger KVs when the action row is missing."),
    StructurePin(skill="design", label="step2b5 rc handling must delegate gate-b-hard-size to approval-gates", path="skills/design/references/step2b5-rc-handling.md", kind="contains", needle="Do not load for `SETTLE_NEXT_ACTION=gate-b-hard-size`; Gate B uses `approval-gates-gate-b.md`."),
    StructurePin(skill="design", label="step2b5 rc handling must remove Gate A fallback rc trigger", path="skills/design/references/step2b5-rc-handling.md", kind="absent", needle="Gate A / discussion-round2 fallback rc `12`"),
    StructurePin(skill="design", label="step2b5 rc handling must remove Gate B fallback rc trigger", path="skills/design/references/step2b5-rc-handling.md", kind="absent", needle="Gate B fallback rc `12`"),
    StructurePin(skill="design", label="approval-gates must own Gate B pre-apply round binding", path="skills/design/references/approval-gates-gate-b.md", kind="contains", needle="Before executing the Gate B body, bind `_gate_b_round` from `FINAL_ROUND_NUM`, then `STEP3_REVIEW_ROUND_NUM`, then `ROUND_NUM`; fail closed if it is empty or non-numeric."),
    StructurePin(skill="design", label="approval-gates must route post-apply resume through settle without reapply", path="skills/design/references/approval-gates-gate-b.md", kind="contains", needle='Route through the same settle wrapper with `--round-num "$_gate_b_round"` without reapplying.'),
    StructurePin(skill="design", label="approval-gates must bind Step 3 resume round after post-apply resume", path="skills/design/references/approval-gates-gate-b.md", kind="contains", needle='Bind `STEP3_RESUME_ROUND="$_gate_b_round"` before any later Step 3 resume fence.'),
    StructurePin(skill="design", label="approval-gates must forbid direct Step 3b jump from post-apply resume", path="skills/design/references/approval-gates-gate-b.md", kind="contains", needle="Do not jump directly to Step 3b from this post-apply resume branch"),
    StructurePin(skill="design", label="SKILL must name step2b-drafter Rust authority", path="skills/design/SKILL.md", kind="contains", needle="scripts/larch.sh design step2b-drafter"),
    StructurePin(skill="design", label="SKILL must name step2b-postplan Rust authority", path="skills/design/SKILL.md", kind="contains", needle="scripts/larch.sh design step2b-postplan"),
    StructurePin(skill="design", label="launcher must map design-step6.sh", path="crates/larch-core/src/session_env.rs", kind="contains", needle="design-step6.sh)"),
    StructurePin(skill="design", label="launcher must forward step6 to scripts/larch.sh", path="crates/larch-core/src/session_env.rs", kind="contains", needle=r'scripts/larch.sh\" design step6 --session-env-path \"$SESSION_ENV_PATH\" --claude-pid \"$CLAUDE_PID\" \"$@\"'),
    StructurePin(skill="design", label="launcher must map design-step6-prelude.sh", path="crates/larch-core/src/session_env.rs", kind="contains", needle="design-step6-prelude.sh)"),
    StructurePin(skill="design", label="launcher must forward step6-prelude to scripts/larch.sh", path="crates/larch-core/src/session_env.rs", kind="contains", needle=r'scripts/larch.sh\" design step6-prelude --session-env-path \"$SESSION_ENV_PATH\" --claude-pid \"$CLAUDE_PID\" \"$@\"'),
    StructurePin(skill="design", label="launcher must map design-step6-cleanup.sh", path="crates/larch-core/src/session_env.rs", kind="contains", needle="design-step6-cleanup.sh)"),
    StructurePin(skill="design", label="launcher must forward step6-cleanup to scripts/larch.sh", path="crates/larch-core/src/session_env.rs", kind="contains", needle=r'scripts/larch.sh\" design step6-cleanup --session-env-path \"$SESSION_ENV_PATH\" --claude-pid \"$CLAUDE_PID\" \"$@\"'),
    StructurePin(skill="design", label="SKILL Step 6 fence must use bare launcher verb", path="skills/design/SKILL.md", kind="contains", needle='"$HOME/.cache/larch/sessions/design-run-$PPID.sh" step6'),
    StructurePin(skill="design", label="SKILL Step 5 must load finalize-step5 immediately after invariant", path="skills/design/SKILL.md", kind="adjacent_pair_count_at_least", needle="**Invariant (anti-pattern):** do **not** reorder finalize sub-steps to run the `[DESIGNED]` rename (old Step 5c tail) before OOS filing (Step 5b) completes successfully: that would publish a terminal title while accepted OOS items are not yet filed. Step **5b** MUST run before Step **5b.5**, and Step **5c** MUST complete the Step **5b.5** sanitize gate before `larch:plan` write, publish, and rename.", needle2="**MANDATORY: READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/finalize-step5.md` completely.", expected=1, count_unit="adjacent_pair", comparator="at_least"),
    StructurePin(skill="design", label="SKILL Step 5 must load finalize-step5 before prepare fence", path="skills/design/SKILL.md", kind="ordered", needle="**MANDATORY: READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/finalize-step5.md` completely.", needle2='"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step5b-prepare.sh', match_mode="exact_line"),
        StructurePin(skill="design", label="approval-gates must load settle dispatch immediately before Gate B branch directive", path="skills/design/references/approval-gates-gate-b.md", kind="adjacent_pair_count_at_least", needle="   1. **MANDATORY: READ ENTIRE FILE**: Read `skills/design/references/settle-rc-dispatch.md` completely.", needle2="   2. Require `SETTLE_NEXT_ACTION`; stop for repair if it is absent. If the action row and wrapper rc disagree, stop for repair. Branch only on the matching `SETTLE_NEXT_ACTION` row in `settle-rc-dispatch.md`.", expected=1, count_unit="adjacent_pair", comparator="at_least"),
    StructurePin(skill="design", label="discussion-rounds must use numbered settle dispatch steps 1-2", path="skills/design/references/discussion-rounds.md", kind="adjacent_pair_count_at_least", needle="1. **MANDATORY: READ ENTIRE FILE**: Read `skills/design/references/settle-rc-dispatch.md` completely.", needle2="2. Require `SETTLE_NEXT_ACTION`; stop for repair if it is absent. Branch only on the matching `SETTLE_NEXT_ACTION` row in `settle-rc-dispatch.md`.", expected=1, count_unit="adjacent_pair", comparator="at_least"),
    StructurePin(skill="design", label="SKILL Gate A guard must load settle dispatch immediately before branch directive", path="skills/design/SKILL.md", kind="adjacent_pair_count_at_least", needle="1. **MANDATORY: READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/settle-rc-dispatch.md` completely (if not already loaded at discussion-round2).", needle2="2. Require `SETTLE_NEXT_ACTION`; stop for repair if it is absent. If the action row and wrapper rc disagree, stop for repair. Branch only on the matching `SETTLE_NEXT_ACTION` row in `settle-rc-dispatch.md`.", expected=1, count_unit="adjacent_pair", comparator="at_least"),
    StructurePin(skill="design", label="SKILL Gate B guard must load settle dispatch immediately before branch directive", path="skills/design/SKILL.md", kind="adjacent_pair_count_at_least", needle="1. **MANDATORY: READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/settle-rc-dispatch.md` completely (if not already loaded at Step 1e).", needle2="2. Require `SETTLE_NEXT_ACTION`; stop for repair if it is absent. If the action row and wrapper rc disagree, stop for repair. Branch only on the matching `SETTLE_NEXT_ACTION` row in `settle-rc-dispatch.md`.", expected=1, count_unit="adjacent_pair", comparator="at_least"),
StructurePin(skill="design", label="Gate A slice must load only in the Step 1e re-entry block", path="skills/design/SKILL.md", kind="exact_count", needle="approval-gates-gate-a.md` completely", expected=1, count_unit="matching_line", comparator="exact"),
    StructurePin(skill="design", label="Gate A slice must remain absent from the default pre-plan path", path="skills/design/SKILL.md", kind="ordered", needle="<!-- step:1e: Discussion Mode Gate (Gate A) -->", needle2="approval-gates-gate-a.md` completely", match_mode="contains"),
)

ALL_PINS: Final[tuple[StructurePin, ...]] = (
    *ALIAS_PINS,
    *BUG_PINS,
    *LEARN_FROM_BUGS_PINS,
    *DESIGN_PINS,
    *IMPLEMENT_PINS,
    *RESEARCH_PINS,
    *REVIEW_PINS,
    *UMBRELLA_PINS,
)


def validate_pin_table(pins: tuple[StructurePin, ...]) -> None:
    """Fail loudly on duplicate IDs or malformed pin configuration."""
    seen: set[str] = set()
    for pin in pins:
        if pin.kind not in {
            "contains",
            "absent",
            "exact_count",
            "count_at_least",
            "ordered",
            "same_line",
            "adjacent_pair_count_at_least",
            "cross_file_bound",
        }:
            raise ValueError(f"unknown predicate: {pin.kind!r}")
        if not pin.label.strip():
            raise ValueError(f"empty label for skill={pin.skill!r}")
        if not pin.path.strip():
            raise ValueError(f"empty path for label={pin.label!r}")
        pid = pin.param_id
        if pid in seen:
            raise ValueError(f"duplicate param_id: {pid!r} ({pin.label!r})")
        seen.add(pid)
        if pin.match not in {"fixed", "regex"}:
            raise ValueError(f"unknown match kind: {pin.match!r}")
        if pin.count_unit not in {"physical_line", "matching_line", "substring", "adjacent_pair"}:
            raise ValueError(f"unknown count unit: {pin.count_unit!r}")
        if pin.comparator not in {"exact", "at_least"}:
            raise ValueError(f"unknown comparator: {pin.comparator!r}")
        if pin.match_mode not in {"exact_line", "contains"}:
            raise ValueError(f"unknown match mode: {pin.match_mode!r}")
        if pin.kind in {"contains", "absent", "exact_count", "count_at_least"} and not pin.needle:
            raise ValueError(f"empty needle for {pin.label!r}")
        if pin.kind == "ordered" and (not pin.needle or not pin.needle2):
            raise ValueError(f"ordered pin incomplete: {pin.label!r}")
        if pin.kind == "adjacent_pair_count_at_least":
            if not pin.needle or not pin.needle2:
                raise ValueError(f"adjacent-pair incomplete: {pin.label!r}")
            if (
                not isinstance(pin.expected, int)
                or isinstance(pin.expected, bool)
                or pin.expected < 0
            ):
                raise ValueError(
                    f"adjacent-pair needs non-negative integer expected: {pin.label!r}"
                )
            if pin.count_unit != "adjacent_pair":
                raise ValueError(
                    f"adjacent-pair requires count_unit='adjacent_pair': {pin.label!r}"
                )
            if pin.comparator != "at_least":
                raise ValueError(
                    f"adjacent-pair requires comparator='at_least': {pin.label!r}"
                )
        if pin.kind == "cross_file_bound":
            if not pin.path2 or not pin.needle or not pin.needle2:
                raise ValueError(f"cross_file_bound incomplete: {pin.label!r}")
            if (
                not isinstance(pin.bound, int)
                or isinstance(pin.bound, bool)
                or pin.bound < 0
            ):
                raise ValueError(
                    f"cross_file_bound needs non-negative integer bound: {pin.label!r}"
                )
        if pin.kind in {"exact_count", "count_at_least"}:
            if not isinstance(pin.expected, int) or isinstance(pin.expected, bool) or pin.expected < 0:
                raise ValueError(f"count pin needs non-negative integer expected: {pin.label!r}")
            expected_comparator = "exact" if pin.kind == "exact_count" else "at_least"
            if pin.comparator != expected_comparator:
                raise ValueError(
                    f"{pin.kind} requires comparator={expected_comparator!r}: {pin.label!r}"
                )
        if pin.kind == "same_line" and len(pin.tokens) < 2:
            raise ValueError(f"same_line needs >=2 tokens: {pin.label!r}")
        if pin.kind == "same_line" and any(not token for token in pin.tokens):
            raise ValueError(f"same_line has empty token: {pin.label!r}")


validate_pin_table(ALL_PINS)

# Focused Make -k expressions: pins use skill- prefix; specialized tests use test_<skill>_structure
FOCUSED_SELECTION: Final[dict[str, str]] = {
    "alias": "alias_structure",
    "file-bug": "file_bug_structure",
    "design": "design_structure_pin or design_structure_specialized",
    "implement": "implement_structure",
    "learn-from-bugs": "learn_from_bugs_structure",
    "research": "research_structure",
    "review": "review_structure",
}

FOCUSED_TARGETS: Final[dict[str, str]] = {
    "alias": "test-alias-structure",
    "file-bug": "test-file-bug-structure",
    "design": "test-design-structure",
    "implement": "test-implement-structure",
    "learn-from-bugs": "test-learn-from-bugs-structure",
    "research": "test-research-structure",
    "review": "test-review-structure",
}

SPECIALIZED_MODULES: Final[dict[str, str]] = {
    "alias": "_structure_alias_specialized",
    "file-bug": "_structure_file_bug_specialized",
    "design": "_structure_design_specialized",
    "implement": "_structure_implement_specialized",
    "learn-from-bugs": "_structure_learn_from_bugs_specialized",
    "research": "_structure_research_specialized",
    "review": "_structure_review_specialized",
}
