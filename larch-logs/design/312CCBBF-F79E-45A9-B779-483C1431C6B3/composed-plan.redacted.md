## Plan

# Implementation Plan — Rigid summary template for /design + /implement cost-line consolidation (#2714)

## Approach

Bring `/design` end-of-run output to parity with `/implement` by reusing `scripts/render-run-summary.sh` with a new `--skill design` schema branch. Both skills emit the dollar-primary cost line in exactly one place — the rendered `larch:final-summary` body — and nowhere else (in chat, in committed log batches, or in `token-report.sh --summary` output).

Round 1 decisions are normative inputs:
- Reuse marker `<!-- larch:final-summary v1 runid=<R> -->` (different `runid=...` segments keep /design and /implement comments distinct on the same tracking issue).
- Emit the rendered summary on ALL post–Step-0a exits in /design. Pre–Step-0a aborts (session-setup failure, tier-flag mutex collision) skip the renderer because `$DESIGN_TMPDIR` doesn't yet exist.
- Both skills go terse: rendered summary block + machine footer; no `token-report.sh --summary` / `timing-report.sh --summary` chat-tail prints; no `LARCH_VERBOSE_TOKENS=true --full --markdown` branch in chat.

**Single chat-side emission invariant** (FINDING_1): the rendered summary block is printed in chat EXACTLY once per run. For `/implement`, only Step 17 prints the body to chat via `write-final-report.sh --print-stdout`; Step 18's `write-final-report.sh` refresh call omits `--print-stdout` so the GitHub upsert and log refresh happen silently. The `scripts/test-implement-structure.sh:242-249` harness that currently PINS Step 18 to retain `--print-stdout` is rewritten to assert the opposite (Step 18 must NOT use `--print-stdout`).

