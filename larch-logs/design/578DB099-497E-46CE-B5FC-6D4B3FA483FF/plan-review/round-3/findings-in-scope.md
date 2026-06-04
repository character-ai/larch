### FINDING_1: Plan targets nonexistent renderer and harness paths
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The plan points implementers at `skills/review/scripts/render-specialist-prompt.sh` and `skills/review/scripts/test-render-specialist-prompt.sh`, but the runtime renderer and harness live under `scripts/`. Following the plan would edit or test nonexistent files, so reviewer-testing plan injection would not affect actual reviewer prompts or CI coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Retarget those subsections to `scripts/render-specialist-prompt.sh` and `scripts/test-render-specialist-prompt.sh` (and `scripts/test-render-specialist-prompt.md` if the contract is updated)
  - From Cursor-Edge: Point the plan at `scripts/test-render-specialist-prompt.sh` and `scripts/test-render-specialist-prompt.md` only.
  - From Codex-Edge: Retarget the renderer and tests to scripts/render-specialist-prompt.sh and scripts/test-render-specialist-prompt.sh; add the reviewer-testing basename exception there
  - From Cursor-Innovation: Retarget to scripts/render-specialist-prompt.sh and scripts/test-render-specialist-prompt.sh (dispatch-panel.sh already calls PLUGIN_ROOT/scripts/render-specialist-prompt.sh)
  - From Codex-Pragmatic: Retarget those plan sections to scripts/render-specialist-prompt.sh and scripts/test-render-specialist-prompt.sh.
  - From Codex-Requirements: Update the plan entries to scripts/render-specialist-prompt.sh, scripts/test-render-specialist-prompt.sh, and the sibling .md contracts, then keep the same reviewer-testing-specific plan-injection test scope

### FINDING_2: No-fallback static drops bypass or disappear from the >50% threshold
- **Reviewer(s)**: Codex-Arch, Cursor-Edge, Codex-Edge, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements, Codex-dyn-denominator-tracing
- **Severity**: important
- **Concern**: The plan relies on no-fallback peer rows but does not specify how dropped static rows are counted. Today a dropped no-fallback static slot can set `STATIC_DISPATCH_OK=false` and hard-stop review-core before threshold math, or be omitted from collected outputs and disappear from the denominator/failure count if the shortcut is relaxed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a minimal plan step to plumb DROPPED_SLOTS_FILE or an equivalent static-drop count into check-reviewer-failure-threshold, distinguish countable reviewer drops from dispatch infrastructure failure, and test 1 of 8 static drops does not fail while 5 of 8 does with dyn drops excluded
  - From Cursor-Edge: Keep intended=emitted static count, but set `--launched-slots` from waterfall success (e.g. `ALL_OUTPUT_FILES` / paths-file line count for static slots only), or fold `DROPPED_SLOTS_FILE` static drops into `FAILED_SLOTS` in `check-reviewer-failure-threshold.sh`.
  - From Codex-Edge: Revise the plan to avoid global --no-fallback on the mixed manifest; either split peer dispatches with the opposite vendor marked absent so only Claude fallback remains, or add an explicit per-slot fallback policy and threshold accounting for dropped static rows
  - From Codex-Innovation: Revise the plan to add a minimal explicit mechanism: split peer/no-peer manifests or add a per-row fallback=false field, and count no-fallback static drops as threshold failures instead of unconditional dispatch-failed.
  - From Cursor-Pragmatic: Only bypass threshold on dispatch failure when no static outputs remain, or compute `STATIC_DISPATCH_OK` per archetype (false only when both peers fail); add a harness case: Cursor drop + Codex OK must not panel-fail
  - From Codex-Pragmatic: Count no-fallback dropped static rows as failed slots in the threshold path and do not bypass the >50% threshold solely because STATIC_DISPATCH_OK=false; reserve dispatch-failed for true dispatcher/infrastructure failure.
  - From Codex-Requirements: Specify the minimal plumbing: surface no-fallback dropped static rows as failed threshold records, do not make any single dropped peer an unconditional dispatch-failed hard stop, and add a review-core/dispatch test where one peer drops but the 8-slot threshold still passes while >4 drops fail
  - From Codex-dyn-denominator-tracing: Specify the minimal no-duplicate path: add row-level fallback suppression or equivalent in dispatch-with-waterfall, and ensure dropped static peer failures are counted by check-reviewer-failure-threshold instead of bypassing it via static_dispatch_ok; add a 1-of-8-failed test that remains OK and a >4-of-8-failed test that stops

