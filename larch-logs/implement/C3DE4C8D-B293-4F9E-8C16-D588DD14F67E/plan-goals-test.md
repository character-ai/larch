## Goal
Implement issue #6529: [IMPLEMENTING] [BUG] Final run summary (Gantt report) not displayed at end of /design and /implement….

## Implementation Plan
## Plan

Approach synthesis is `NO_SKETCHES`; draft from direct repo inspection.

## Approach

- Make final-summary emission a **terminal-position contract** on every `/design` and `/implement` path:
  - Read or capture the summary (and allowed sidecars) into orchestrator context when the file or marker body is still available;
  - run all required cleanup, sentinel, warning, footer, cancellation/partition, and tail-relay tool calls;
  - emit the cached verbatim summary body last, with no later tool calls or recap text.
- **Read/cache is not emission.** Mid-run `Read` of `FINAL_SUMMARY_PATH` or marker extraction may populate an in-context cache only; plain-chat emission is authorized solely by the terminal-placement rule.
- Keep generation unchanged. Only change prompt-side placement, caller ordering, and outcome display.
- Preserve old artifact tolerance. Readers must accept prior `DONE`, `STALLED`, `stalled`, and emoji-prefixed shapes where they already exist.
- On `/implement`, add an explicit **terminal-emit precedence** so Step 18 refreshed markers win over a stale Step 17 cache when `EMIT_BODY=true`.

## Files to modify/create

### UPDATED: skills/shared/final-summary-emit.md

Add a shared **terminal placement rule**: emitted final-summary bodies must be the final assistant text message of the turn, and no tool call may follow.

Qualify shared rule 8 (`When a Read path is used…`): Read may populate an in-context cache; only the terminal-placement rule authorizes plain-chat emission.

Update the `/design` Read-always profile:
- split **Read/cache** from **emit**;
- allow Read of `FINAL_SUMMARY_PATH` and allowed sidecars before cleanup;
- defer plain-chat emission until after cleanup (Step 5c happy path) or after required operator/cancellation/warning lines on early-exit paths;
- note that sidecar bodies, when allowed, must also be read before cleanup and emitted with the final summary, with no text after them.

Update marker-first wording and callsite bindings so `/implement` callers capture marker bodies, finish sentinel and teardown work, then emit the cached marker body last. Change Step 17 after-action from “write `.step17-emitted` after top-chat emission” to “wrapper writes `.step17-emitted` via `--step17-emitted true` before teardown when a body was cached for terminal emit.”

Add a short **Deferred emit procedure** subsection that other skill files may point to instead of duplicating ordering prose.

Add an **`/implement` terminal-emit precedence** subsection (authoritative for orchestrator chat emit):
1. After Step 18 warnings, finalize/teardown, and tail relay complete, choose exactly one body for terminal plain-chat emit.
2. **Precedence A — refreshed Step 18 body:** when captured composite stdout (`NEXT_ACTION=finalize-done`) or captured standalone finalize stdout has `EMIT_BODY=true`, `WFR_RC=0`, and a valid marker pair with non-empty body, terminal emit must use that post-Step-18b marker body even if a Step 17 cache exists.
3. **Precedence B — Step 17 cache:** when Precedence A does not apply and a non-empty Step 17 marker body was cached during Step 17, terminal emit uses the Step 17 cache.
4. **Precedence C — missing body:** when neither applies, emit only the existing missing-marker warning; do not Read `summary-final.md` after teardown.
5. Document that `STEP17_EMITTED_PRESENT` and `--step17-emitted true` are sentinel/suppression inputs for Step 18b refresh logic (`should_emit_updated_body`), not overrides of orchestrator terminal-emit precedence.

### UPDATED: skills/design/SKILL.md

**`### Final summary block`** — make this the authoritative deferred-emit procedure for every caller (Step 0b cancel routes, clarify failures, sprawl/decompose/partition exits, Step 3 `final-summary:*` routes, and Step 5c):

1. After bgjob `DONE` with `BGJOB_RC=0`, parse `FINAL_SUMMARY_PATH` and Read/cache the summary plus allowed sidecars from disk.
2. Do **not** print the cached body yet; mid-run Read is cache-only.
3. Print any required operator cancellation, partition, or failure line next (for example `**ℹ /design cancelled by operator.**`, partition exit text, plan-write failure warning).
4. Run any remaining non-summary work (WARN replay, Step 5 footer, Step 6 cleanup when applicable).
5. Emit the cached summary/sidecars as the sole terminal plain-chat output; no tool call or recap may follow.

Update inline cancel/partition callers (already-planned cancel, sprawl cancel, decompose cancel/partition, title-filter/file-only cancel profile, Step 3 `final-summary:*`) to follow this block: operator line before terminal emit, not after summary emission.

