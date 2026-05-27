## Goal
Implement issue #2970: [IMPLEMENTING] Final-summary rigid template is invisible in chat for both /design and…\n\nFinal-summary rigid template is invisible in chat for both /design and /implement when the script is invoked directly from an orchestrator Bash block..

## Implementation Plan
## Plan

Surface the full `larch:run-summary` / `larch:final-summary` structured block at top chat for both `/design` and `/implement`. Replace the current "cost-line-only" orchestrator emission with a strictly-verbatim full-block emission that reads the persisted summary file and emits its entire body as plain chat markdown after the renderer's Bash call.

### Approach

`render-final-summary.sh` (design) and `write-final-report.sh` (implement) already persist the canonical structured block to `$DESIGN_TMPDIR/final-summary.md` and `$IMPLEMENT_TMPDIR/summary-final.md` respectively. The renderer's own print loop continues to write the block to stdout (which lands inside the collapsed Bash tool result UI) or to FD 3 when `LARCH_QUIET_PID=$$`. No script change.

The orchestrator-side change is a contract change in **all** SKILL.md anti-halt / terminal-boundary sites that currently bind the orchestrator to a single-line `- **Cost**:` emit. Replace "the orchestrator MUST emit that single verbatim `- **Cost**:` line" with "the orchestrator MUST read the persisted summary file and emit its full body verbatim as plain chat markdown, only when the file is non-empty". The gating condition becomes **file non-empty**, not **contains a Cost line**, so cost-absent but otherwise valid summaries still surface (FINDING_3). Strict no-paraphrase / no-extra-prose guards remain so the per-agent cost breakdown invariant from #2837 cannot regress.

The cost line is no longer extracted and emitted separately — it stays inside the full body that the orchestrator emits. The Bash tool will continue to capture the renderer's stdout inside the collapsed tool result UI; the orchestrator emit at top chat is the visibility channel. This produces a brief duplication (full block appears inside the Bash result AND at top chat) which is acceptable — better duplicate than invisible.

For Step 17/18 in `/implement`, the change is mechanical (FINDING_4, FINDING_8): rename and re-purpose the existing Bash variables that track "did Step 17 print, did cost change". The new contract is "did Step 17 emit a non-empty body, and did the body change between Step 17 and Step 18". Use a `cmp -s` against a durable pre-Step-18 snapshot file written inside the Step 18 Bash fence before re-render.

### Files to modify/create

#### UPDATED: `skills/design/SKILL.md`

Replace cost-line-only language with full-block-verbatim language at every relevant callsite. Gating becomes "non-empty persisted file" instead of "contains a Cost line".

- **Anti-halt continuation reminder** (around line 30): change `The only orchestrator-text addition permitted after that Bash summary is the single verbatim - **Cost**: line from $DESIGN_TMPDIR/final-summary.md` to require the **full body** of `$DESIGN_TMPDIR/final-summary.md` verbatim, gated on the file being non-empty. Keep the "NEVER write a free-form natural-language recap summary" guard intact.
- **Post-publish emit prose** (around line 288, after the `### Final summary block` fence): change `the orchestrator MUST emit exactly that one line as plain chat text` to `the orchestrator MUST read $DESIGN_TMPDIR/final-summary.md and emit its full body verbatim as plain chat markdown`. Change gating from `contains a line beginning with - **Cost**:` to `[ -s "$DESIGN_TMPDIR/final-summary.md" ]` (non-empty). Update the mechanism: `read final-summary.md (via the Read tool, or via Bash cat whose output is then re-emitted as orchestrator text), emit the entire file body verbatim as plain markdown chat text. Do NOT paraphrase, summarize, reorder, or add prose between bullets. The full structured block — including title, mode, duration, cost line with per-agent breakdown, tokens, and all bullets — must appear at top chat.` Replace `Do NOT emit any other summary content as plain text; title, mode, duration, and other bullets stay inside the rendered block.` with `Do NOT add free-form prose around the block. The verbatim file body is the only permitted summary content at top chat.`
- **Step 5c item 10** (FINDING_1 — currently bullet "(chat print + larch:final-summary upsert when issue-bound — rerenders after publish so warnings/exec-issue counts match committed logs). … If the helper exits 0 and `$DESIGN_TMPDIR/final-summary.md` contains `- **Cost**:`, emit that single verbatim cost line as plain chat text, and no other summary prose."): replace the cost-line-only instruction with the same non-empty `final-summary.md` full-body verbatim emit contract used at line ~288. Specifically: change `If the helper exits 0 and $DESIGN_TMPDIR/final-summary.md contains - **Cost**:, emit that single verbatim cost line as plain chat text, and no other summary prose.` to `If the helper exits 0 and $DESIGN_TMPDIR/final-summary.md is non-empty, emit the full body of final-summary.md verbatim as plain chat markdown, and no other summary prose.`
- **End-of-Step-5 prose** (around line 1021): same contract swap. Replace `The only orchestrator-text addition permitted after that Bash block is, in order: the single extracted - **Cost**: line, any required repeated external-reviewer warnings, and the machine footer.` with `The orchestrator MUST emit the full body of $DESIGN_TMPDIR/final-summary.md verbatim as plain chat markdown after the Bash block (only when the file is non-empty), followed by any required repeated external-reviewer warnings, and then the machine footer. No free-form recap may appear between or after those pieces.` Adjust the `Reason:` clause accordingly: `Reason: a verbatim full-block emission ensures the per-agent breakdown (Claude $X, Codex $X, Cursor $X) and all other bullets are visible at top chat without depending on Bash-tool UI expansion. Free-form summaries are forbidden because they would either omit or paraphrase that breakdown.` Replace any remaining "mandatory verbatim cost-line emit" vocabulary in this section with "mandatory verbatim full-body emit".

