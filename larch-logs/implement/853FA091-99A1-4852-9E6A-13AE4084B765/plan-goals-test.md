## Goal
Implement issue #2956: [IMPLEMENTING] Get rid of trivial mode in /design, consolidating SIMPLE and HARD\n\n<!-- larch:plan:start -->.

## Implementation Plan
## Plan

# Implementation Plan — Issue #2956

Consolidate `/design` to two tiers (`SIMPLE` / `HARD`) by removing the `TRIVIAL` tier entirely, collapsing the `run-params.json` schema to a single `design_classification` enum, deleting all derived/legacy fields (`quick_mode`, `review_budget`, `sketch_budget`, `design_classification_source`, `design_classification_reason`), narrowing `workflow_path` scope to legacy timing-readers only, introducing per-tier emphasis prose (SIMPLE = minimize changes; HARD = thoroughness), and adding a per-tier review-round cap that fires on every Step 3 entry (SIMPLE = 3 total panel runs, HARD = 5). No backward compatibility shims.

New SIMPLE = no sketches + no dialectic + full external review panel + plan-command validator + 3-round Step 3 cap. New HARD = unchanged from current HARD behavior + 5-round Step 3 cap.

## Approach

**Strategy: contract collapse, not compatibility layer.** Single enum drives all design-skill branching. A new shared reader `scripts/read-design-classification.sh` is the canonical fallback path (python3 → jq → grep, defaults to HARD on read failure with a warning); SKILL.md, approval-gates.md prose, and `render-plan-review-prompt.sh` all consume it. `--trivial` argv → Pre-Step-0 hard error. Validator gating script is renamed and runs unconditionally. SIMPLE sketch-skip uses the renamed `NO_SKETCHES_CLASSIFIED_SIMPLE` sentinel.

**`workflow_path` is NOT renamed globally.** `/implement` run logs still write `workflow_path`. `scripts/timing-ledger.sh`, `scripts/timing-report.sh`, `skills/report-tokens/scripts/run-analysis.sh` keep reading `workflow_path` UNCHANGED to preserve implement-run analysis. They gain a graceful fallback: read `workflow_path` first; if absent (the new design v2 shape), read `design_classification`. /design's v2 run-params.json does NOT carry `workflow_path` — design-only readers (e.g., `render-final-summary.sh`) read `design_classification` directly.

**Review-round cap state and enforcement**: persist a counter at `$DESIGN_TMPDIR/review-round-count.txt` (single integer, no schema). **Ownership: SKILL.md Step 3 is the sole writer.** `plan-review-loop.sh` MUST NOT read or write the file — it only consumes the supplied `--round-num <int>`. SKILL.md Step 3 entry block executes the following at every Step 3 entry (initial, Gate C re-run, Gate A "Ready for review" post-discussion):

1. Read `$DESIGN_TMPDIR/review-round-count.txt` (treat missing/empty/non-numeric as 0; log a Warning if non-numeric).
2. Read `design_classification` via `read-design-classification.sh` (defaults HARD on failure). Cap = 3 for SIMPLE, 5 for HARD.
3. If counter >= cap: print `**⚠ Step 3: review-round cap (<cap>) reached for <tier>; skipping panel and returning to Gate C.**`, skip `plan-review-loop.sh` entirely, jump to Step 3b/4/4b with existing artifacts. Gate C then offers only Approve / Discuss further (Re-run is hidden because cap is hit).
4. Otherwise increment the counter (count+1) and write it back; pass `--round-num "$count"` (the post-increment value) to `plan-review-loop.sh`.

Gate C still reads the counter to decide whether to hide the "Re-run review panel" option (counter >= cap → hide). But the Step 3 entry guard is the real enforcement so that Gate C → Discuss further → Gate A → "Ready for review" → Step 3 ALSO honors the cap.