**Upsert vs publish/rename gate decoupling** (FINDING_2): the `tracking-issue-summary.sh upsert-summary` call runs whenever `ISSUE_NUMBER` is non-empty AND the rendered body is non-empty — independent of `PLAN_WRITE_OK`. The `PLAN_WRITE_OK` flag gates ONLY `design-log-publish.sh` invocation and the `[DESIGNED]` rename (which are happy-path-only by design). Explicit exclusions to upsert: Split-path (preserves `$DESIGN_TMPDIR`) and pre-Step-0a aborts (`$DESIGN_TMPDIR` doesn't exist). The matrix is documented in the helper's sibling `.md` and referenced from SKILL.md prose.

Sketch synthesis (`approach-synthesis.txt`) narrowed the consolidation surface meaningfully: `timing-report.sh --summary` emits elapsed/vendor-task counts only with NO dollar line, so it is NOT a duplication site — only `token-report.sh --summary` is. Round 1 Decision 6 also requires stripping the dollar line from `token-report.sh --summary` itself; FINDING_3 mandates a replacement non-cost emit (`Tokens: <N>k` + per-vendor token counts) so the success branch is not silently empty after the dollar line is removed.

`scripts/render-cost-line.sh` becomes a standalone helper with no in-tree callers after consolidation. We keep it (and its harnesses) intact rather than deleting — operators can still invoke it manually for cost-only queries — but the cross-skill grep test asserts zero `render-cost-line.sh` matches in `skills/**` and only its own file + harnesses in `scripts/`. This is a minor (justified) relaxation of the issue body's literal acceptance text ("render-run-summary.sh as the new sole caller"). The behavioral invariant ("one cost line per run, owned by the rendered summary block") is preserved either way.

## Outcome string enumeration (normative)

Outcome strings passed to `render-run-summary.sh --outcome` for /design runs:

- `approved` — happy path (Gate C approved, plan written, [DESIGNED] rename)
- `cancelled-clarify` — Step 0b sub-step 3 clarify-loop exit (after clarify response posted, before tier gate)
- `cancelled-already-planned` — Step 0b sub-step 4 (c) already-planned router cancel (FINDING_16)
- `cancelled-tier-gate` — Step 0b sub-step 5 tier gate Other → exit 0
- `cancelled-sprawl` — Step 1c / Step 1d semantic-sprawl heuristic Cancel (FINDING_10)
- `cancelled-plan-size-hard` — Step 2b.5 hard-trigger Cancel
- `failed-plan-write` — Step 5c `plan-block-write.sh` failure

Outcomes intentionally NOT in the enumeration:
- `cancelled-plan-size-soft` / `cancelled-plan-size-soft-partition` / `cancelled-plan-size-soft-semantic` — Step 2b.5 soft branch offers only Split / Continue (no Cancel option exists today, per `references/approval-gates.md`). The cost-line consolidation PR does NOT add a Cancel option to the soft prompt — scope safety per FINDING_11 option (a). The outcome enumeration is closed; if a future PR adds soft Cancel, that PR adds the outcome string at the same time.
- `cancelled-plan-size-split` — Split-path deliberately preserves `$DESIGN_TMPDIR` for operator re-run and does NOT call the renderer; Split-path is an exclusion to the "emit on all post-Step-0a exits" rule per FINDING_19. The outcome string is removed from the enumeration entirely.
- Gate C "Other" branch — non-terminal per `references/approval-gates.md` (re-prompts, never exits); no outcome assigned. Not a post-Step-0a exit at all.

The `case "$OUTCOME" in` pattern in `render-run-summary.sh` is extended to `bailed*|stalled|cancelled-*|failed-*) printf -- '- **Outcome**: %s\n' "$OUTCOME" ;;` so the Outcome bullet fires for every /design outcome except `approved` (mirrors /implement's hide-on-happy-path).

## Files to modify/create

### NEW: `skills/design/scripts/render-final-summary.sh`

Bash dispatcher invoked from /design's `### Final summary block` (replaces the legacy `### Terminal cost line` block). Inputs: `$DESIGN_TMPDIR`, `$ISSUE_NUMBER`, `$SESSION_ID`, `--outcome <string>`, `--mode <string>`, `--repo <owner/repo>` (optional). Behavior:

1. Read `$DESIGN_TMPDIR/run-params.json` for `workflow_path` (becomes renderer `--workflow-path`); fall back to `unknown` if absent.
2. Run `token-report.sh --full --format json --output "$DESIGN_TMPDIR/token-report-final.json" 2>"$DESIGN_TMPDIR/token-report-final.stderr.log"` (best-effort; non-zero exit captured, never blocks).
3. Run `timing-report.sh --full --format json --output "$DESIGN_TMPDIR/timing-report-final.json" 2>"$DESIGN_TMPDIR/timing-report-final.stderr.log"` (best-effort) — uses the same `LARCH_TIMING_LEDGER` and `LARCH_TIMING_SKILL=design` session env contract as other design timing calls (FINDING_6). Parse `total_hms` via `jq` (same field name `write-final-report.sh:188-190` uses) → renderer `--duration`. When the JSON is missing or jq fails, pass empty `--duration` so the renderer emits `- **Duration**: N/A`.
4. Parse claude/codex/cursor per-bucket token counts from `token-report-final.json` via `jq`. **Cost-unavailable signal** (FINDING_12): when the JSON is missing, unparseable, or all per-bucket counts are zero AND `token-report-final.stderr.log` is non-empty, pass NO `--claude-*` / `--codex-*` / `--cursor-*` / `--*-tokens` arguments. The renderer's empty-cost path then emits `- **Cost**: N/A` (rather than the misleading `$0.00` that `token-cost.sh` returns for all-zero inputs). When zero counts come from a successful but empty run (e.g., trivial Claude-only), pass the explicit zero values — those produce `$0.00` legitimately.
5. **Counting algorithm for `--exec-issues` and `--warnings`** (FINDING_13): use `grep -c '^\*\*Step ' "$DESIGN_TMPDIR/execution-issues.md"` for the total `Step` entry count; partition into the two integer counts by reading the next-non-blank line after each `^### ` section header (current values: `### Tool Failures`, `### External Reviewer Issues`, `### Warnings`). Tool failures + External reviewer issues collapse into `--exec-issues`; the `### Warnings` section contributes to `--warnings`. When `execution-issues.md` is missing or empty, both counts are `0`. Document the rule in `render-final-summary.md`.
6. Compose `--plan-review-line` from `$DESIGN_TMPDIR/voting-tally.md`: count accepted FINDING_N + OOS_N rows, format as `N accepted (X critical / Y high / Z medium / W low)`. When the tally file is missing (Trivial tier, no panel ran), emit `skipped (trivial)`. When zero findings, emit `0 findings`. Compose `--oos-count` and `--oos-urls` from `$DESIGN_TMPDIR/oos-issues-created.md` after Step 5b (URLs are absent on early exits).

7. **Two-phase render** (FINDING_7):
   - **Phase 1 (pre-publish)**: Invoke `${CLAUDE_PLUGIN_ROOT}/scripts/render-run-summary.sh --skill design ... --output-file "$DESIGN_TMPDIR/final-summary.md"` (NO `--print-stdout`, NO upsert). Local file only. This lets `design-log-publish.sh` enumerate `$DESIGN_TMPDIR` and include the file in the committed `larch-logs/design/<RUN_ID>/`.
   - **Phase 2 (post-publish)**: After `design-log-publish.sh` runs (whether success or failure → updated `Warnings` count + accurate `Run logs` path), RE-RENDER with current state, THEN `--print-stdout` to chat AND (when `ISSUE_NUMBER` is non-empty and the body is non-empty) call `${CLAUDE_PLUGIN_ROOT}/scripts/tracking-issue-summary.sh upsert-summary --issue $ISSUE_NUMBER --marker "<!-- larch:final-summary v1 runid=$SESSION_ID -->" --content-file "$DESIGN_TMPDIR/final-summary.md" ${REPO:+--repo "$REPO"}` (best-effort, capture stderr to a failure log and append under `Warnings` on non-zero exit). The Phase 1 file may be overwritten by Phase 2.
   - **Exit paths that skip publish entirely** (clarify, plan-size cancel, failed-plan-write, already-planned cancel, sprawl-cancel, tier-gate-cancel): Phase 1 is skipped; only Phase 2 runs (single render → print + upsert). These paths have no `larch-logs/design/<RUN_ID>/` commit anyway.

8. **Encapsulation invariant** (FINDING_14): The helper INTERNALLY owns the `tracking-issue-summary.sh upsert-summary` call. SKILL.md prose mentions only `render-final-summary.sh`; it does NOT cross-reference `tracking-issue-summary.sh` separately. The `test-design-structure.sh` anchor (Check 15 successor) asserts only the `render-final-summary.sh` invocation in Step 5 — not a second `tracking-issue-summary.sh` string match.

Sibling: `skills/design/scripts/render-final-summary.md` documenting purpose, the seven callers (Step 0b sub-step 3 clarify, sub-step 4 (c) already-planned cancel, sub-step 5 tier-gate cancel, Step 1c/1d sprawl cancel, Step 2b.5 hard cancel, Step 5 finalize happy, Step 5c failed-plan-write), the two-phase ordering, the cost-unavailable signal, the exec-issues/warnings counting rule, the upsert gate (issue-bound only, decoupled from `PLAN_WRITE_OK`), and the Split-path / pre-Step-0a exclusions.

### NEW: `skills/design/scripts/test-render-final-summary.sh`

Hermetic harness:
- `--outcome approved` happy path: byte-aligned stdout vs file via `cmp -s` (FINDING_20), all bullets populated.
- `--outcome cancelled-clarify` and `--outcome failed-plan-write`: `- **Outcome**:` line present.
- `--outcome cancelled-already-planned` and `--outcome cancelled-sprawl`: same Outcome bullet behavior.
- `--mode --trivial` → `Plan review: skipped (trivial)`.
- No `tracking-issue-summary.sh` call when `$ISSUE_NUMBER` is empty.
- `token-report-final.json` missing → `- **Cost**: N/A` (FINDING_12), not `$0.00`.
- `timing-report-final.json` missing → `- **Duration**: N/A` (FINDING_6).
- Two-phase ordering: when `design-log-publish.sh` is mocked to fail, Phase 2 re-renders with updated Warnings count (FINDING_7).
- Counting fixtures: `execution-issues.md` with mixed Tool Failures / Warnings sections produces correct integers (FINDING_13).
- Sentinel `<!-- larch:run-summary v=1 -->` present at end of body.
- Negative: `render-final-summary.sh --outcome cancelled-plan-size-soft` produces a clear error (outcome not in enumeration — FINDING_11 scope-safe).

Sibling: `skills/design/scripts/test-render-final-summary.md`.

### UPDATED: `scripts/render-run-summary.sh`

1. Extend argv validation at line 104 from `case "$SKILL" in implement) ;; *) usage; exit 2 ;; esac` to `case "$SKILL" in implement|design) ;; *) usage; exit 2 ;; esac`.
2. Update `usage()` at lines 28-29 (FINDING_8) to list both skills, e.g. `Usage: render-run-summary.sh --skill {implement|design} ... (see render-run-summary.md)`.
3. Add a conditional schema branch keyed on `$SKILL`:
   - For `design`: SKIP the `- **Code review**:` printf at line ~225 (use `[ "$SKILL" = design ] || printf …`).
   - For `design`: SKIP `- **PR**:` unconditionally (extend the existing PR-N/A conditional to also short-circuit when `$SKILL = design`).
   - For `design`: emit the `- **Plan review**:` line as today.
4. **Outcome conditional extension**: change line 215's `case "$OUTCOME" in bailed*|stalled)` to `case "$OUTCOME" in bailed*|stalled|cancelled-*|failed-*)` so the Outcome bullet fires for every /design intermediate-exit outcome AND remains absent for `approved` (no `approved` match in the pattern).
5. Verify and document (in code comments) that field suppression for `--skill design` is a skipped printf — NOT an empty-string emission — so the byte-aligned invariant between `--print-stdout` and `--output-file` content holds (FINDING_20).

### UPDATED: `scripts/render-run-summary.md`

1. Document `--skill design` mode with the full schema field list (PR + Code review hidden for design; Plan review + OOS filed + Exec issues + Warnings preserved).
2. Add "single-source dollar-line invariant" note: this renderer's `- **Cost**:` bullet is the sole authoritative emission of the dollar-primary cost line for both `/implement` and `/design`. Neither SKILL.md, nor `token-report.sh --summary`, nor `timing-report.sh --summary` may emit this line independently.
3. Update the byte-alignment invariant note to require `cmp -s` byte identity (FINDING_20) — not "no trailing whitespace divergence". Cover both skills' `<skill>/<run-id>/final-summary.md` projection vs the GitHub upsert payload.
4. Outcome strings table: list `/implement` outcomes (bailed*, stalled, plus new cancelled-*/failed-* support) and the /design outcomes from the enumeration above (FINDING_10, FINDING_11, FINDING_16, FINDING_19). Explicitly note `approved` does NOT trigger the Outcome bullet.

### UPDATED: `scripts/token-report.sh`

1. **Strip dollar line from `--summary`** AND `--full --markdown`: remove the `larch_emit_cost_line` call and the subsequent `emit "$_cost_ln"` at line 743-745.
2. Remove `💰 Cost: N/A — token-cost unavailable` fallback at line 731. Replace with a plain `Tokens: %sk` emit using the existing `$tok_k` value.
3. **Add a replacement non-cost summary emit on success** (FINDING_3): after stripping the dollar line, emit `Tokens: <N>k` (total tokens) plus per-vendor token counts in a stable format (e.g., `Claude: <N>k | Codex: <M>k | Cursor: <P>k`). The format is whatever the harness pins; the goal is non-empty, non-dollar-bearing summary output for direct invocations.
4. Inspect `--full --markdown` rendering path: confirm no rolled-up dollar line exists in the jq `markdown()` branch (FINDING_17 from cursor-edge — likely a no-op; verify-only). Add a regression assertion in `scripts/test-token-report.sh` that `--full --markdown` output contains no `💰 Cost:` literal.

### UPDATED: `scripts/test-token-report-summary-format.sh`

Invert dollar-line assertions:
1. Assertions that previously required `💰 Cost: ` in `--summary` output → assert ABSENT.
2. Add positive assertion that the new replacement Tokens line is present (FINDING_3).
3. Same treatment for `--full --markdown`.

### UPDATED: `scripts/test-token-report.sh` (FINDING_4)

1. Update Cases 1 and 2 (and any other dollar-line assertions at lines 516-534) to assert (a) ABSENCE of the dollar-primary cost line in `--summary` output, and (b) PRESENCE of the new non-cost Tokens summary line (matching the contract from FINDING_3).
2. Update sibling `scripts/test-token-report.md` to document the new assertions.

### UPDATED: `scripts/test-render-cost-line-callsites.sh`

Replace existing callsite assertions:
1. `grep -rln 'render-cost-line.sh' skills/` returns ZERO matches.
2. `grep -rln 'render-cost-line.sh' scripts/` matches ONLY: own file (+ .md), test-render-cost-line*.sh (+ .md), test-render-cost-line-callsites.sh (+ .md), test-render-cost-line-realism.sh (+ .md), AND the sibling docs being updated in FINDING_15 (`scripts/token-report.md`, `scripts/token-cost.md` — only if they retain references; per FINDING_15 they should NOT reference `render-cost-line.sh` going forward, so update the allowlist accordingly).
3. Additionally assert `scripts/token-report.sh` does NOT emit `💰 Cost: ` literal in its `--summary` or `--full --markdown` paths.

### UPDATED: `scripts/test-render-run-summary.sh`

Add a `--skill design` cohort:
1. Happy `--outcome approved`: body contains `## /design run …`, `- **Cost**:`, `- **Plan review**:`, `- **OOS filed**:`, `<!-- larch:run-summary v=1 -->`. Does NOT contain `- **PR**:` or `- **Code review**:`. Does NOT contain `- **Outcome**:`.
2. `--outcome cancelled-clarify`, `--outcome failed-plan-write`, `--outcome cancelled-already-planned`, `--outcome cancelled-sprawl`, `--outcome cancelled-tier-gate`, `--outcome cancelled-plan-size-hard`: each shows `- **Outcome**: <string>`.
3. **Byte-identity check via `cmp -s`** (FINDING_20): when `--output-file` and `--print-stdout` are both set, the stdout body equals the file content byte-for-byte (no whitespace pre-processing).
4. `--skill foo` rejected with exit 2.

### UPDATED: `scripts/test-render-run-summary-callsites.sh`

Extend (FINDING_20 sub-point from cursor-byte-alignment): assert that any new caller of `render-run-summary.sh` invokes it with the full per-bucket argv shape (no missing `--*-input-tokens` / `--*-output-tokens` flags) — the `render-final-summary.sh` wrapper's invocation must match the shape `write-final-report.sh` uses for /implement.

### UPDATED: `scripts/test-design-structure.sh` (FINDING_5)

1. Replace Check 15 (lines 373-401): retarget the 45-55-line pairing windows from `### Terminal cost line` / `render-cost-line.sh` to `### Final summary block` / `render-final-summary.sh`. Preserve the pairing-distance intent (banner-anchor co-location around cancel/footer markers).
2. Add positive anchor: Step 5 finalize body MUST invoke `render-final-summary.sh` (via the new banner-fenced block).
3. **Negative assertions** (FINDING_14 encapsulation): the anchor asserts ONLY `render-final-summary.sh` is referenced in Step 5. It does NOT additionally require `tracking-issue-summary.sh` in Step 5 — the helper encapsulates upsert.
4. Negative: `skills/design/**` (SKILL.md, references/*, scripts/*) MUST NOT contain `render-cost-line.sh` references.
5. Negative: `skills/design/SKILL.md` MUST NOT contain `token-report.sh --summary` or `timing-report.sh --summary` invocations (single emission rule).
6. Rename the regression anchor comment from `design-cost-line-anchor` to `design-final-summary-anchor` and update the sibling `scripts/test-design-structure.md`.

### UPDATED: `scripts/test-implement-structure.sh` (FINDING_1)

Update lines 242-249 (and any related anchors): the harness currently PINS Step 18 to retain `write-final-report.sh --print-stdout`. Invert this: assert Step 18's `write-final-report.sh` invocation does NOT include `--print-stdout` (silent refresh only). Update the sibling `scripts/test-implement-structure.md` accordingly.

### UPDATED: `skills/design/SKILL.md`

1. **Replace the `### Terminal cost line` block** (lines 243-275) with a new `### Final summary block` fenced bash block invoking `skills/design/scripts/render-final-summary.sh --outcome <outcome> --mode <mode-string>` (helper reads everything else from `$DESIGN_TMPDIR` and `run-params.json`).
2. **Add the canonical foreground banner** above the new opening ```bash fence (FINDING_18 — the current block has no banner today; this is an ADD, not a "remains"): `**⚠ Foreground required — do NOT set \`run_in_background: true\`.**`. Add `# Foreground required: see BASH_AUTHORING.md §4` within five in-fence lines above the `render-final-summary.sh` anchor.
3. **Update every callsite** to reference `### Final summary block` instead of `### Terminal cost line`:
   - Step 0b sub-step 3 clarify-loop exit (after clarify response posted) → `--outcome cancelled-clarify`.
   - Step 0b sub-step 4 (c) **already-planned cancel** (FINDING_16, currently at line 188) → `--outcome cancelled-already-planned`.
   - Step 0b sub-step 5 tier-gate Other → `--outcome cancelled-tier-gate`.
   - Step 1c / Step 1d **semantic-sprawl Cancel** (FINDING_10, current callsites in SKILL.md:592-600 routing through Terminal cost line via `references/discussion-rounds.md`) → `--outcome cancelled-sprawl`.
   - Step 2b.5 hard-trigger Cancel → `--outcome cancelled-plan-size-hard`.
   - **Step 2b.5 soft / partition-soft / semantic-soft branches**: NO Cancel option exists today; the soft `AskUserQuestion` retains Split / Continue only (FINDING_11). The new Final summary block is NOT invoked from the soft branch — Continue proceeds to Step 3, Split runs the existing Split-path which preserves `$DESIGN_TMPDIR` and exits 1 without rendering (FINDING_19).
   - **Step 2b.5 Split-path** (FINDING_19): preserves `$DESIGN_TMPDIR`, does NOT invoke the Final summary block (deliberate exclusion to "emit on all post-Step-0a exits"). Document this explicitly in the Split-path prose.
   - Step 5 finalize happy path (`PLAN_WRITE_OK=true`) → `--outcome approved`.
   - Step 5c plan-block-write failure (`PLAN_WRITE_OK=false`) → `--outcome failed-plan-write`.
   - Gate C "Other" branch — non-terminal per `references/approval-gates.md`; NO Final summary block invocation (re-prompts only).

4. **Step 5c ordering** (FINDING_7): two-phase render — render to `$DESIGN_TMPDIR/final-summary.md` BEFORE `design-log-publish.sh` (no print, no upsert); after publish (success or failure → Warnings updated), re-render → print stdout AND upsert (when ISSUE_NUMBER + non-empty body). The helper handles both phases internally; SKILL.md prose describes the order at the conceptual level. Adjust Step 5c flow: helper Phase 1 → `design-log-publish.sh` → helper Phase 2 → `[DESIGNED]` rename (only when PLAN_WRITE_OK=true AND PUBLISH_OK=true). For non-happy-path exits where publish is skipped, helper runs Phase 2 only (single render + print + upsert; no Phase 1 file is needed because no log commit happens).

5. **Remove the bare `render-cost-line.sh` invocation** from the (now-removed) Terminal cost line block.

6. **Remove the `**⚠ /design: token report unavailable; cost line suppressed**` fallback prose** — the helper handles token-report failure internally with cost-unavailable signaling (FINDING_12).

7. **Rewrite the "Do NOT write any farewell message …" admonition** at line 956 (FINDING_9 analogue for /design): replace with "emit the rendered summary block produced by the Final summary block above, followed by the machine footer; do not add additional prose, summary recaps, or farewell wording outside the rendered block." The rendered block IS the structured summary; the prohibition still applies to free-form prose around it.

### UPDATED: `skills/design/references/discussion-rounds.md` (FINDING_10)

Update sprawl-cancel paths at lines 22-26 (Step 1c heuristic) and the parallel Step 1d body: replace references to `### Terminal cost line` with `### Final summary block` and assign `--outcome cancelled-sprawl`. Confirm the file's load-when contract still applies (no semantics change beyond the rename + outcome).

### UPDATED: `skills/implement/SKILL.md`

1. **Step 18 `--print-stdout` removal** (FINDING_1, FINDING_4): change the Step 18 `write-final-report.sh` refresh call at lines 1868-1883 from `--print-stdout` mode to silent refresh mode (GitHub upsert + log refresh only; no second chat print).
2. **Delete the chat-tail Bash block** around lines 1820-1837 (both `LARCH_VERBOSE_TOKENS=true` and default branches that call `token-report.sh --summary` / `timing-report.sh --summary` and `--full --markdown`).
3. **Reword Step 17 prose** at lines 1814-1818 (FINDING_9): remove the "continue to the token summary" language; replace with: "The dollar-primary cost line is owned exclusively by the `larch:final-summary` block produced by `${CLAUDE_PLUGIN_ROOT}/scripts/render-run-summary.sh` (rendered by Step 17 via `skills/implement/scripts/write-final-report.sh --print-stdout`). Step 18 emits no token/timing summary to chat. The full per-step token and timing data is committed to `larch-logs/implement/<run-id>/token-report.md` and `timing-report.md` via `refresh-run-logs.sh`."
4. **Preserve** the `--since-last-mark --terse > /dev/null` calls at lines 1922-1923 (load-bearing ledger window cap; stdout already redirected).
5. **Preserve** the closing `Step 18 — done` `timing-ledger.sh mark` at line 1929.

### UPDATED: `skills/implement/references/summary-comment-template.md`

1. Update the marker list (top of file) to note that `larch:final-summary` is shared by both `/implement` and `/design`; `run-id` segments disambiguate.
2. Update the "rich markdown produced by `scripts/render-run-summary.sh`" prose to mention both skills' usage and the byte-aligned invariant for both `<skill>/<run-id>/final-summary.md` projections.

### UPDATED: `scripts/token-report.md` (FINDING_15)

Replace references to `--summary` as the dollar-primary surface and references to `render-cost-line.sh` as the /design caller. Describe the new contract: `token-report.sh --summary` emits a non-dollar Tokens summary; `render-run-summary.sh` is the sole authoritative dollar-line owner via its `- **Cost**:` bullet.

### UPDATED: `scripts/token-cost.md` (FINDING_15)

Update prose at lines 3-6 and 65 (per cursor-plan-pragmatic): describe `render-run-summary.sh` as the authoritative cost-line consumer of `token-cost.sh`; mark `render-cost-line.sh` as a deprecated standalone helper with no in-flow callers.

### UPDATED: `scripts/render-cost-line.md` (FINDING_15)

Add a deprecation banner at the top: "Deprecated standalone helper. No in-flow callers after PR #2714 — see `render-run-summary.sh` for the canonical cost-line emission path. Operators may still invoke this script directly for ad-hoc cost queries; harness coverage retained."

### UPDATED: `docs/linting.md` (FINDING_15)

Update the matrix row at lines 272-279 for `test-token-report-summary-format`: describe the new contract (assertions invert from "must contain dollar line" to "must NOT contain dollar line, must contain Tokens line"). Add a row for the new `test-render-final-summary` target.

### UPDATED: `Makefile`

Register new harnesses (with explicit `.PHONY` and target bodies):
- `test-render-final-summary` → invokes `skills/design/scripts/test-render-final-summary.sh`.
Add to the `lint` aggregate target (or pre-commit registration list).

### UPDATED: `agent-lint.toml`

Add `skills/design/scripts/test-render-final-summary.sh` near the design test-script exclusions (lines 799-812 per codex-pragmatic FINDING_15 sub-point) and `skills/design/scripts/test-render-final-summary.md` near the design `test-*.md` sibling exclusions (lines 1139-1152), mirroring the pattern for existing design harnesses.

## Edge cases

- **Token-report failure**: when `token-report.sh --full --format json` fails, the helper detects the failure via `token-report-final.stderr.log` non-empty + missing/unparseable JSON. Per FINDING_12, the helper passes NO token args to the renderer → `- **Cost**: N/A` (not `$0.00`). Captures `token-report-final.failure.log` and appends under `### Warnings` in `execution-issues.md` via `append-tool-failure.sh`. Silent degradation in chat.
- **Timing-report failure**: same pattern (FINDING_6) — `- **Duration**: N/A`. Captured to `timing-report-final.failure.log`. Silent degradation.
- **`jq` unavailable**: helper falls through to zero token values per bucket AND cost-unavailable signal → `- **Cost**: N/A`. Same N/A treatment for duration.
- **`$ISSUE_NUMBER` empty**: helper skips the upsert silently. Local `final-summary.md` is still written and chat block still printed.
- **Multiple `/design` runs on same issue, same run-id**: `tracking-issue-summary.sh upsert-summary` PATCHes the existing comment — idempotent.
- **Multiple runs, different run-ids**: separate comments coexist on the same tracking issue (run-id embedded in marker).
- **`--trivial` /design**: `Plan review` line shows `skipped (trivial)`. `OOS filed` shows `0`. `Cost` bullet shows Claude-only spend (Codex $0, Cursor $0) — legitimate zero, not the cost-unavailable signal.
- **Step 2b.5 soft-trigger paths**: no Final summary block invocation. Continue → Step 3. Split → existing Split-path (preserves `$DESIGN_TMPDIR`, exits 1, no render).
- **Gate C cancellation via "Other"**: non-terminal per `references/approval-gates.md`. No outcome assigned. Final summary block not invoked.
- **`token-report.sh --summary` direct invocation (post-consolidation)**: emits non-dollar `Tokens: <N>k` + per-vendor token counts only (FINDING_3). Operators querying dollar-cost must invoke `render-cost-line.sh` standalone (deprecated standalone helper) or run a full skill flow.
- **`render-cost-line.sh` still present**: no callers in `skills/**`; tests assert this. Script remains for ad-hoc operator use; deprecation banner added to sibling `.md` (FINDING_15).
- **Two-phase render with publish failure** (FINDING_7): Phase 1 writes `final-summary.md` pre-publish. Phase 2 reads updated `execution-issues.md` (with publish failure Warnings appended) and re-renders. The GitHub upsert reflects post-publish state. The committed `larch-logs/design/<RUN_ID>/final-summary.md` (Phase 1 content) may be slightly stale vs the GitHub comment (Phase 2 content) — document this drift in `render-final-summary.md` as an acceptable trade-off; the alternative (re-commit final-summary.md after Phase 2) requires a second push which is heavier.

## Failure modes

1. **Renderer schema divergence between /design and /implement projections**: byte-aligned invariant breaks if the `--skill design` branch introduces whitespace/formatting drift vs `--skill implement`. Earliest signal: `scripts/test-render-run-summary.sh` `--skill design` `cmp -s` assertion fails (FINDING_20). Mitigation: harness fixture covers both skills side-by-side; CI fails on divergence.

2. **Marker collision when /design and /implement run concurrently on same tracking issue with same run-id substring**: `tracking-issue-summary.sh` would find 2 matching comments and fail. Practically impossible (run-ids are UUIDs). Earliest signal: `tracking-issue-summary.sh` exits 2 in `--site "design Step 5"` stderr capture. Mitigation: log `Warnings` entry; do not block Step 5.

3. **Cost-line emission regression in `token-report.sh` rollback**: a revert reintroduces the dollar-line emit. Earliest signal: `scripts/test-token-report.sh` (FINDING_4) AND `scripts/test-token-report-summary-format.sh` both fail. Mitigation: both harnesses are part of `make lint`.

## Testing strategy

1. **`scripts/test-render-run-summary.sh` extension**: `--skill design` cohort, all outcome strings from the enumeration, `cmp -s` byte identity (FINDING_20).
2. **`skills/design/scripts/test-render-final-summary.sh` (new)**: dispatcher integration tests covering cost-unavailable (FINDING_12), duration N/A (FINDING_6), two-phase ordering (FINDING_7), counting algorithm (FINDING_13), outcome enumeration enforcement.
3. **`scripts/test-token-report-summary-format.sh` update**: invert dollar-line assertions; assert new Tokens line (FINDING_3).
4. **`scripts/test-token-report.sh` update** (FINDING_4): same inversion at Cases 1 and 2 + `--full --markdown` regression.
5. **`scripts/test-render-cost-line-callsites.sh` update**: zero matches in `skills/**`; only own file + harnesses + allowed siblings in `scripts/`.
6. **`scripts/test-design-structure.sh` update** (FINDING_5): retarget Check 15; new anchor name; encapsulation-aware (FINDING_14).
7. **`scripts/test-implement-structure.sh` update** (FINDING_1): invert Step 18 `--print-stdout` pin.
8. **Manual end-to-end smoke**: `/design --trivial` on a sandbox issue + `/implement`; observe single `larch:final-summary` comment per skill (distinct run-ids), one cost-line chat emission per run, `make lint` green.
9. **`make lint` aggregate**: includes all harnesses above; CI must pass before merge.


## Acceptance

- `/design` end-of-run output (all tiers, all post-Step-0a exits) shows a single `- **Cost**:` bullet inside the `larch:final-summary` body produced by `scripts/render-run-summary.sh --skill design`. No separate cost-line print elsewhere in the run.
- `/implement` end-of-run output for a full run shows the same single `- **Cost**:` bullet inside its `larch:final-summary` block (rendered by Step 17 only). Step 18 emits no token/timing summary to chat — both the default and `LARCH_VERBOSE_TOKENS=true` chat-tail branches are removed.
- `grep -rn 'render-cost-line.sh' skills/` returns ZERO matches. In `scripts/`, matches only `scripts/render-cost-line.sh` (+ its `.md` + its test harnesses).
- `scripts/token-report.sh --summary` no longer emits the dollar-primary cost line; it emits a non-dollar Tokens summary instead (verified by `scripts/test-token-report.sh` AND `scripts/test-token-report-summary-format.sh`).
- Both `/implement` Step 17 and `/design` Step 5 upsert their rendered summary to the tracking issue under the shared `<!-- larch:final-summary v1 runid=<R> -->` marker. The committed `<skill>/<run-id>/final-summary.md` projection is byte-identical to the GitHub upsert payload — verified via `cmp -s` in the new `--skill design` test cohort.
- `scripts/test-design-structure.sh` Check 15 successor (the new `design-final-summary-anchor` pin) passes.
- `scripts/test-implement-structure.sh` Step 18 anchor inversion (assert NO `--print-stdout`) passes.
- All new harnesses (`skills/design/scripts/test-render-final-summary.sh`) and updated harnesses pass.
- `make lint` is green.
- `/design --simple` (this run) records OOS follow-ups in #2726, #2727, #2728.

diff_lines: 850