#### UPDATED: `skills/implement/SKILL.md`

Mirror the design changes at every implement-side callsite. Gating becomes non-empty file in all sites.

- **Terminal-boundary instruction** (FINDING_2 — around line 14): change the top-level cost-line-only emit instruction to direct the orchestrator to follow NEVER #20's full-body verbatim emit contract after Step 17. Specifically: replace `emit only the mandatory cost line after Step 17` (or the equivalent current wording) with `emit the full body of summary-final.md verbatim per NEVER #20 after Step 17, then continue to Step 18`.
- **NEVER #20** (around line 73): replace `The only orchestrator-text addition permitted after the Bash summary is the single verbatim cost-line emit defined in Step 17` with `The only orchestrator-text addition permitted after the Bash summary is the verbatim full-body emission of $IMPLEMENT_TMPDIR/summary-final.md defined in Step 17`. Update the `How to apply:` sentence to `after Step 17's write-final-report.sh invocation prints to chat, if summary-final.md is non-empty then write $IMPLEMENT_TMPDIR/.step17-printed, and the orchestrator emits the full body of summary-final.md verbatim as plain chat markdown, then immediately continue to Step 18.` Keep the `Do NOT add a closing recap, do NOT echo the structured block in your own words, and do NOT mention costs in your own prose` guards. Replace `The only orchestrator-text addition permitted after the Bash summary is the single verbatim cost-line emit defined in Step 17` references with the full-body emit equivalent.
- **Step 17 cost-line emit prose** (around line 1760): replace `if the script succeeded and summary-final.md contains a line beginning with - **Cost**:, the orchestrator MUST emit that line verbatim as one line of plain chat text` with `if the script succeeded and summary-final.md is non-empty, the orchestrator MUST emit the full body of summary-final.md verbatim as plain chat markdown`. Update the mechanism: `read summary-final.md (via the Read tool, or via Bash cat whose output is then re-emitted as orchestrator text), emit the entire file body verbatim as plain markdown chat text. Do NOT paraphrase, summarize, reorder, or add prose between bullets.` Replace `The cost line is the sole exception under NEVER #20.` with `The verbatim full-body emission is the sole exception under NEVER #20; the cost line with its per-agent breakdown is part of that body and not a separate emission.`
- **Step 17 "no separate cost line" sentinel logic and Step 18 dual-condition guard prose** (around line 1764): replace `Step 18 emits no token/timing summary to chat` with `Step 18 emits the refreshed summary-final.md body verbatim as plain chat markdown only under the dual-condition guard described below (either Step 17 did not print, or the post-render body differs from the pre-Step-18 snapshot)` (FINDING_9).
- **Step 18 cost-line emit prose** (around line 1828): replace `the orchestrator MUST emit that single verbatim - **Cost**: line as plain chat text when either condition holds: Step 18 passed --print-stdout because $IMPLEMENT_TMPDIR/.step17-printed was absent, or the refreshed cost line changed from the pre-Step-18 value` with `the orchestrator MUST emit the full body of summary-final.md verbatim as plain chat markdown when either condition holds: Step 18 passed --print-stdout because $IMPLEMENT_TMPDIR/.step17-printed was absent, or the body of summary-final.md changed from the pre-Step-18 snapshot (compared via cmp -s against $IMPLEMENT_TMPDIR/.step18-prebody)`.
- **Step 17 Bash fence variables** (FINDING_4): rename `_wfr_emit_cost`, `_wfr_prev_cost`, `_wfr_new_cost` to body-based equivalents `_wfr_emit_body`, `_wfr_prev_body`, `_wfr_new_body` (or similar). Gate the `.step17-printed` touch on `[ -s "$IMPLEMENT_TMPDIR/summary-final.md" ]` rather than "contains Cost line". Preserve the rest of the Step 17 mechanics (sentinel write, ordering).
- **Step 18 Bash fence — pre-refresh snapshot mechanism** (FINDING_8): inside the Step 18 fenced Bash, immediately **before** the `write-final-report.sh` re-render call, copy the current `$IMPLEMENT_TMPDIR/summary-final.md` to `$IMPLEMENT_TMPDIR/.step18-prebody` (or skip the copy if `summary-final.md` is absent). After the re-render, compare with `cmp -s "$IMPLEMENT_TMPDIR/.step18-prebody" "$IMPLEMENT_TMPDIR/summary-final.md"`. The orchestrator's emit decision uses the cmp result (non-zero exit = body changed → emit). This snapshot lives entirely inside the Bash fence; the orchestrator reads only the post-fence `summary-final.md`.
- **Step 17 vs Step 18 tmpdir vs run-log path clarity** (FINDING_10 — wherever the overview names tmpdir final summary path): clarify that the **tmpdir** path is `$IMPLEMENT_TMPDIR/summary-final.md`, while `larch-logs/implement/<RUN_ID>/final-summary.md` is the separately persisted run-log artifact written by ship-pr / log-publish helpers. Edit the misnamed reference to use the correct tmpdir basename.