**Per-tier emphasis text** (concrete wording, locked phrases for harness assertions):
- **SIMPLE (designer prose, Step 2b)**: "This is a SIMPLE-tier design. Bias the plan toward the **smallest change that achieves the goal**. Resist adding files, abstractions, refactors, or scope not strictly required by the feature description. If you find yourself writing more than the minimum, stop and prune. Prefer single-file edits to multi-file refactors. Prefer renaming over rewriting. Prefer leaving working code alone over polishing it."
- **HARD (designer prose, Step 2b)**: "This is a HARD-tier design. Bias the plan toward **thoroughness**. Surface all relevant edge cases, failure modes, and cross-cutting concerns; do not omit considerations to save effort. Address invariants, contract boundaries, and downstream consumers explicitly."
- **SIMPLE (reviewer prompt prefix, Step 3)**: "**Tier emphasis: SIMPLE.** Bias your findings toward flagging **scope creep and unnecessary complexity**. Do NOT request additions. Prefer EXONERATE on nits, style concerns, and forward-looking issues. Accept (YES) only when the fix is materially required for correctness. When in doubt, EXONERATE."
- **HARD (reviewer prompt prefix, Step 3)**: "**Tier emphasis: HARD.** Bias your findings toward **thoroughness**. Flag missed considerations, edge cases, and architectural concerns. Request additions when warranted. Engage seriously with all findings."
- **Tier-gate descriptions (Step 0b AskUserQuestion)**:
  - SIMPLE: "No upfront sketches, no dialectic. Full external review panel still runs. Designer + reviewers bias toward simplicity and minimum-change. Re-run cap: 3 total review runs."
  - HARD: "4 personality sketches + dialectic + full review panel. Designer + reviewers bias toward thoroughness. Re-run cap: 5 total review runs."

**Tier emphasis injection mechanics**: `render-plan-review-prompt.sh` emits the prompt body as `<role-line>\n<tier-emphasis>\n<rest-of-prompt>`. The dynamic-prompt assembly in `dispatch-plan-review-panel.sh` uses `tail -n +2` to strip the role line; with tier emphasis on line 2, it stays in the output. Static slots receive the full `role + tier + rest` body. **Renderer contract**: requires `DESIGN_TMPDIR` (set via env or `--design-tmpdir <path>` argv); on missing/invalid `run-params.json`, defaults to HARD emphasis and prints a single Warning to stderr.

**Schema v2 `run-params.json`** — final shape:
```json
{
  "schema_version": 2,
  "design_classification": "SIMPLE" | "HARD",
  "partition_requested": false,
  "brainstorm_requested": false
}
```

`write-run-params.sh` argv collapses to `--classification SIMPLE|HARD --output <path> [--partition-requested true|false] [--brainstorm-requested true|false]`. The `--reason`, `--source`, `--sketch-budget`, `--review-budget`, `--workflow-path` args are deleted.

## Files to modify/create

### NEW: `scripts/read-design-classification.sh`
Single canonical reader for `design_classification` from `$DESIGN_TMPDIR/run-params.json`. Same fallback pattern as the existing `read-design-review-budget.sh` (python3 → jq → grep). Returns `SIMPLE` or `HARD` on stdout; on any read failure, returns `HARD` to stdout and prints `**⚠ read-design-classification: <reason>; defaulting to HARD**` to stderr. Sibling: `read-design-classification.md`.

