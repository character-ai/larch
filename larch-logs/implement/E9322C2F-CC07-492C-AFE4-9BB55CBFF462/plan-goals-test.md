## Goal
Implement issue #3097: [IMPLEMENTING] OOS follow-ups from #3059 combined-fallback rollout (design consumers + test coverage)\n\n## Out-of-Scope Observation.

## Implementation Plan
## Plan

This plan implements the three accepted OOS items from issue #3097 with a minimum-change SIMPLE-tier approach. The fix shape is locked in by Step 1c clarifications: Item A emits a single new `COMBINED_FALLBACK_COUNT` KV from `scripts/dispatch-with-waterfall.sh` and updates three design consumers; Item B adds two new harness scenarios; Item C extends one existing harness scenario. Step 3 plan review surfaced four accepted findings; the plan below incorporates all four directly (Gate B auto-apply mode).

A scope clarification surfaced during Step 0c codebase scan that is preserved here so reviewers and the implementer share the same premise: the dispatcher NDJSON schema treats `agent` and `prompt_file` as mutually exclusive (see `scripts/dispatch-with-waterfall.sh` validation, around the `slot '$slot_name' must not set both agent and prompt_file` guard). Issue #3097 Item C describes "agent_file alongside prompt_file" — interpreted literally, that fixture shape would be rejected. The plan implements the truthful intent of Item C: extend the existing competition-notice scenario (which already uses an `agent` slot) to additionally assert the dispatcher threads `--agent-file <path>` into the external launcher argv. This closes the real coverage gap (no argv-shape assertion today) without changing the dispatcher schema.

## Files to modify/create

### UPDATED: `scripts/dispatch-with-waterfall.sh`
- Add one `emit_kv COMBINED_FALLBACK_COUNT "$combined_fallback"` line in the stdout-emit block immediately after the existing `PHASE2_RELAUNCH_COUNT` emit (around the `emit_kv FALLBACK_COUNT` / `emit_kv PHASE2_RELAUNCH_COUNT` cluster). The `combined_fallback` local already exists (it is what gates the WARN). No other behavior change; this is purely an additive KV.
- Extend the embedded `cp` stub support so the Item B-1 scenario can drive two phase-2 reuse-copy failures. The existing `cp` stub in `scripts/test-dispatch-with-waterfall.sh` only fails the **first** match against `CP_STUB_FAIL_TARGET_CONTAINS`; FINDING_1 from the review panel showed B-1 cannot be exercised without a minimal stub extension. The stub change goes in the harness file (see below), but a one-line comment in `dispatch-with-waterfall.sh` near the existing `cp -p` reuse call (around the `cp -p "$reuse_source" "$slot_phase1_output"` site) is sufficient — no production-code change is required. If review feedback during /implement deems the production-code touch unnecessary, omit the comment.

### UPDATED: `scripts/dispatch-with-waterfall.md`
Add a bullet to the **Stdout keys** list:
- `COMBINED_FALLBACK_COUNT` = `FALLBACK_COUNT` + `PHASE2_RELAUNCH_COUNT` (the same value the WARN compares against `LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD`).

### UPDATED: `skills/design/scripts/dispatch-plan-review-panel.sh`
- Add `COMBINED_FALLBACK_COUNT=""` to the variable initialization block alongside the existing `FALLBACK_COUNT=""`.
- Add `COMBINED_FALLBACK_COUNT) COMBINED_FALLBACK_COUNT="$_value" ;;` to the `case "$_key"` parse table.
- After the existing `case "$FALLBACK_COUNT" in ''|*[!0-9]*) FALLBACK_COUNT=0 ;; esac` numeric guard, add the same guard for `COMBINED_FALLBACK_COUNT` defaulting to `$FALLBACK_COUNT` when the new KV is absent (defensive: handles older waterfall builds without the KV; ensures parity with current behavior in that case).
- Swap the `(( 10#$FALLBACK_COUNT > floor_half ))` comparison to `(( 10#$COMBINED_FALLBACK_COUNT > floor_half ))`.

### UPDATED: `skills/design/scripts/dispatch-plan-review-panel.md`
Update the **Extra stdout KVs** sentence: change the parenthetical describing when `DEGRADED_ROUND` fires from `FALLBACK_COUNT > floor(slot_count/2)` to `COMBINED_FALLBACK_COUNT > floor(slot_count/2)`. Also tweak the pass-through sentence to add `COMBINED_FALLBACK_COUNT` next to the existing `FALLBACK_COUNT` / `PHASE2_RELAUNCH_COUNT` list.