#### UPDATED: `skills/design/scripts/render-final-summary.md`

Update the chat-print contract description so the doc accurately reflects the two-step contract (script renders/persists; orchestrator surfaces persisted body to top chat).

- Around lines 6, 57-58: change "prints the body to chat" wording to "renders the body to `final-summary.md` and streams it via stdout (or FD 3 when `LARCH_QUIET_PID=$$`); the calling skill's orchestrator then emits the full file body verbatim as plain chat markdown so the block is visible at top chat without depending on Bash-tool UI expansion".
- Add a "Top-chat visibility contract" section (~5 lines) explicitly stating: the script writes the canonical block to disk and to its print stream; the orchestrator (per SKILL.md anti-halt prose) is responsible for reading that file and emitting its full body verbatim at top chat after the Bash call, gated on the file being non-empty.

#### UPDATED: `skills/implement/scripts/write-final-report.md`

Mirror the design sibling doc update.

- Around lines 46-48 (the `--print-stdout` section): clarify that `--print-stdout` is the renderer's print mechanism; top-chat visibility is achieved by the orchestrator emitting the persisted `summary-final.md` body verbatim after the Bash call (per `skills/implement/SKILL.md` Step 17 / Step 18 prose). Note that the FD-3-vs-stdout dichotomy remains relevant for lib-quiet-aware callers but is not the primary top-chat visibility channel. Note that the canonical tmpdir basename is `summary-final.md`, distinct from `larch-logs/implement/<RUN_ID>/final-summary.md` (FINDING_10).

#### UPDATED: `scripts/test-render-cost-line-callsites.sh`

This test currently pins the cost-line-only prose. Update it to pin the new full-block-verbatim prose AND add negative greps to prove the retired prose is gone.

- **Positive pins (replace existing line ~46, 48, 49, 54 cost-line pins)**:
  - Pin `skills/design/SKILL.md` post-publish prose contains the literal `the orchestrator MUST read $DESIGN_TMPDIR/final-summary.md and emit its full body verbatim as plain chat markdown`.
  - Pin `skills/design/SKILL.md` Step 5c item 10 contains the literal `If the helper exits 0 and $DESIGN_TMPDIR/final-summary.md is non-empty, emit the full body of final-summary.md verbatim as plain chat markdown`.
  - Pin `skills/implement/SKILL.md` Step 17 contains the literal `the orchestrator MUST emit the full body of summary-final.md verbatim as plain chat markdown`.
  - Pin `skills/implement/SKILL.md` Step 18 contains the literal `the orchestrator MUST emit the full body of summary-final.md verbatim as plain chat markdown when either condition holds`.
  - Pin `skills/implement/SKILL.md` NEVER #20 contains the literal `The only orchestrator-text addition permitted after the Bash summary is the verbatim full-body emission of $IMPLEMENT_TMPDIR/summary-final.md`.
