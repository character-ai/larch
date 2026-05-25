## Plan

Add a public boolean flag `--brainstorm` to `/design`. When set, a new **Step 1d.5** runs between Step 1d (Round 1 discussion) and Step 1e (Gate A): it dispatches a 3-agent ideation panel (Cursor + Codex + always-Claude), the main agent synthesizes/dedupes/orders the outputs to `$DESIGN_TMPDIR/brainstorm.md`, then enters a free-form discussion loop with the user until they signal ready. A `$DESIGN_TMPDIR/.brainstorm-done` sentinel makes the step one-shot per invocation. Downstream Step 2a (sketch prompt context), Step 2a.5 (dialectic synthesis input), Step 2b (plan), and Step 3 (plan-review reviewer feature-context) read `brainstorm.md` additively (never required, never load-bearing). All existing tier flows are functionally unchanged when `--brainstorm` is absent.

Dialectic-resolved (DECISION_1, 3-0 THESIS): Step 1d.5 placement (before Gate A) wins over Step 1f (after Gate A's first-time Ready). Placing brainstorm before Gate A preserves the pre-plan Gate A "Discuss more" re-entry path for scope questions surfaced by brainstorm.

### Files to modify/create (19 total: 4 NEW, 15 UPDATED)

**NEW**
- `skills/design/references/brainstorm.md` — normative Step 1d.5 body: front matter, MANDATORY directive pointing at brainstorm-prompts.md, anti-halt override (with explicit ScheduleWakeup/sleep/polling prohibition), entry guard, per-slot prompt-file rendering (discussion-round1.md read conditionally), 3-agent panel launch matrix with **Agent-returns-text + parent-writes-file** fallback convention, collection (`collect-agent-results.sh` for externals only, with foreground banner + in-fence comment per `lint-foreground-markers.sh`), post-collection dirty-tree boundary (`STAGE=brainstorm-collection`), synthesis, `## Brainstorm Synthesis` H2 + per-idea H3 + `**Source**:` schema, free-form discussion loop with **classify-message-first** branch order and **standalone primary-intent** termination disambiguation, sentinel write, downstream consumer contract naming Step 2a / 2a.5 / 2b / 3.
- `skills/design/references/brainstorm-prompts.md` — three role prompts: `<BRAINSTORM_FRAMING_PROMPT>` (Cursor role: feature framings), `<BRAINSTORM_SCOPE_PROMPT>` (Codex role: scope alternatives), `<BRAINSTORM_PRAGMATIC_PROMPT>` (always-Claude role: smallest-viable interpretations).
- `skills/design/scripts/test-brainstorm-prompts.sh` + sibling `.md` — offline harness pinning the three prompt-token literals; mirrors `test-plan-review-prompt.sh`.

**UPDATED — skills/design/**
- `SKILL.md` — argument-hint frontmatter; opening flags paragraph + compact flag table row; mutual-exclusion paragraph; anti-halt continuation reminder extended to `1c→1d→1d.5→1e` with the Step 1d.5 carve-out (only synthesis-print turn-yield permitted; no ScheduleWakeup/summary/handoff); Pre-Step-0 interactive `--trivial + --brainstorm` collision via `AskUserQuestion` (Upgrade to --simple / Cancel) setting `effective_tier=simple` that Step 0b honors; Step 0b argv parser extended (`--brainstorm` → `brainstorm_requested`); Step 0b tier gate also fires the same collision prompt when user picks trivial with brainstorm set; Step 0b already-planned router's ad-hoc Q&A branch writes run-params AND runs Step 1d.5 before the Q&A exit; Step 0b tier→run-params block passes `--brainstorm-requested`; recovery jq-merge and no-file-recovery write paths guard on `partition_requested OR brainstorm_requested` and merge/pass both flags atomically; NEW Step 1d.5 section between Step 1d and Step 1e with MANDATORY pointer to `references/brainstorm.md`; Step 2a (sketches) prose extended so sketch `<FEATURE_DESCRIPTION>` substitution incorporates brainstorm.md when present; Step 2a.5 dialectic synthesis_text MAY incorporate brainstorm context; Step 2b plan reads brainstorm.md additively; Step 3 plan-review feature-context (passed via `plan-review-loop.sh --feature-file`) includes brainstorm.md when present.
- `references/flags.md` — public `--brainstorm` flag bullet; mutual-exclusion paragraph extended; internal `brainstorm_requested` JSON field note.
- `scripts/step-name-registry.tsv` — append `1d.5\tbrainstorm` between rows 4 and 5.

**UPDATED — scripts/ (run-params + timing-kinds plumbing)**
- `write-run-params.sh` + sibling `.md` — add `--brainstorm-requested <true|false>` (1:1 mirror of `--partition-requested`); validate `require_enum true false`; persist as `brainstorm_requested` JSON boolean; document in sibling .md.
- `test-write-run-params.sh` + sibling `.md` — round-trip + default-false + invalid-value rejection + both-flags-true (FINDING_15 recovery path coverage) tests; sibling .md syncs.
- `lib-timing-kinds.sh` — append `cursor-brainstorm`, `codex-brainstorm` task kinds.
- `lib-timing-kinds.md` — sibling-doc sync (no-op if file absent).
- `test-design-structure.sh` + sibling `.md` — 17 new grep-based assertions covering: `--brainstorm` literals in argument-hint / flag table / public-argv allowlist sentence / mutex prose; Step 1d.5 anchor + breadcrumb; new reference files exist; step-name-registry row; brainstorm-prompts.md prompt-token literals; flags.md content; anti-halt sequence `1c→1d→1d.5→1e`; brainstorm.md MANDATORY pointer to brainstorm-prompts.md; brainstorm.md collector fence foreground markers; Step 0b primary writer `--brainstorm-requested "$brainstorm_requested"` literal; recovery writer + jq merge literals; brainstorm.md anti-halt ScheduleWakeup-prohibition sentence.

**UPDATED — top-level + docs**
- `Makefile` — add `test-brainstorm-prompts` to `.PHONY`, target rule wrapped in `harness-timer`, exactly one `test-harnesses-N` shard entry.
- `docs/linting.md` — document the new harness row.
- `README.md` — argument-hint string + brief `--brainstorm` mention.
- `docs/skills.md` — `/design` skill entry argument string + brief description.

**Deliberately NOT modified**: `scripts/write-design-current-env.sh`, `agents/`, `plan-block-write.sh`, `design-log-publish.sh`, `composed-plan.md` composition logic, `tracking-issue-write.sh`, `tally-plan-review.sh`, `validate-plan-commands.sh`, `agent-lint.toml`, Step 3 per-reviewer prompt templates (brainstorm context flows through the existing `--feature-file` channel, not via prompt-template edits).

### Approach summary

The implementation is shaped exactly like the existing `--partition` plumbing for reviewer comparability — same flag-parsing pattern, same JSON field, same recovery-block pattern. The new step body is modeled on Step 2a sketch parallel-launch but uses the **Agent-returns-text + parent-writes-file** convention required by existing larch convention (Agent tools return text to parent; do NOT write files). `effective_tier` is the single mechanism mediating `--trivial + --brainstorm` collision across Pre-Step-0 and Step 0b's tier gate.

### Architecture

A mermaid flowchart is attached separately to the design log (`$DESIGN_TMPDIR/architecture-diagram.md`). It shows the new Step 1d.5 control flow (`--trivial` collision gate → effective_tier → Step 0b → 1c/1d → 1d.5 panel → discussion loop → sentinel → Gate A), the 3-agent panel structure (Cursor / Codex / always-Claude with Agent-fallback Write convention), the collection + dirty-tree boundary, the free-form discussion loop with intent classification and termination disambiguation, and the additive downstream-consumer paths into Step 2a / 2a.5 / 2b / 3.

## Acceptance

The design is ready for `/implement` admission. To consider the implementation done, the following must hold:

1. **Public flag surface**: `--brainstorm` parses correctly on argv; `claude '/design --brainstorm --simple 9999'` (against any throwaway issue) does not fail flag parsing; SKILL.md argument-hint, flag table, and flags.md bullet are all in sync.
2. **run-params.json schema**: `brainstorm_requested` boolean field present in `run-params.json` (`false` by default; `true` when `--brainstorm` is on argv or set by the Pre-Step-0 upgrade path). `scripts/test-write-run-params.sh` passes.
3. **Pre-Step-0 collision UX**: `claude '/design --brainstorm --trivial 9999'` fires an `AskUserQuestion` BEFORE `session-setup.sh` runs. Upgrade-to-simple selects `effective_tier=simple` AND `brainstorm_requested=true` in run-params.json. Cancel exits 0 without `DESIGN_TMPDIR`.
4. **Tier-gate collision UX**: `claude '/design --brainstorm 9999'` (no tier flag) shows the tier gate; if user picks `trivial`, the same Upgrade/Cancel prompt fires; Upgrade maps to SIMPLE.
5. **Already-planned ad-hoc Q&A**: when an issue body already has a `larch:plan` block and the user picks ad-hoc Q&A with `--brainstorm` set, run-params.json is written with `brainstorm_requested=true` AND Step 1d.5 runs before the Q&A exit.
6. **Step 1d.5 anchored**: SKILL.md contains `<!-- step:1d.5 — Brainstorm Panel -->` anchor and the breadcrumb literal; `skills/design/scripts/step-name-registry.tsv` has the `1d.5\tbrainstorm` row.
7. **References exist**: `skills/design/references/brainstorm.md` and `brainstorm-prompts.md` are present, non-empty, with the three `<BRAINSTORM_*_PROMPT>` token literals; brainstorm.md includes the explicit anti-halt override with the ScheduleWakeup/sleep/polling prohibition; brainstorm.md collector fence carries the foreground banner + in-fence `# Foreground required: see BASH_AUTHORING.md §4` comment (`make lint-foreground-markers` passes).
8. **Anti-halt sequence pin**: SKILL.md anti-halt paragraph contains `1c→1d→1d.5→1e` in the transition list and the Step 1d.5 narrow-exception sentence.
9. **Agent-return convention**: brainstorm.md explicitly states that Cursor/Codex Agent fallbacks return text to the parent and the parent Writes that returned text to the deterministic slot output file before synthesis; `collect-agent-results.sh` is invoked ONLY for genuinely external slots actually launched.
10. **Dirty-tree boundary**: brainstorm.md includes the post-collection `check-mid-run-dirty-tree.sh --mode checkpoint` step with `STAGE=brainstorm-collection` and the `.dirty-tree-prompted-brainstorm-collection` sentinel.
11. **Discussion loop semantics**: brainstorm.md documents the classify-message-first branch order (terminal → sentinel → continue to Step 1e in same turn, no re-print; refinement → mutate → re-print → end turn; ambiguous → two-option AskUserQuestion) AND the termination-vocabulary disambiguation rule (terminate only on standalone primary-intent cue; negated/conditional/refinement-bearing → continue).
12. **Downstream readers**: SKILL.md Step 2a (sketches), Step 2a.5 (dialectic), Step 2b (plan), and Step 3 (plan-review feature-context) all include the additive read of `$DESIGN_TMPDIR/brainstorm.md` when present and non-empty. Step 3 wiring updates `dispatch-plan-review-panel.sh` (or its caller) so the feature-context blob passed to reviewers includes brainstorm.md content.
13. **Test coverage**: `make test-write-run-params` and `make test-brainstorm-prompts` pass; `scripts/test-design-structure.sh` includes the 17 new assertions and passes; `make lint` and `make lint-foreground-markers` pass with no new agent-lint suppressions; `bash scripts/relevant-checks.sh` passes.
14. **Sibling docs**: `scripts/write-run-params.md`, `scripts/test-write-run-params.md`, `scripts/lib-timing-kinds.md` (if it exists), `scripts/test-design-structure.md` are updated to document the new fields, test cases, and assertions.
15. **Public docs**: `README.md` and `docs/skills.md` mention `--brainstorm`; `Makefile` and `docs/linting.md` document the new `test-brainstorm-prompts` harness.
16. **Off-path byte-stability**: `claude '/design --simple 9999'` (no `--brainstorm`) shows `⏩ 1d.5: brainstorm — skipped` and produces a plan path byte-equivalent to today's `--simple` flow (no brainstorm.md, no sentinel, no panel launches).

diff_lines: 530