Change Step 5c item 5 from “Read and emit now” to “Read and cache now, emit later.”

For `_publish_rc` in `{0,1,3}`:
- parse `FINAL_SUMMARY_PATH`;
- Read/cache the summary and any allowed sidecar before Step 6 can delete `$DESIGN_TMPDIR`;
- do not print the summary yet;
- run existing WARN replay, plan-write warning, footer, and Step 6 cleanup as applicable;
- after Step 6 completes, emit the cached final-summary body as the final text.

For `PLAN_WRITE_OK=false`, skip Step 6 as today, but emit the cached summary after the plan-write failure warning so the summary is still the last text.

For `_publish_rc=2` or unexpected non-zero aborts, keep the existing stop path, but ensure summary Read/cache and sidecar reads happen before tmpdir loss and terminal emit is the last action after any required staging.

Rewrite anti-halt / anti-recap text: forbid recap **after** the terminal summary emit, not after the old Step 5 footer. Clarify that the turn may end only after deferred verbatim summary (plus sidecars) with zero following tool calls.

### UPDATED: skills/design/references/finalize-step5.md

Mirror the Step 5c and Step 5d ordering changes:
- final-summary is produced by the driver;
- prompt-side Read/cache may happen before cleanup;
- prompt-side emission must wait until all cleanup or failure routing is complete;
- Step 5 footer is no longer the last human-visible output of the whole run.

Keep the existing rule that Step 6 is skipped when plan write fails.

Point early-exit finalize wording at the authoritative `### Final summary block` deferred-emit procedure in `SKILL.md`.

### UPDATED: skills/design/references/design-outline.md

On outline cancel (`cancelled-outline`), follow the shared Final summary block contract: Read/cache during the block, print the cancellation line, defer verbatim emission to terminal text with no following tool call.

### UPDATED: skills/design/references/discussion-rounds.md

On sprawl cancel (`cancelled-sprawl`), follow the same deferred-emit contract instead of implying immediate summary emission before the cancellation line.

### UPDATED: skills/design/references/decompose-panel.md

On partition success, decompose cancel, and judge-panel failure exits, follow the shared contract: operator/partition line before terminal summary emit.

### UPDATED: skills/implement/SKILL.md

Invert the Step 17 and Step 18 final-report order and add firm terminal-emit precedence.

**Recover-then-report paragraph:** stall paths still skip to Step 18 first. Terminal marker emission happens only after Step 18 warnings, finalize/teardown, and tail relay complete. The final report renders exactly once at terminal text position.

**Anti-halt terminal boundary (rewrite):** Step 16–17 only capture a pending body; Step 18 runs cleanup/teardown/tail relay; terminal plain-chat emit is the last action with no following tool call. Remove emit-then-continue wording that treats Step 17 emission or the Step 17 `.step17-emitted` write as turn-ending.

**Step 17 green path:**
- run `python/cli.py implement step-16-17`;
- capture any valid marker body from wrapper stdout into a Step 17 cache;
- do **not** emit it yet;
- bind `STEP17_EMITTED_FOR_STEP18=true` **only** when a non-empty Step 17 marker body is cached for deferred terminal emit (drop the “already emitted to top chat” disjunct);
- continue to Step 18;
- wrapper owns `.step17-emitted` via `--step17-emitted true` before teardown when a Step 17 body is pending;
- after Step 18 warning replay, finalize/teardown, and tail relay, apply terminal-emit precedence (below).

**Step 18a / 18b:**
- parse `EMIT_BODY`, `WFR_RC`, and marker bodies from captured composite stdout on `NEXT_ACTION=finalize-done`, or from captured standalone finalize stdout on the stall-recovery path;
- run all warnings, missing-marker warnings, status parsing, closing marks, restore-finalize-state, and tail relay **before** terminal marker emission;
- **Terminal-emit precedence (authoritative):**
  - when `EMIT_BODY=true`, `WFR_RC=0`, and captured stdout has a valid marker pair with non-empty body, terminal chat emit must use that post-Step-18b marker body even if a Step 17 cache exists;
  - when `EMIT_BODY=false` and a non-empty Step 17 cache exists, terminal chat emit uses the Step 17 cache;
  - do not suppress Step 18 terminal emit solely because a Step 17 cache exists when `EMIT_BODY=true`;
- do not write `.step17-emitted` after finalization returns on the Step 18-only emit path.

Update NEVER #17 to allow only one final verbatim report emission, at the terminal text position. Keep the no-recap and no-cost-paraphrase bans; forbid prose or tool calls after that emit.

### UPDATED: skills/implement/references/step18-cleanup.md