- **Bash-snippet pins (FINDING_4 / FINDING_8)**: replace the `_wfr_emit_cost` / `_wfr_new_cost` / `contains - **Cost**:` Step 17/18 sentinel grep pins at lines 37, 44 with new pins that match the body-based variable names (`_wfr_emit_body`), the `[ -s "$IMPLEMENT_TMPDIR/summary-final.md" ]` non-empty gate, and the `cmp -s "$IMPLEMENT_TMPDIR/.step18-prebody"` comparison.
- **Negative greps (FINDING_5)**: add `if git -C "$REPO" grep -Fq -- '<retired prose>' skills/design/SKILL.md skills/implement/SKILL.md; then fail '<reason>'` pins for each retired substring, including (but not limited to): `emit exactly that one line`, `emit that single verbatim`, `single extracted - **Cost**:`, `The cost line is the sole exception`, `orchestrator emits the single verbatim cost line`, `single verbatim cost-line emit`.
- **Keep the allowlist guard** for `render-cost-line.sh` references — that machinery is separate and out of scope.
- **Defer rename** of the test file itself to keep the diff small; the file's purpose evolves from "cost-line callsite pins" to "summary full-block callsite pins" but the filename is preserved unless `make lint` flags the mismatch.

#### UPDATED: `scripts/test-render-cost-line-callsites.md`

Update the sibling doc to describe the new full-block summary callsite contract (FINDING_6). Keep the render-cost-line allowlist wording explicitly scoped to the deprecated standalone helper. Mention the negative-grep coverage now part of the test.

#### UPDATED: `docs/linting.md`

Around line 291 (the `test-render-cost-line-callsites` row in the linter catalog): update the description to reflect the new full-block summary callsite contract (FINDING_6). Note that the test now pins both positive full-body emission prose AND negative greps preventing reintroduction of cost-line-only language.

#### UPDATED: `scripts/test-design-structure.sh`

If this script contains any prose pin that hard-codes the cost-line-only emission text, swap it for the new full-block-verbatim text. Codebase scan suggests this file does not currently pin that specific prose — verify with a `grep -F` check. Update or remove pins as needed.

#### UPDATED: `scripts/test-implement-structure.sh`

Same pattern as `test-design-structure.sh`. Verify any pins on cost-line-only prose and swap to full-block-verbatim prose where needed.

#### UPDATED: `CHANGELOG.md`