### UPDATED: `skills/design/scripts/plan-review-loop.sh`
- Add `COMBINED_FALLBACK_COUNT=""` to the initialization cluster alongside the existing `FALLBACK_COUNT="0"`. Use the **empty-string** form (not `"0"`) so the existing `''|*[!0-9]*)` numeric guard correctly defaults to `$FALLBACK_COUNT` when the new KV is absent from dispatcher output (FINDING_2). This mirrors the other two consumers exactly.
- Add `COMBINED_FALLBACK_COUNT) COMBINED_FALLBACK_COUNT="$_value" ;;` to the dispatcher-output parse `case`.
- Add `case "$COMBINED_FALLBACK_COUNT" in ''|*[!0-9]*) COMBINED_FALLBACK_COUNT="$FALLBACK_COUNT" ;; esac` after the existing numeric guard.
- Change the `if (( 10#$FALLBACK_COUNT > floor_half ))` comparison to `if (( 10#$COMBINED_FALLBACK_COUNT > floor_half ))`.
- **FINDING_3 — zero-finding short-circuit**: the existing `emit_loop_kvs complete 0 0 skipped-empty-input skipped-empty-findings ...` call near the no-findings branch hardcodes `DEGRADED_PANEL=0`, bypassing the COMBINED check. Replace the hardcoded `0` with a small inline calculation that mirrors the main degradation block: at minimum, set the value to `1` when `STATIC_DISPATCH_OK=false`, `PANEL_DISPATCH_OK=false`, `DEGRADED_ROUND=true`, or `10#$COMBINED_FALLBACK_COUNT > floor_half`. Compute it once into a local variable just before both `emit_loop_kvs` call sites and pass that variable in place of the hardcoded literal. Voter-failure conditions (`_nonfailed_voters < 2`) do not apply on the no-findings path because voting was skipped.

### UPDATED: `skills/design/scripts/plan-review-loop.md`
Add a short clarifying sentence to the existing degradation-decision prose (or its KV pass-through list) noting that `DEGRADED_PANEL` now factors in phase-2 fall-through relaunches via `COMBINED_FALLBACK_COUNT`, and that this signal is honored even on the no-findings short-circuit branch.

### UPDATED: `skills/design/scripts/decompose-panel-dispatch.sh`
Mirror the `dispatch-plan-review-panel.sh` triple:
- `COMBINED_FALLBACK_COUNT=""` init.
- `COMBINED_FALLBACK_COUNT) COMBINED_FALLBACK_COUNT="$_value" ;;` parse case.
- Numeric guard defaulting to `FALLBACK_COUNT` on absence.
- Swap the `(( 10#$FALLBACK_COUNT > floor_half ))` comparison to `(( 10#$COMBINED_FALLBACK_COUNT > floor_half ))`.

### UPDATED: `skills/design/scripts/decompose-panel-dispatch.md`
Update the relevant degradation-decision sentence (mirrors `dispatch-plan-review-panel.md`).

### UPDATED: `scripts/test-dispatch-with-waterfall.sh`
Four additions in this file:

1. **Stub extension for FINDING_1**: extend the embedded `cp` stub (around the `STUB` heredoc near the top of the file) to optionally support a multi-target list. Two options of equal weight — implementer picks:
   - Add `CP_STUB_FAIL_TARGET_CONTAINS_LIST` (newline-separated substrings); fail the first call whose argv matches any item not yet consumed; consume the matched item from the list (write the remaining list back to a state file alongside `CP_STUB_FAIL_COUNTER`).
   - Add `CP_STUB_FAIL_COUNT` (integer); fail the first N calls whose argv matches the single `CP_STUB_FAIL_TARGET_CONTAINS` substring.
   Either knob is sufficient; the second is the smaller diff. Preserve the existing single-fail behavior when neither new var is set (back-compat).