### UPDATED: `skills/design/SKILL.md`
Pre-Step-0: remove the `--trivial`+`--partition` mutual-exclusion block AND the `--trivial`+`--brainstorm` upgrade prompt; instead emit `**⚠ /design: --trivial flag removed; tier consolidation in #2956. Use --simple or --hard.**` and exit **1** unconditionally when `--trivial` is scanned. Remove the trivial row from the flag table. Update Step 0b sub-step 5 tier-gate `AskUserQuestion` to 2 options (SIMPLE / HARD) with the descriptions in this plan's Approach. Update sub-step 6 tier mapping to emit only `--classification SIMPLE|HARD` to `write-run-params.sh` (drop `--reason`, `--source`, `--sketch-budget`, `--review-budget`, `--workflow-path`). **Update the router-flag-persistence `jq` fallback block** (currently calls `write-run-params.sh` with all v1 flags) to use v2 argv only: `--classification HARD` (safe default) + `--partition-requested` + `--brainstorm-requested`. **Update sub-step 4(b)** (ad-hoc Q&A only path on already-planned re-entry): the branch must NOT call `write-run-params.sh` (no tier choice has been made); instead use a direct `jq` merge to ensure `brainstorm_requested: true` is present, preserving any existing fields, without re-writing the classification or schema_version. Update Step 2a opening prose to branch on `design_classification == SIMPLE | HARD` rather than `sketch_budget`. Delete the "Zero-sketch mode (`sketch_budget=0`)" / "Quick/simple mode (`sketch_budget=2`)" mode sections; replace with **SIMPLE branch** (skip sketches, write sentinel using `NO_SKETCHES_CLASSIFIED_SIMPLE`) and **HARD branch** (existing 4-personality launch). Delete Step 2a.3 "Quick mode" 2-output collection block. Update Step 2a.5 entry guard to branch on `design_classification == SIMPLE` (skip + breadcrumb) vs `HARD` (proceed). Update Step 2b validator dispatch to call `invoke-plan-validator.sh` (renamed) unconditionally. **Add the Step 3 entry guard** (counter read → cap check → short-circuit-or-increment) as a fenced Bash block at the top of Step 3; the existing Bash block that invokes `plan-review-loop.sh` consumes the `$count` integer via `--round-num "$count"`. Update Step 3 plan-review opening prose to delete the `review_budget=quick` branch entirely (full panel always runs). Delete Step 5d L3-velocity comment block in its entirety. Update Step 5c item 2 to call `invoke-plan-validator.sh`. Update the helper-contract `Plan helper contracts` list to drop `read-design-review-budget.sh` and `invoke-plan-validator-if-not-quick.sh`; add `read-design-classification.sh` and `invoke-plan-validator.sh`. Add per-tier designer-emphasis prose at the head of Step 2b (paragraph branches on `read-design-classification.sh` output). **Rewrite Anti-pattern #1** (NEVER skip sketches): "Skip sketches only when `design_classification == SIMPLE` (write `NO_SKETCHES_CLASSIFIED_SIMPLE` sentinel); HARD always runs 4 personality sketches. Why: anchoring bias still locks architectural direction; SIMPLE's no-sketch path is the user-confirmed minimum-change carve-out."

### UPDATED: `skills/design/references/flags.md`
Delete `--trivial` row from the public flags list and any mention in the mutual-exclusion / brainstorm-upgrade rules. Update the **Mutual exclusion** paragraph to drop the `--trivial`+`--partition` and `--trivial`+`--brainstorm` clauses. Update the **Plan-size thresholds** section to reference SIMPLE/HARD only. Delete the **Per-round velocity (deferred)** section entirely. Delete the **Plan-command validator (`review_budget` gating)** subsection; replace with: "Plan-command validator runs unconditionally on both SIMPLE and HARD after each successful `ACTION=EMIT_PLAN` on `plan.txt` and once on `composed-plan.md` in Step 5c."

### UPDATED: `skills/design/references/approval-gates.md`
Delete the `--trivial` mentions in the cross-tier invariant paragraph (sentence collapses to "Gates apply uniformly across `--simple` and `--hard`."). Delete the per-tier behavior bullet list under **Discussion sub-round body**. Add a new **Per-tier review-round cap** subsection: "Gate C reads `$DESIGN_TMPDIR/review-round-count.txt` (treat missing/empty/non-numeric as 0; log Warning if non-numeric) and `design_classification` via `read-design-classification.sh`. Cap: SIMPLE = 3, HARD = 5. When counter >= cap, the 'Re-run review panel' option is omitted from the Gate C `AskUserQuestion`; only Approve / Discuss further remain. Step 3 also enforces the cap at every entry (initial, Gate C re-run, Gate A 'Ready for review' post-discussion) and short-circuits to Gate C with a `**⚠ Step 3: review-round cap reached**` breadcrumb when counter >= cap. SKILL.md Step 3 is the sole writer of the counter; `plan-review-loop.sh` is stateless w.r.t. the file. Gate A 'Discuss more' loops remain uncapped." Update Gate B Apply-all/Per-finding sections to remove `review_budget` checks on validator call.