Add a one-paragraph entry under the appropriate version section (likely the same patch tier as #2837's PR #2836, or a fresh patch entry):

> **Fix #2970:** Final-summary rigid template now surfaces at top chat for both `/design` and `/implement`. The renderer infrastructure from #2837 stays intact — the change is purely the orchestrator-side emission contract: the orchestrator now reads the persisted `final-summary.md` / `summary-final.md` and emits its full body verbatim as plain chat markdown after the Bash call. The previous cost-line-only emission is replaced with full-body emission gated on a non-empty persisted file, which preserves the per-agent cost breakdown invariant from #2837 and makes the full structured block visible without depending on Bash-tool UI expansion.

### Edge cases

- **Missing or empty persisted summary file**: if `$DESIGN_TMPDIR/final-summary.md` (or `$IMPLEMENT_TMPDIR/summary-final.md`) is absent or empty after a renderer Bash block, the orchestrator MUST NOT emit anything; the existing "summary not produced" behavior takes over. All SKILL.md prose must gate the emit on `[ -s "<file>" ]` (non-empty file), NOT on "contains `- **Cost**:`" (FINDING_3). A cost-absent but otherwise valid summary (e.g., a degraded run where the cost helper failed but the body still rendered) MUST still surface.
- **Renderer printed via FD 3** (when `LARCH_QUIET_PID=$$`): the orchestrator still emits the full body verbatim at top chat. FD-3 output does not magically surface to top chat; the orchestrator emission is the visibility channel regardless of which FD the renderer chose.
- **Step 18 unchanged body**: when Step 18's refreshed body equals Step 17's body byte-for-byte (`cmp -s` succeeds against the durable `.step18-prebody` snapshot), the orchestrator does NOT re-emit (FINDING_4, FINDING_8).
- **Step 18 absent `.step18-prebody`** (e.g., first time Step 18 runs without Step 17 having printed): treat as "body changed" → emit the full body once.
- **Cancellation paths** (Step 5 cancel branches in `/design`): they follow the same full-body emission contract because they flow through the post-publish prose at SKILL.md line ~288 (which the plan updates once).
- **`pre-publish-only` render** (Step 5c item 8): writes the file but does NOT print; the orchestrator does NOT emit during pre-publish. Preserve existing gating ("after every `render-final-summary.sh --post-publish-only` invocation").

### Failure modes

1. **Paraphrase regression**: the highest-risk failure path. Mitigation: test pins in `test-render-cost-line-callsites.sh` assert the exact verbatim-emission prose is present (positive pins) AND that the retired cost-line-only prose is absent (negative greps, FINDING_5).
2. **Orchestrator forgets to emit**: the SKILL.md prose uses mandatory MUST-emit language with concrete "Mechanism:" instructions. Optionally surface a single-line breadcrumb (e.g., `📋 emitting final-summary at top chat`) before the emit so operators see it happened.
3. **File-byte mismatch between Step 17 and Step 18**: Step 18 Bash fence writes a durable pre-render snapshot at `$IMPLEMENT_TMPDIR/.step18-prebody`; orchestrator uses `cmp -s` against the post-render `summary-final.md` to decide whether to emit (FINDING_8).

### Testing strategy

- Run `bash scripts/relevant-checks.sh` after every edit pass.
- Update `scripts/test-render-cost-line-callsites.sh` to pin the new prose (positive) AND retire the old prose (negative greps, FINDING_5).
- Run `scripts/test-design-structure.sh` and `scripts/test-implement-structure.sh`; update any prose pins that referenced the cost-line-only exception.
- Manual smoke: run `/design --simple <some-test-issue>` or `/implement --merge <some-test-issue>` against a low-stakes issue and verify the full structured block appears at top chat without manual Bash-output expansion.
- Per-agent cost breakdown invariant: confirm the `Claude $X, Codex $X, Cursor $X` shape is preserved.

## Acceptance

The implementation is complete when ALL of the following hold:

1. **Design SKILL.md edits applied at four sites** — Anti-halt continuation reminder (line ~30), Post-publish emit prose (line ~288), Step 5c item 10, and End-of-Step-5 prose (line ~1021) — each replacing cost-line-only language with full-body verbatim emission, with gating on `[ -s "$DESIGN_TMPDIR/final-summary.md" ]` rather than "contains `- **Cost**:`".
2. **Implement SKILL.md edits applied at five sites** — Terminal boundary (line ~14), NEVER #20 (line ~73), Step 17 emit prose (line ~1760), Step 17 "no token/timing" sentence (line ~1764), and Step 18 emit prose (line ~1828) — each replacing cost-line-only language with full-body verbatim emission, with non-empty file gating.
3. **Implement Step 17 / Step 18 Bash fence variables updated** — `_wfr_emit_cost` / `_wfr_prev_cost` / `_wfr_new_cost` renamed/repurposed to body-based equivalents; `.step17-printed` touch gated on non-empty `summary-final.md`; Step 18 fence writes `.step18-prebody` snapshot before re-render and uses `cmp -s` for the body-change check.
4. **Sibling docs updated** — `skills/design/scripts/render-final-summary.md` and `skills/implement/scripts/write-final-report.md` describe the two-step contract (script renders/persists; orchestrator surfaces persisted body verbatim).
5. **Test harness updated** — `scripts/test-render-cost-line-callsites.sh` has positive pins for the new full-body emission prose at all five SKILL.md callsites plus the Bash-snippet variable pins, AND negative greps proving the retired cost-line-only prose is absent.
6. **Linter catalog and harness sibling doc updated** — `docs/linting.md` (around line 291) and `scripts/test-render-cost-line-callsites.md` describe the new full-block summary callsite contract.
7. **Path drift correction in implement SKILL.md overview** — `$IMPLEMENT_TMPDIR/summary-final.md` correctly named (no `final-summary.md` typo confusion with the run-log artifact).
8. **`scripts/test-design-structure.sh` and `scripts/test-implement-structure.sh` pass** — any prose pins referencing cost-line-only emission are swapped or removed.
9. **`bash scripts/relevant-checks.sh` passes** — no test regressions.
10. **CHANGELOG.md** records the channel-of-emission change (renderer infrastructure unchanged; orchestrator emission contract updated).
11. **No template body change** — `larch:run-summary` / `larch:final-summary` markdown shape, GitHub issue comment upsert path, and committed `larch-logs/.../final-summary.md` file path all remain exactly as today.
12. **Manual smoke confirms top-chat visibility** — running `/design --simple <issue>` or `/implement --merge <issue>` after merge, operators see the full structured block (including the per-agent `Claude $X, Codex $X, Cursor $X` cost breakdown) at top chat without manual Bash-output expansion.

diff_lines: 150

## Test plan
(no test plan section in plan-file)