2. **Item B-1 — multi-fall-through `PHASE2_RELAUNCH_COUNT=2`**: A new scenario with three grouped slots (cursor primary) all in one `fallback_group`, using the new stub knob so two of the phase-2 reuse-copies fail. Assert `PHASE2_RELAUNCH_COUNT=2`, `COMBINED_FALLBACK_COUNT=2` (with `FALLBACK_COUNT=0`), `DISPATCH_OK=true`, and the new cp-fail counter equals 2. This is a direct extension of the existing `cp-fail-*` block (the multi-slot grouped fixture pattern) with two failing reuse copies rather than one.
3. **Item B-2 — `--fallback-counter-file` combined persistence**: A new scenario passing `--fallback-counter-file "$TMPROOT/persist.count"` with one slot configured to relaunch in phase-2 and another configured to fall through to phase-3 Claude. Parse `FALLBACK_COUNT` and `PHASE2_RELAUNCH_COUNT` from `$out`, sum them, and assert the persisted file content equals the sum. This pins the existing combined-sum persistence behavior.
4. **Item C — argv-shape assertion**: Extend the existing competition-notice scenario (the block that already uses an `agent` slot pointing at `agents/reviewer-structure.md`). Add `grep -Fq -- '--agent-file' "$codex_log"` plus an `agents/reviewer-structure.md` match assertion so the harness explicitly proves the dispatcher threads the `agent` field through as `--agent-file <path>` to the external launcher argv. Three or four new assertion lines, no new fixture file required.

### UPDATED: `skills/design/scripts/test-plan-review-loop.sh`
Address FINDING_4 for the loop consumer:
- Extend the inline `printf 'DISPATCH_OK=...\nFALLBACK_COUNT=...\n...'` stubs (existing happy-path and degraded-path stub call sites) to also emit `PHASE2_RELAUNCH_COUNT=0\nCOMBINED_FALLBACK_COUNT=0\n` so every existing scenario passes the new KV through with consistent value. Existing assertions remain valid because `COMBINED_FALLBACK_COUNT=0` does not change degradation outcome under existing fixtures.
- Add one new scenario (or extend an existing one) where the dispatcher stub emits `FALLBACK_COUNT=0` and `COMBINED_FALLBACK_COUNT=<floor_half + 1>` with `STATIC_DISPATCH_OK=true`. Assert `DEGRADED_PANEL=1` on the loop's stdout — proving the new comparison fires when only the COMBINED path crosses the threshold.

### UPDATED: `skills/design/scripts/test-dispatch-plan-review-panel.sh`
Address FINDING_4 for the dispatch consumer:
- Extend the dispatcher stub helper (the `cat >` heredoc around `W_STUB_FALLBACK_COUNT` consumption) to also emit `COMBINED_FALLBACK_COUNT=${W_STUB_COMBINED_FALLBACK_COUNT:-$fc}` (defaults to FALLBACK_COUNT for back-compat with existing scenarios). Also emit `PHASE2_RELAUNCH_COUNT=${W_STUB_PHASE2_RELAUNCH_COUNT:-0}` for completeness.
- Add one new scenario with `W_STUB_FALLBACK_COUNT=0`, `W_STUB_COMBINED_FALLBACK_COUNT=<floor_half + 1>`, `W_STUB_STATIC_OK=true`. Assert `DEGRADED_ROUND=true` on dispatch-plan-review-panel.sh stdout, confirming the new comparison path is exercised.

### UPDATED: `skills/design/scripts/test-decompose-panel-dispatch.sh`
Address FINDING_4 for the decompose-panel consumer:
- Same stub extension as test-dispatch-plan-review-panel.sh (`W_STUB_COMBINED_FALLBACK_COUNT` defaults to `$fc`, `W_STUB_PHASE2_RELAUNCH_COUNT` defaults to `0`).
- Add one new scenario with `W_STUB_FALLBACK_COUNT=0`, `W_STUB_COMBINED_FALLBACK_COUNT=<floor_half + 1>`, `W_STUB_STATIC_OK=true`. Assert `DEGRADED_PANEL=true` on decompose-panel-dispatch.sh stdout.

Trailing harness footers (`assert_*` helpers, `summarise` calls) remain unchanged.

## Approach

The fix preserves the existing waterfall semantics 1:1 — the only behavior changes are: (a) one additional stdout KV from `dispatch-with-waterfall.sh`, (b) three design consumers now reason about degradation using `COMBINED_FALLBACK_COUNT` instead of phase-3-only `FALLBACK_COUNT`, (c) the no-findings short-circuit in `plan-review-loop.sh` honors the same degradation signal as the main path. The defensive fallback (default `COMBINED_FALLBACK_COUNT` to `FALLBACK_COUNT` via the existing `''|*[!0-9]*)` guard) keeps the consumers compatible with any imaginable downgrade path; FINDING_2 from review confirmed the empty-string init is mandatory for that guard to activate.