Mirror the deferred-emit order for Step 18b: warnings → finalize/teardown capture → closing marks / restore / teardown → tail relay → terminal marker emit. Document `--step17-emitted true` semantics for cached-not-yet-emitted Step 17 bodies, that chat emission happens after teardown (not before), and that orchestrator terminal emit follows shared precedence: Step 18 refreshed markers when `EMIT_BODY=true`, else Step 17 cache when `EMIT_BODY=false`. Note that `should_emit_updated_body` in `python/larch/report/final_report.py` remains the refresh signal for `EMIT_BODY=true` when Step 17 sentinel exists but `summary-final.md` changed during Step 18b.

### UPDATED: python/larch/git/pr_body.py

Extend `_map_outcome_display`:
- success outcomes return `✅ DONE`;
- `stalled` returns `❌ STALLED`;
- other outcomes stay raw.

Keep the token text intact after the emoji for grep-ability.

### UPDATED: python/larch/report/final_report.py

Update stalled-summary reconciliation to accept old and new stalled outcome bullets:
- `stalled`;
- `STALLED`;
- `❌ STALLED`.

Rewrite recovered outcome bullets via `_map_outcome_display("merged")` → `✅ DONE` (not bare `DONE`).

Extend `_summary_stalled_outcome_index` and post-rewrite residue guards to match all three stalled forms; ensure no old or emoji stalled outcome bullet remains after recovery.

No change required to `should_emit_updated_body` unless implementation review shows prompt-side precedence and existing refresh logic diverge; document the contract in skill prose either way.

### UPDATED: python/larch/design/design_summary.py

Verify the degraded fallback already uses `_map_outcome_display`. Change only if needed to keep degraded `/design` summaries on the shared emoji display path.

### UPDATED: python/tests/git/test_pr_body.py

Update `_map_outcome_display` expectations and run-summary first-bullet assertions for `✅ DONE` and `❌ STALLED`.

Keep assertions that raw non-success outcomes remain unchanged.

### UPDATED: python/tests/report/test_run_logs.py

Update stalled summary and reconciliation expectations:
- new renders use `❌ STALLED`;
- recovered rewrites use `✅ DONE`;
- legacy fixture inputs may still use old `stalled`, `STALLED`, and bare `DONE` to prove backward tolerance.

### UPDATED: python/tests/design/test_design_summary.py

Update degraded and regular design summary expectations from `DONE` to `✅ DONE` where the shared mapper renders the Outcome bullet.

### UPDATED: python/tests/implement/test_ship.py

Update recovered-summary assertions where the final summary is expected to rewrite stalled state. Preserve old stalled fixture inputs to test compatibility with already-committed logs.

### UPDATED: skills/implement/scripts/test-write-final-report.sh

Update expected summary display strings:
- success and design-only paths expect `✅ DONE`;
- stalled paths expect `❌ STALLED`;
- raw bail outcomes stay unchanged.

Keep matrix coverage for outcomes that should omit the Outcome bullet.

### UPDATED: scripts/test-design-structure.sh

Update pinned design prompt strings for the new terminal-position rule:
- Final summary block Read/cache before emit;
- deferred emission after cleanup or operator lines;
- Step 5c reads before cleanup, Step 6 precedes final emission;
- no recap after terminal emission;
- contains/require pins for at least one cancel path (`cancelled-already-planned` or `cancelled-outline`).

Keep existing pins for `FINAL_SUMMARY_PATH`, sidecar handling, and render-exit carve-out.

### UPDATED: scripts/test-implement-structure.sh

Update pinned implement prompt strings:
- Step 17 caches marker body instead of emitting immediately;
- `STEP17_EMITTED_FOR_STEP18=true` only when a non-empty Step 17 body is cached;
- `.step17-emitted` is owned by wrappers before teardown;
- tail relay precedes terminal marker emit;
- final marker body emission happens after teardown with no following tool call;
- remove pins for old emit-then-continue / “write `.step17-emitted` only after top-chat emission” wording;
- add precedence pins: when `EMIT_BODY=true` with valid markers, terminal emit uses post-Step-18b body even if Step 17 cache exists; Step 17 cache only when `EMIT_BODY=false`.

### UPDATED: scripts/test-render-cost-line-callsites.sh

Update cross-surface pins for the shared final-summary emit contract, deferred Read/cache vs emit wording, implement Step 17/18 sentinel ordering, and `/implement` terminal-emit precedence (`EMIT_BODY=true` → Step 18 body wins).

Preserve the checks that forbid Bash or Python printing of the summary body.

### MAY_UPDATE: scripts/test-implement-fence-shape.sh

Update only if the implementation changes, adds, removes, or converts Bash fences in `skills/implement/SKILL.md`.

If touched, update `EXPECTED_OLD` / `EXPECTED_NEW` for the new fence shape.