### UPDATED: `skills/design/references/sketch-launch.md`
Delete the **Quick Mode (`sketch_budget=2`)** section entirely. Rename **Zero-Sketch Mode (`sketch_budget=0`)** → **SIMPLE Mode** with branch trigger `design_classification == SIMPLE`. Replace the sentinel write with `NO_SKETCHES_CLASSIFIED_SIMPLE`. Rename **Regular Mode (`sketch_budget=4`)** → **HARD Mode**, branch trigger `design_classification == HARD`. Update the **Contract** paragraph to drop budget vocabulary; describe the SIMPLE/HARD branch.

### UPDATED: `skills/design/references/sketch-prompts.md`
Delete the `GENERIC_PROMPT` entry. Update the **Consumer** description to name only the four HARD personality slots (ARCH/EDGE/INNOVATION/PRAGMATIC).

### UPDATED: `skills/design/references/plan-review.md`
Update the **Consumer** line to say "Step 3 always runs the full panel via `plan-review-loop.sh`" (drop `review_budget=full` gating). Document the per-tier emphasis prefix injection: `render-plan-review-prompt.sh` reads `design_classification` and injects the SIMPLE-emphasis or HARD-emphasis text immediately after the role line (so `tail -n +2` in dynamic-prompt assembly preserves it). Existing reviewer focus areas (code-quality / risk-integration / correctness / architecture / security) unchanged.

### UPDATED: `skills/design/references/discussion-rounds.md`
Drop `review_budget` references in the post-plan sub-round body.

### UPDATED: `skills/design/scripts/render-plan-review-prompt.sh`
Add `--design-tmpdir <path>` argv option (alternative to env-exported `DESIGN_TMPDIR`). At minimum one path must be set. Use `read-design-classification.sh` to determine tier (defaults to HARD with stderr Warning on failure). Output ordering: `<role-line>\n<tier-emphasis>\n<rest-of-prompt>` so dynamic-prompt assembly's `tail -n +2` strips role only and preserves tier emphasis. Tier emphasis text matches the locked SIMPLE/HARD phrases in this plan's Approach.

### UPDATED: `skills/design/scripts/render-plan-review-prompt.md`
Document the new `--design-tmpdir` argv, the required environment contract, the tier-emphasis injection mechanics, and the HARD-fallback-with-Warning behavior on read failure.

### UPDATED: `skills/design/scripts/dispatch-plan-review-panel.sh`
Pass `--design-tmpdir "$DESIGN_TMPDIR"` to every `render-plan-review-prompt.sh` invocation (both static slots and the shared-tail/dynamic path). No env-export hack needed since the argv is now explicit.

### UPDATED: `skills/design/scripts/test-plan-review-prompt.sh`
Add fixtures that create v2 `run-params.json` with `design_classification: SIMPLE` and `design_classification: HARD` in two separate temp design-tmpdirs. Assert that the rendered SIMPLE prompt contains `Tier emphasis: SIMPLE` and `Bias your findings toward flagging` (locked substring); assert HARD contains `Tier emphasis: HARD` and `Bias your findings toward thoroughness`. Assert both static and dynamic rendered prompts contain the tier prefix exactly once.

### UPDATED: `skills/design/scripts/plan-review-loop.sh`
Drop any `review_budget` argv parsing / branching. Document via header comment that `--round-num` is a stateless integer input from the caller; the script does NOT read or write `review-round-count.txt`. Continue to emit `--round-num N` KV in artifact paths.

### UPDATED: `skills/design/scripts/plan-review-loop.md`
Drop `review_budget` mentions. Add explicit ownership statement: "Gate C owns cap enforcement; SKILL.md Step 3 owns counter incrementing and writes `$DESIGN_TMPDIR/review-round-count.txt`; `plan-review-loop.sh` is stateless and consumes the supplied `--round-num <int>` only for emitted KVs and round-N artifact paths." Add structural-coverage note: Step 3 must not pass `--round-num 1` unconditionally; supplied `--round-num 2` must produce round-2 artifact paths.

### UPDATED: `skills/design/scripts/design-driver.md`
Drop `review_budget` mentions.

### UPDATED: `skills/design/scripts/render-final-summary.sh`
**Remove the trivial branch entirely** — not just `workflow_path`/`quick_mode` reads. Use `read-design-classification.sh` to fetch the tier label for the summary; map SIMPLE → "SIMPLE (no sketches; full review)" and HARD → "HARD (4 sketches; full review)". No legacy "skipped (trivial)" path remains.