The `--fallback-counter-file` persistence already uses `combined_fallback` (see the existing `printf '%s\n' "$((prior + combined_fallback))"` line in `scripts/dispatch-with-waterfall.sh`). Item B-2 is a coverage gap, not a behavior gap — the new test pins the existing combined-sum behavior so a future regression would surface.

The consumer harness updates (FINDING_4) are mandatory for the design-consumer changes to be regression-proof. The three test files use slightly different stub patterns (inline `printf` for `test-plan-review-loop.sh` vs `W_STUB_*` env vars for the other two), so the test changes are structurally varied but conceptually identical: each stub emits `COMBINED_FALLBACK_COUNT`, each harness gains one targeted degradation-threshold scenario where only the COMBINED value crosses the threshold.

## Edge cases

- **Older waterfall consumer mismatch**: a design consumer running an updated `dispatch-with-waterfall.sh` will see the new KV; a design consumer reading an older waterfall (e.g., during a partial deploy) will see `COMBINED_FALLBACK_COUNT` absent and fall back to `FALLBACK_COUNT` via the numeric guard. Same degradation result as today.
- **Empty / non-numeric KV**: the numeric guard handles whitespace, empty string, and non-digit inputs identically to the existing `FALLBACK_COUNT` guard pattern; no new validation needed. The `""` (not `"0"`) initialization in plan-review-loop.sh is what makes the guard fire when the dispatcher emits no `COMBINED_FALLBACK_COUNT` line.
- **Floor-half boundary**: comparison remains strict `>` so behavior at the exact half boundary is unchanged.
- **Counter-file persistence on zero combined fallback**: when `combined_fallback == 0`, the existing code still rewrites the counter file with `prior + 0`; the new persistence test only triggers under non-zero conditions, so it does not perturb the zero path.
- **Stub argv format**: the `CODEX_STUB_LOG` captures argv via `printf '%s\n' "$*"`, so the new Item C `grep -Fq -- '--agent-file'` assertion is whitespace-tolerant and order-independent.
- **No-findings short-circuit (FINDING_3 path)**: the new local degradation variable must reach both `emit_loop_kvs` call sites — the happy-path emit and the no-findings emit. Compute once near the top of the resolution block (after `FALLBACK_COUNT` / `COMBINED_FALLBACK_COUNT` numeric guards), then reuse.
- **Cp stub multi-fail interaction with other scenarios**: when neither new stub knob is set, behavior must remain byte-identical to today (`CP_STUB_FAIL_TARGET_CONTAINS` triggers exactly one fail). Existing `cp-fail-*` and `cp-warn-*` scenarios use that exact shape and must remain green.

## Failure modes

- **New KV missing from stdout**: a typo or accidental removal of `emit_kv COMBINED_FALLBACK_COUNT ...` would cause design consumers to silently fall back to `FALLBACK_COUNT` via the numeric guard — degradation reasoning would silently regress to the pre-fix state. Mitigation: a new dedicated assertion `assert_line "COMBINED_FALLBACK_COUNT=<N>" "$out"` in the Item B-1 scenario pins the contract; any future drop of the emit would fail the harness loudly. The three consumer harness threshold scenarios (FINDING_4 additions) further pin the contract end-to-end.
- **Consumer regression to phase-3-only logic**: if any of the three design consumers is reverted to read only `FALLBACK_COUNT`, the resulting drift would re-open the original invariant gap. Mitigation: keep the three consumers' parse blocks structurally identical (same comment shape, same numeric guard, same comparison) so a future grep-driven sweep catches the divergence; each consumer's harness now has a dedicated threshold scenario where only `COMBINED_FALLBACK_COUNT` (not `FALLBACK_COUNT`) crosses `floor_half`.
- **Test fixture drift on Item C**: if a later cleanup changes the competition-notice scenario to switch from `agent` to `prompt_file`, the new `--agent-file` assertion would fail loudly. Mitigation: the assertion fail message names the missing argv pattern explicitly so the diagnosis is one-line obvious.
- **Plan-review-loop short-circuit regression (FINDING_3)**: if the no-findings emit is later changed back to a hardcoded literal, the degradation signal would be lost for that branch. Mitigation: the test-plan-review-loop.sh threshold scenario (FINDING_4 addition) should exercise the no-findings branch with `COMBINED_FALLBACK_COUNT > floor_half`, asserting `DEGRADED_PANEL=1` even when zero findings were produced — pinning the FINDING_3 fix end-to-end.

## Testing strategy

Run `bash scripts/test-dispatch-with-waterfall.sh` after each of the four test additions is in place (stub extension, Item B-1, Item B-2, Item C). The existing harness exits non-zero on the first `FAIL:` so each new scenario surfaces incrementally during dev.