### FINDING_3: Peer-row no-fallback cannot be expressed safely with the current global dispatcher flag
- **Reviewer(s)**: Cursor-Edge, Codex-Edge, Codex-Innovation, Cursor-Requirements, Codex-dyn-denominator-tracing, Cursor-dyn-vendor-mirror-completeness, Codex-dyn-vendor-mirror-completeness
- **Severity**: important
- **Concern**: The plan describes row-specific no-fallback behavior for Cursor rows that have Codex peers, but `dispatch-with-waterfall.sh` only supports a call-level `--no-fallback`. Leaving fallback enabled can duplicate Codex peer work; applying the global flag too broadly can disable intended Claude fallback for both-down or single-vendor rows, including dynamic rows in the shared manifest.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Spell out orchestration: either (minimal) two waterfall passes — Codex rows with `cursor-present false` + `--no-fallback`, Cursor rows with `codex-present false` and normal Claude fallback — then merge outputs; or add a per-slot `no_fallback` (or equivalent) field to manifest rows and teach `dispatch-with-waterfall.sh` to honor it without a global flag.
  - From Codex-Edge: Revise the plan to avoid global --no-fallback on the mixed manifest; either split peer dispatches with the opposite vendor marked absent so only Claude fallback remains, or add an explicit per-slot fallback policy and threshold accounting for dropped static rows
  - From Codex-Innovation: Revise the plan to add a minimal explicit mechanism: split peer/no-peer manifests or add a per-row fallback=false field, and count no-fallback static drops as threshold failures instead of unconditional dispatch-failed.
  - From Cursor-Requirements: Pass `--no-fallback` only when both `CURSOR_AVAILABLE` and `CODEX_AVAILABLE` are true; omit it otherwise so Phase-3 Claude fallback stays. Spell this out in `dispatch-panel.md` (differs from `/design`, which pads both-down before dispatch).
  - From Codex-dyn-denominator-tracing: Specify the minimal no-duplicate path: add row-level fallback suppression or equivalent in dispatch-with-waterfall, and ensure dropped static peer failures are counted by check-reviewer-failure-threshold instead of bypassing it via static_dispatch_ok; add a 1-of-8-failed test that remains OK and a >4-of-8-failed test that stops
  - From Cursor-dyn-vendor-mirror-completeness: In `dispatch-panel.sh` (and `dispatch-panel.md`), specify the `/design`-equivalent contract explicitly: append `--no-fallback` to the single `dispatch-with-waterfall.sh` invocation only when `CODEX_AVAILABLE=true` and `CURSOR_AVAILABLE=true`; omit it for single-vendor and both-down manifests so Phase-2/3 remain available; set `--codex-present` from `CODEX_AVAILABLE` (replace `codex_present_for_waterfall=false` at dispatch-panel.sh:398). Add harness checks (per skills/design/scripts/test-dispatch-plan-review-panel.sh:108) that stub logs include `--no-fallback` for both-vendor cases and exclude it for both-down / single-vendor cases. Dynamic Codex twins inherit the same rule via the shared manifest—no separate per-row mechanism.
  - From Codex-dyn-vendor-mirror-completeness: Simplest fix: explicitly mirror /design by passing global --no-fallback only for a manifest whose Cursor rows all have same-run Codex peers, and use the normal waterfall path for both-down or peerless rows; otherwise add a small row-level no_fallback field to dispatch-with-waterfall.sh and test static plus dynamic Cursor-fails-with-Codex-peer cases.

### FINDING_4: Review-core test contract contradicts STATIC_SLOT_COUNT denominator rule
- **Reviewer(s)**: Cursor-dyn-denominator-tracing
- **Severity**: important
- **Concern**: The `test-review-core.sh` contract text says `--intended-slots` is availability-derived, which conflicts with the plan’s rule that `STATIC_SLOT_COUNT` is the single source of truth. That could cause implementers to reintroduce vendor-availability arithmetic and recreate phantom padding or denominator mismatches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-denominator-tracing: Align `test-review-core.sh` / `test-review-core.md` with `dispatch-panel.sh` + `review-core.sh`: assert `check-reviewer-failure-threshold.sh` receives `--intended-slots` and `--launched-slots` both set from parsed `STATIC_SLOT_COUNT` (e.g. 4 single-vendor, 8 both-vendor), not from availability flags

### FINDING_5: Codex peer rows may be skipped because waterfall still receives `--codex-present false`
- **Reviewer(s)**: Cursor-dyn-reversal-risk-audit
- **Severity**: important
- **Concern**: The plan names the #2449 guard `codex_present_for_waterfall="false"` in decisions but does not include updating it in the dispatch-panel edit list. If it remains false, manifest rows with `tool:"codex"` are skipped in phase 1 even after Codex rows are re-added, leaving the panel Cursor-only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-reversal-risk-audit: In `dispatch-panel.sh` set `codex_present_for_waterfall="$CODEX_AVAILABLE"` (mirror dispatch-plan-review-panel.sh:241) and assert in test-dispatch-panel.sh that the waterfall argv passes `--codex-present true` when Codex is available