### MAY_UPDATE: skills/implement/scripts/step-18.md

Update only if `--step17-emitted` and marker-handoff wording would become stale after the cache-then-emit contract and terminal-emit precedence.

### MAY_UPDATE: skills/implement/scripts/write-final-report.md

Update only if exact prose about `DONE` and `STALLED` display would become stale after emoji prefixes. Keep this a prose-only sync with `_map_outcome_display`.

## Edge cases

- `/design` Step 6 deletes `$DESIGN_TMPDIR`: Read/cache final summary and allowed sidecars before cleanup, then emit from cached content.
- `/design` early-exit routes (cancel, partition, failed-postplan): Read/cache during Final summary block, print operator line, emit cached body last with no following tool call.
- `/design` plan-block write failure skips cleanup: emit the cached summary after the warning, since no cleanup tool remains.
- `/implement` Step 17 marker body cached and Step 18 refresh produces new markers with `EMIT_BODY=true`: terminal emit uses the refreshed Step 18 marker body, not the Step 17 cache.
- `/implement` Step 17 marker body cached and Step 18 returns `EMIT_BODY=false`: terminal emit uses the Step 17 cache after tail relay.
- `/implement` Step 17 marker body absent: Step 18 remains responsible for terminal stall or recovery report markers after teardown when `EMIT_BODY=true`.
- Legacy committed summaries with `- **Outcome**: stalled`, `STALLED`, or bare `DONE` must still reconcile to `✅ DONE`.
- Raw non-success outcomes must not gain emoji unless explicitly mapped later.
- Passing `--step17-emitted true` without a pending Step 17 body must not suppress the only final report when `EMIT_BODY=true`.

## Failure modes

- Emitting before cleanup will still be hidden by the current harness.
- Reading after cleanup on `/design` can lose the only local summary copy.
- Emitting summary before cancellation/partition lines leaves operator context after the Gantt block on early exits.
- Emitting the Step 17 cache when `EMIT_BODY=true` leaves stale cost/timing data visible after Step 18 refresh.
- Writing `.step17-emitted` too late or binding `STEP17_EMITTED_FOR_STEP18` without a cached body can suppress or duplicate the final report.
- Regexes that require exact `STALLED` can miss `❌ STALLED` and leave stale summaries unreconciled.
- Updating prompt prose without harness pins can leave green tests that do not protect the new ordering or precedence.

## Testing strategy

Run changed-file checks only.

- `bash scripts/test-design-structure.sh`
- `bash scripts/test-implement-structure.sh`
- `bash scripts/test-render-cost-line-callsites.sh`
- `bash skills/implement/scripts/test-write-final-report.sh`
- If `skills/implement/SKILL.md` fence shape changes: `bash scripts/test-implement-fence-shape.sh`
- `python3 -m pytest python/tests/git/test_pr_body.py python/tests/report/test_run_logs.py python/tests/design/test_design_summary.py python/tests/implement/test_ship.py`

Also run targeted linters for changed skill and shell files if relevant checks select them:
- `python3 python/cli.py checks run-relevant`

## Acceptance

- `/design` final summary body is the final assistant text on Step 5c success, plan-write failure, and every Final summary block early-exit path.
- `/implement` final report body is the final assistant text on Step 17 green paths and Step 18b terminal paths, after teardown completes.
- On `/implement`, when `EMIT_BODY=true` with valid post-Step-18b markers, terminal emit shows refreshed Step 18 content even if a Step 17 cache exists; Step 17 cache emits only when `EMIT_BODY=false`.
- No tool call, cleanup fence, sentinel write, warning relay, operator line, or recap text follows the verbatim final summary.
- Outcome bullets render `✅ DONE` and `❌ STALLED`.
- Legacy stalled summaries still reconcile to `✅ DONE`.
- Prompt-shape harnesses pin deferred Read/cache, operator-line ordering, tail-relay-before-emit, and Step 18-over-Step-17 terminal-emit precedence on both skills.

## Acceptance

Run changed-file checks only.

- `bash scripts/test-design-structure.sh`
- `bash scripts/test-implement-structure.sh`
- `bash scripts/test-render-cost-line-callsites.sh`
- `bash skills/implement/scripts/test-write-final-report.sh`
- If `skills/implement/SKILL.md` fence shape changes: `bash scripts/test-implement-fence-shape.sh`
- `python3 -m pytest python/tests/git/test_pr_body.py python/tests/report/test_run_logs.py python/tests/design/test_design_summary.py python/tests/implement/test_ship.py`

Also run targeted linters for changed skill and shell files if relevant checks select them:
- `python3 python/cli.py checks run-relevant`

mechanical_churn: false
oversize_override: operator
diff_lines: 340

## Test plan
(no test plan section in plan-file)