### UPDATED: `skills/design/scripts/test-render-final-summary.sh`
Update all fixture run-params.json to v2 shape. Drop assertions on `workflow_path`/`quick_mode` output lines. Add assertions on the SIMPLE/HARD summary labels.

### UPDATED: `skills/design/scripts/test-design-driver.sh`
Drop `TRIVIAL_DOC_ONLY` / `--trivial` / `sketch_budget`-keyed test cases. Update fixture `run-params.json` writes to the v2 shape. Update validator-dispatch tests to assert unconditional invocation.

### RENAMED: `skills/design/scripts/invoke-plan-validator-if-not-quick.sh` → `invoke-plan-validator.sh`
Body simplified: delete the `_review_budget` read and the `quick`-tier skip branch. Always pipes `ACTION=VALIDATE_PLAN_COMMANDS ARGS=--plan-file <PATH>` to `design-driver.sh`. Update sibling md.

### REWRITTEN: `scripts/write-run-params.sh`
Collapse argv to `--classification SIMPLE|HARD --output <path> [--partition-requested true|false] [--brainstorm-requested true|false]`. Delete `--reason`, `--source`, `--sketch-budget`, `--review-budget`, `--workflow-path` parsing and validation. Bump `schema_version` from 1 to 2. Emit only `schema_version`, `design_classification`, `partition_requested`, `brainstorm_requested`. Update `require_enum` to accept only `SIMPLE|HARD`. Update usage banner.

### UPDATED: `scripts/write-run-params.md`
Rewrite to document v2 schema, new argv, and the absence of derived fields.

### UPDATED: `scripts/test-write-run-params.sh`
Update test cases to v2 argv. Delete cases exercising `--sketch-budget`, `--review-budget`, `--workflow-path`, `--reason`, `--source`. Add an explicit "rejects `--classification TRIVIAL_DOC_ONLY`" case (asserts exit 2 with enum-violation stderr).

### UPDATED: `scripts/test-write-run-params.md`
Document new test-case structure and v2 schema expectations.

### UPDATED: `scripts/test-design-structure.sh`
Delete `--trivial` pin assertions (mutual-exclusion prose, upgrade prose). Delete `sketch_budget=0|2|4` / `review_budget` / `workflow_path` prose pins where they apply to design SKILL.md. **Update the YES↔EXONERATE anchor relocation**: pin only `plan-review.md` (since `plan-review-quick.md` is deleted). **Update the FINDING_2678 reference** (if any) to a surviving authority. Add new pins for SIMPLE/HARD branch prose in Step 2a, Anti-pattern #1 rewrite, per-tier emphasis locked phrases, Step 3 entry-guard cap-check prose, Gate C per-tier cap prose, the `NO_SKETCHES_CLASSIFIED_SIMPLE` sentinel string, the `read-design-classification.sh` reference. **Remove `test-read-design-review-budget-invoke` from `.PHONY` and `test-harnesses-12` shard.** **Remove the entire `test-read-design-review-budget-invoke` Makefile target block.**

### UPDATED: `scripts/test-design-structure.md`
Sibling-doc parity: rewrite to describe the new SIMPLE/HARD routing, `NO_SKETCHES_CLASSIFIED_SIMPLE` sentinel, unconditional review panel, the per-tier cap, and the removed quick-mode pins. Drop `sketch_budget` and quick-mode guidance.

### UPDATED: `Makefile`
Remove `test-read-design-review-budget-invoke` from `.PHONY` (line 4 area) and from the `test-harnesses-12` shard (line 67 area). Delete the `test-read-design-review-budget-invoke` target body (lines 406-407 area). No replacement target needed since the underlying script is deleted; the per-tier emphasis coverage lives in the updated `test-plan-review-prompt.sh` (already wired into its existing Makefile target).

### UPDATED: `agent-lint.toml`
Remove `skills/design/scripts/test-read-design-review-budget-invoke.sh` and `skills/design/scripts/test-read-design-review-budget-invoke.md` from the exclude list (the files no longer exist; no exclusion needed).

### UPDATED: `scripts/test-effort-prose.sh`
Remove `skills/design/references/plan-review-quick.md` from the FILES array; harness no longer scans the deleted prose source.