Run `bash skills/design/scripts/test-plan-review-loop.sh`, `bash skills/design/scripts/test-dispatch-plan-review-panel.sh`, and `bash skills/design/scripts/test-decompose-panel-dispatch.sh` after the consumer-harness updates land so the new `COMBINED_FALLBACK_COUNT` parse paths and threshold scenarios are exercised.

Then run `make lint` (which dispatches `scripts/relevant-checks.sh`) to confirm bash 3.2 portability and bare-grep-probe hygiene on the modified files, and `make test-plan-review-loop` / `make test-decompose-panel-dispatch` / `make test-dispatch-plan-review-panel` (or `make test` for a full sweep) so any wired Makefile targets are exercised.

No new harness files are created; all additions land in the four existing files (`scripts/test-dispatch-with-waterfall.sh`, `skills/design/scripts/test-plan-review-loop.sh`, `skills/design/scripts/test-dispatch-plan-review-panel.sh`, `skills/design/scripts/test-decompose-panel-dispatch.sh`).


## Acceptance

- `scripts/dispatch-with-waterfall.sh` emits a new stdout key `COMBINED_FALLBACK_COUNT` equal to `FALLBACK_COUNT + PHASE2_RELAUNCH_COUNT`; `scripts/dispatch-with-waterfall.md` documents it in the **Stdout keys** list.
- `skills/design/scripts/dispatch-plan-review-panel.sh`, `skills/design/scripts/plan-review-loop.sh`, and `skills/design/scripts/decompose-panel-dispatch.sh` all parse `COMBINED_FALLBACK_COUNT`, default it to `FALLBACK_COUNT` when absent via the existing `''|*[!0-9]*)` numeric guard (so `plan-review-loop.sh` uses the **empty-string** init, not `"0"`), and use it (instead of phase-3-only `FALLBACK_COUNT`) in the `> floor_half` degradation comparison. Their `.md` siblings document the change.
- `skills/design/scripts/plan-review-loop.sh` no-findings short-circuit no longer hardcodes `DEGRADED_PANEL=0`: it computes the degradation value once and reuses it on both `emit_loop_kvs` call sites so phase-2-only relaunch overload still surfaces `DEGRADED_PANEL=1` even when zero findings were produced.
- `scripts/test-dispatch-with-waterfall.sh` gains: (i) a minimal extension of the embedded `cp` stub so the harness can drive multiple phase-2 reuse-copy failures (`CP_STUB_FAIL_COUNT` or `CP_STUB_FAIL_TARGET_CONTAINS_LIST`); (ii) a new scenario asserting `PHASE2_RELAUNCH_COUNT=2` and `COMBINED_FALLBACK_COUNT=2` (with `FALLBACK_COUNT=0`); (iii) a new scenario passing `--fallback-counter-file` with both phase-2 and phase-3 fallbacks, asserting persisted-file content equals `FALLBACK_COUNT + PHASE2_RELAUNCH_COUNT` parsed from the same run's stdout; (iv) the existing competition-notice `agent`-slot scenario gains a `grep -Fq -- '--agent-file'` assertion plus an `agents/reviewer-structure.md` substring match against `CODEX_STUB_LOG`. Existing scenarios remain green.
- `skills/design/scripts/test-plan-review-loop.sh`, `skills/design/scripts/test-dispatch-plan-review-panel.sh`, and `skills/design/scripts/test-decompose-panel-dispatch.sh` each: (i) extend their dispatcher stubs to emit `COMBINED_FALLBACK_COUNT` (defaulting to FALLBACK_COUNT for back-compat); (ii) gain one targeted threshold scenario where `FALLBACK_COUNT=0` and `COMBINED_FALLBACK_COUNT > floor_half`, asserting the consumer reports `DEGRADED_PANEL=1` / `DEGRADED_ROUND=true`. `test-plan-review-loop.sh` exercises both the main path and the no-findings short-circuit path via the new scenario.
- `make lint` (which dispatches `scripts/relevant-checks.sh`) passes; bash 3.2 portability and bare-grep-probe hygiene hold on every modified file.
- No changes under `skills/review/scripts/` — review-path code reasons from `DISPATCH_OK`, not `FALLBACK_COUNT`, and its `dispatch-panel.md` already documents the combined-WARN behavior accurately.

diff_lines: 140

## Test plan
(no test plan section in plan-file)