### UPDATED: `scripts/timing-ledger.sh`
Fallback chain for tier label: read `workflow_path` first (preserves /implement run analysis unchanged); if absent, read `design_classification`; map values 1:1. Reuse the existing `python3 → jq → grep` fallback pattern. No CLI output renaming.

### UPDATED: `scripts/timing-report.sh`
Same fallback chain: `workflow_path` → `design_classification`. No output rename.

### UPDATED: `scripts/timing-report.md`
Document the fallback chain.

### UPDATED: `scripts/test-timing-report.sh`
Add fixture cases for v2 run-params (design_classification only, no workflow_path) to confirm fallback works.

### UPDATED: `scripts/test-refresh-run-logs.sh`
Update fixture run-params.json files to v2 shape where they exercise design runs.

### UPDATED: `skills/report-tokens/scripts/run-analysis.sh`
Same fallback chain: `workflow_path` → `design_classification`. No CLI output rename.

### UPDATED: `skills/report-tokens/scripts/run-analysis.md`
Document fallback chain.

### UPDATED: `skills/shared/topology.tsv`
Remove rows keying on `quick_mode` or `sketch_budget=2`. Keep HARD's `design.sketch.regular_slots` row; add or update a `design.sketch.simple_slots` row with value 0.

### UPDATED: `docs/skills.md`
Drop `--trivial` from `/design` argument-hint. Update per-tier description to name SIMPLE/HARD only.

### UPDATED: `docs/workflow-lifecycle.md`
Drop `--trivial`. Update per-tier description.

### UPDATED: `docs/issue-anchored-plan.md`
Drop `--trivial` mentions.

### UPDATED: `docs/review-agents.md`
Drop `quick_mode` mentions; state both tiers run full review.

### UPDATED: `docs/topology.md`
Drop `quick_mode` mentions. Regenerate design.sketch counts (HARD=4 slots, SIMPLE=0).

### UPDATED: `docs/collaborative-sketches.md`
Update `NO_SKETCHES_CLASSIFIED_TRIVIAL` → `NO_SKETCHES_CLASSIFIED_SIMPLE`. Drop quick-mode description; keep SIMPLE (no sketches) and HARD (4 personality sketches).

### UPDATED: `docs/linting.md`
Drop `sketch_budget`, `review_budget` mentions. Update or delete row 217 (formerly the test-read-design-review-budget-invoke harness entry). Add row for the renamed `invoke-plan-validator.sh` coverage if appropriate.

### UPDATED: `docs/voting-process.md`
Remove `--quick` plan-review prose and any link to deleted `plan-review-quick.md`. State `/design` plan review always uses the 3-voter (Claude + Codex + Cursor) panel for SIMPLE and HARD.

### UPDATED: `.claude/rules/topology-generation.md`
Remove `skills/design/references/plan-review-quick.md` from the input-path list.

### UPDATED: `SECURITY.md`
Update the `/design` external-delegation paragraph to describe: SIMPLE = 0 external sketch slots + full plan review panel; HARD = 4 external sketch slots + full plan review panel; both tiers use the 3-judge voting panel.

### UPDATED: `README.md`
Update `/design` argument-hint to drop `--trivial`. Update prose mentioning the three-tier model to two-tier.

### UPDATED: `.claude-plugin/plugin.json`
Update the `/design` description to remove `--trivial` and three-tier prose. Replace with the two-tier (SIMPLE/HARD) description.

### DELETED: `skills/design/references/plan-review-quick.md`
No tier uses the Claude-only quick review path anymore.

### DELETED: `skills/design/references/l3-velocity-deferral-comment.txt`
Step 5d block deletion makes this file dead.

### DELETED: `skills/design/scripts/read-design-review-budget.sh`
No field to read.

### DELETED: `skills/design/scripts/test-read-design-review-budget-invoke.sh`
Target script deleted.

### DELETED: `skills/design/scripts/test-read-design-review-budget-invoke.md`
Target test deleted.

## Edge cases

- **`/design --trivial 2956`** — Pre-Step-0 emits `**⚠ /design: --trivial flag removed; tier consolidation in #2956. Use --simple or --hard.**` and exits 1 before `session-setup.sh`.
- **v1 `run-params.json` mid-flight** — `/design` sessions started pre-this-PR have v1 shape. The new `read-design-classification.sh` won't find `design_classification`; falls back to HARD with Warning. Acceptable per no-compat directive.
- **`$DESIGN_TMPDIR/review-round-count.txt` missing on Step 3 entry** — treated as count 0; counter is created at increment time.
- **`$DESIGN_TMPDIR/review-round-count.txt` corrupt (non-numeric, empty)** — same as missing; log a single Warning, treat as 0.
- **`design_classification` missing or unrecognized in `run-params.json`** — `read-design-classification.sh` defaults to HARD with stderr Warning. Safer default (more iteration headroom).
- **Step 3 entry when counter >= cap** — short-circuit print + jump to Step 3b/4/4b with existing artifacts. Subsequent Gate C only offers Approve / Discuss further; Discuss further → Gate A → "Ready for review" again hits the cap guard and short-circuits without re-running panel.
- **`--brainstorm` with new SIMPLE** — unchanged; Step 1d.5 runs regardless of tier.
- **Operator picks SIMPLE expecting old TRIVIAL runtime** — tier-gate description explicitly says "Full external review panel still runs"; informed choice.
- **`timing-ledger.sh` reads v2 design run-params** — `workflow_path` absent, falls back to `design_classification`. /implement runs unaffected (their run-params still write `workflow_path`).
- **Step 0b sub-step 4(b) early brainstorm Q&A path** — branch uses direct `jq` merge to set `brainstorm_requested: true` without re-writing classification or invoking `write-run-params.sh`. No tier value is forced before the user actually picks one.

## Failure modes

1. **Tier emphasis lost on dynamic reviewer slots** — if the renderer outputs role on line 1 but the dynamic-prompt assembly's `tail -n +2` is changed to `tail -n +3` (or the layout changes), the tier prefix could be stripped. **Warning signal**: voting tallies show dynamic-slot finding bias diverging from static slots; harness test catches "Tier emphasis:" absent in dynamic prompts. **Mitigation**: `test-plan-review-prompt.sh` asserts both static and dynamic prompts contain `Tier emphasis: <TIER>` exactly once.

2. **Cap counter desync** — if `plan-review-loop.sh` is ever modified to read or write `review-round-count.txt`, double-counting or stale-counter behavior emerges. **Warning signal**: round-N artifact files appear out of order; counter ratchets past cap silently. **Mitigation**: `plan-review-loop.md` explicit ownership contract; structural-test pin in `test-design-structure.sh` asserts `plan-review-loop.sh` does NOT grep for `review-round-count.txt`.

3. **Timing-ledger fallback regression** — if the fallback chain in `timing-ledger.sh` is implemented as exclusive (only `design_classification`) rather than preferential (workflow_path first, then design_classification), /implement run analysis breaks. **Warning signal**: implement runs show empty workflow_path column in reports. **Mitigation**: `test-timing-report.sh` fixture covers both /implement run-params (with workflow_path) and /design run-params (without). Assert label populated in both cases.

## Testing strategy

- **Unit**: `skills/design/scripts/test-design-driver.sh`, `scripts/test-write-run-params.sh`, `skills/design/scripts/test-render-final-summary.sh`, `scripts/test-timing-report.sh`, `skills/design/scripts/test-plan-review-prompt.sh` updated for v2 fixtures. Explicit "rejects `--classification TRIVIAL_DOC_ONLY`" assertion in `test-write-run-params.sh`. Per-tier locked-phrase substring assertions in `test-plan-review-prompt.sh`.
- **Structural**: `scripts/test-design-structure.sh` pins updated for new SIMPLE/HARD branches in Step 2a, Anti-pattern #1 rewrite, Step 3 entry-guard cap-check prose, Gate C per-tier cap prose, `NO_SKETCHES_CLASSIFIED_SIMPLE` sentinel pin, `read-design-classification.sh` reference, Pre-Step-0 hard-error prose. Stateless-`--round-num` pin: assert `plan-review-loop.sh` does not grep `review-round-count.txt`.
- **Repo-wide lint**: `make lint` and `bash scripts/relevant-checks.sh` must pass.
- **Delete-completeness**: `make lint-link-checker` (or equivalent) confirms no surviving cross-refs to deleted files (`plan-review-quick.md`, `l3-velocity-deferral-comment.txt`, `read-design-review-budget.sh`, `test-read-design-review-budget-invoke.{sh,md}`).
- **Smoke-runnable**: `/design --simple <fixture-issue>` and `/design --hard <fixture-issue>` runs end-to-end on a fixture issue. Verify (a) v2 run-params.json, (b) Step 2a sketches skipped in SIMPLE / launched in HARD, (c) Step 3 always runs full panel, (d) `review-round-count.txt` increments on each Step 3 entry, (e) Gate C hides "Re-run review panel" after per-tier cap, (f) Step 3 entry guard short-circuits at cap.

diff_lines: 1300


## Acceptance

- `/design --trivial <anything>` exits non-zero with the documented error message before any session-setup.sh side effect.
- `/design --simple <issue-N>` and `/design --hard <issue-N>` complete end-to-end on a fixture issue without referencing TRIVIAL_DOC_ONLY, --trivial, quick_mode, sketch_budget=0|2, review_budget, or workflow_path in any orchestrator output.
- `run-params.json` written by /design has exactly the v2 shape (schema_version: 2; design_classification, partition_requested, brainstorm_requested only) — no legacy fields, no `null` placeholders.
- `scripts/read-design-classification.sh` exists and returns SIMPLE or HARD on stdout, with HARD-fallback + stderr Warning on read failure; sibling .md present.
- `skills/design/references/plan-review-quick.md`, `skills/design/references/l3-velocity-deferral-comment.txt`, `skills/design/scripts/read-design-review-budget.sh`, and `skills/design/scripts/test-read-design-review-budget-invoke.{sh,md}` no longer exist in the repo.
- `skills/design/scripts/invoke-plan-validator.sh` exists (renamed from `invoke-plan-validator-if-not-quick.sh`); the rename target does NOT exist; validator runs unconditionally on both tiers.
- `make lint` and `bash scripts/relevant-checks.sh` pass on the rewritten branch.
- `scripts/test-design-structure.sh` pins assert the new SIMPLE/HARD branches in Step 2a, Anti-pattern #1 rewrite, Pre-Step-0 hard-error prose, Step 3 entry-guard cap-check prose, Gate C per-tier cap prose, `NO_SKETCHES_CLASSIFIED_SIMPLE` sentinel.
- `scripts/test-write-run-params.sh` has a case asserting `--classification TRIVIAL_DOC_ONLY` is rejected with exit 2.
- `skills/design/scripts/test-plan-review-prompt.sh` has fixtures for SIMPLE and HARD v2 run-params; asserts `Tier emphasis: SIMPLE` + `Bias your findings toward flagging` (locked substring) in SIMPLE prompts and `Tier emphasis: HARD` + `Bias your findings toward thoroughness` in HARD prompts; asserts both static and dynamic prompts contain the prefix exactly once.
- `scripts/timing-ledger.sh`, `scripts/timing-report.sh`, and `skills/report-tokens/scripts/run-analysis.sh` read `workflow_path` first then fall back to `design_classification`. `scripts/test-timing-report.sh` fixtures cover both shapes.
- `Makefile` has no `test-read-design-review-budget-invoke` target / `.PHONY` entry / shard membership.
- `agent-lint.toml` does not list the deleted test files in any exclude list.
- `scripts/test-effort-prose.sh` FILES array does not contain `plan-review-quick.md`.
- All docs (`README.md`, `docs/skills.md`, `docs/workflow-lifecycle.md`, `docs/issue-anchored-plan.md`, `docs/review-agents.md`, `docs/topology.md`, `docs/collaborative-sketches.md`, `docs/linting.md`, `docs/voting-process.md`, `.claude-plugin/plugin.json`, `SECURITY.md`, `.claude/rules/topology-generation.md`) and shared (`skills/shared/topology.tsv`) reflect the two-tier SIMPLE/HARD model with no `--trivial` / `quick_mode` / `plan-review-quick.md` references.

diff_lines: 1300

## Test plan
(no test plan section in plan-file)
