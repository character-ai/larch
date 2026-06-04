### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:52-57
- **Concern**: Plan cites `skills/review/scripts/render-specialist-prompt.sh` and `skills/review/scripts/test-render-specialist-prompt.sh` but both live under `scripts/`. Scenario: An implementer following the plan paths will edit or test non-existent files and miss the real renderer where plan injection must land
- **Proposed resolution**: Retarget those subsections to `scripts/render-specialist-prompt.sh` and `scripts/test-render-specialist-prompt.sh` (and `scripts/test-render-specialist-prompt.md` if the contract is updated)

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:28,41-43; scripts/dispatch-with-waterfall.sh:436-449,535-540,559-588; skills/review/scripts/review-core.sh:451-456
- **Concern**: The plan adds --no-fallback peer rows but does not account for dropped static slots in the >50% threshold path. Scenario: With both vendors available, one failed Cursor or Codex static slot under --no-fallback sets STATIC_DISPATCH_OK=false and is omitted from ALL_OUTPUT_FILES, so review-core either hard-fails on a single slot before the threshold or, if that shortcut is relaxed, the threshold misses the dropped failure entirely
- **Proposed resolution**: Add a minimal plan step to plumb DROPPED_SLOTS_FILE or an equivalent static-drop count into check-reviewer-failure-threshold, distinguish countable reviewer drops from dispatch infrastructure failure, and test 1 of 8 static drops does not fail while 5 of 8 does with dyn drops excluded

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/dispatch-panel.sh:398-406
- **Concern**: Plan requires per-row Codex-peer `--no-fallback`, but `dispatch-with-waterfall.sh` only supports a global `--no-fallback` (line 53).. Scenario: With `codex-present true`, a failed Cursor static/dynamic row still enters phase-2 Codex fallback (`scripts/dispatch-with-waterfall.sh:451-461`) while a Codex peer row for the same archetype is already in the manifest — duplicate Codex runs/cost (#2449 regression). A global `--no-fallback` on the single manifest also disables phase-3 Claude for the both-vendors-down Cursor-only rows the plan requires.
- **Proposed resolution**: Spell out orchestration: either (minimal) two waterfall passes — Codex rows with `cursor-present false` + `--no-fallback`, Cursor rows with `codex-present false` and normal Claude fallback — then merge outputs; or add a per-slot `no_fallback` (or equivalent) field to manifest rows and teach `dispatch-with-waterfall.sh` to honor it without a global flag.

### FINDING_4:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/review/scripts/review-core.sh:451-456
- **Concern**: Plan sets `--intended-slots` and `--launched-slots` both to `STATIC_SLOT_COUNT` (emitted manifest rows), not to paths actually launched/collected.. Scenario: Under `--no-fallback`, dropped Cursor rows are omitted from `ALL_OUTPUT_FILES` (`dispatch-with-waterfall.sh:538-540`) and never reach `collector-results.env`, while `NEVER_LAUNCHED` stays 0 because intended equals launched — static failures can be under-counted and a degraded panel can pass the >50% gate.
- **Proposed resolution**: Keep intended=emitted static count, but set `--launched-slots` from waterfall success (e.g. `ALL_OUTPUT_FILES` / paths-file line count for static slots only), or fold `DROPPED_SLOTS_FILE` static drops into `FAILED_SLOTS` in `check-reviewer-failure-threshold.sh`.

### FINDING_5:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/dispatch-panel.sh:56-57 (plan)
- **Concern**: Wrong harness path: plan lists `skills/review/scripts/test-render-specialist-prompt.sh`; repo has `scripts/test-render-specialist-prompt.sh` (+ `.md`).. Scenario: Implementer adds or updates a non-existent harness; plan-injection regression for folded plan-fidelity never runs in CI.
- **Proposed resolution**: Point the plan at `scripts/test-render-specialist-prompt.sh` and `scripts/test-render-specialist-prompt.md` only.

### FINDING_6:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/render-specialist-prompt.sh:284-286
- **Concern**: Plan targets skills/review/scripts/render-specialist-prompt.sh, but the runtime renderer is scripts/render-specialist-prompt.sh and still injects plans only for generic diffs. Scenario: The folded reviewer-testing plan-fidelity scan will not receive plan context on docs-only, test-only, or generated-only diffs, so the proposed coverage preservation silently fails
- **Proposed resolution**: Retarget the renderer and tests to scripts/render-specialist-prompt.sh and scripts/test-render-specialist-prompt.sh; add the reviewer-testing basename exception there

### FINDING_7:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/dispatch-with-waterfall.sh:32-53,436-449; skills/review/scripts/review-core.sh:451-456
- **Concern**: The plan relies on per-row no-fallback semantics, but dispatch-with-waterfall.sh only has a global --no-fallback, and review-core treats any static no-fallback drop as dispatch-failed. Scenario: With both vendors available, leaving fallback on duplicates peer reviews; using global --no-fallback drops failed rows from collection and hard-stops on one static failure instead of applying the >50% threshold, and can also break both-down Claude fallback
- **Proposed resolution**: Revise the plan to avoid global --no-fallback on the mixed manifest; either split peer dispatches with the opposite vendor marked absent so only Claude fallback remains, or add an explicit per-slot fallback policy and threshold accounting for dropped static rows

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:52-57
- **Concern**: Plan cites render-specialist-prompt under skills/review/scripts/. Scenario: Implementation edits a non-existent path; folded plan-fidelity testing injection never lands
- **Proposed resolution**: Retarget to scripts/render-specialist-prompt.sh and scripts/test-render-specialist-prompt.sh (dispatch-panel.sh already calls PLUGIN_ROOT/scripts/render-specialist-prompt.sh)

### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/dispatch-with-waterfall.sh:53; scripts/dispatch-with-waterfall.sh:436-448; skills/review/scripts/review-core.sh:451-456
- **Concern**: Peer-row no-fallback cannot be expressed safely with the current dispatcher. Scenario: The plan needs Cursor rows with Codex peers to skip Codex fallback, while rows without peers keep Claude fallback and the >50% threshold still applies. The dispatcher only has global --no-fallback; using it makes any static drop set STATIC_DISPATCH_OK=false and review-core hard-fails on one failed slot instead of applying the planned threshold.
- **Proposed resolution**: Revise the plan to add a minimal explicit mechanism: split peer/no-peer manifests or add a per-row fallback=false field, and count no-fallback static drops as threshold failures instead of unconditional dispatch-failed.

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/review/scripts/review-core.sh:453-456
- **Concern**: `STATIC_DISPATCH_OK=false` hard-stops before threshold when any static row drops. Scenario: With dual-vendor `--no-fallback`, a dropped Cursor row sets `STATIC_DISPATCH_OK=false` even if the Codex peer for the same archetype succeeded; `review-core` writes `THRESHOLD_OK=false` / `dispatch-failed` and skips `--intended-slots` math
- **Proposed resolution**: Only bypass threshold on dispatch failure when no static outputs remain, or compute `STATIC_DISPATCH_OK` per archetype (false only when both peers fail); add a harness case: Cursor drop + Codex OK must not panel-fail

### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/render-specialist-prompt.sh:284-297; skills/review/scripts/dispatch-panel.sh:174
- **Concern**: Plan targets nonexistent reviewer prompt renderer/test paths. Scenario: The plan names skills/review/scripts/render-specialist-prompt.sh and skills/review/scripts/test-render-specialist-prompt.sh, but runtime calls and tests use scripts/render-specialist-prompt.sh and scripts/test-render-specialist-prompt.sh, so the testing-lane plan injection would not affect actual reviewers.
- **Proposed resolution**: Retarget those plan sections to scripts/render-specialist-prompt.sh and scripts/test-render-specialist-prompt.sh.

### FINDING_12:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/review-core.sh:451-456; scripts/dispatch-with-waterfall.sh:436-449
- **Concern**: No-fallback static peer drops bypass the intended >50% threshold. Scenario: With both vendors enabled, one static peer failure under --no-fallback makes dispatch-with-waterfall set STATIC_DISPATCH_OK=false and omit the dropped output; review-core then writes THRESHOLD_OK=false before check-reviewer-failure-threshold.sh runs, so a 7-of-8 healthy panel can stall as dispatch-failed.
- **Proposed resolution**: Count no-fallback dropped static rows as failed slots in the threshold path and do not bypass the >50% threshold solely because STATIC_DISPATCH_OK=false; reserve dispatch-failed for true dispatcher/infrastructure failure.

### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/review/scripts/dispatch-panel.sh:398-406
- **Concern**: Plan says Cursor rows with Codex peers use `--no-fallback` but also requires Phase-3 Claude fallback when both vendors are down or only one vendor is available. Scenario: `dispatch-with-waterfall.sh` only has a global `--no-fallback` flag; always passing it drops both-down and single-vendor slots as `tool-absent` with no Claude pad, contradicting Edge cases lines 163-171
- **Proposed resolution**: Pass `--no-fallback` only when both `CURSOR_AVAILABLE` and `CODEX_AVAILABLE` are true; omit it otherwise so Phase-3 Claude fallback stays. Spell this out in `dispatch-panel.md` (differs from `/design`, which pads both-down before dispatch).

### FINDING_14:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: .cache/larch/sessions/claude-design-larch4-wl4jNr/plan.txt:52-57; scripts/render-specialist-prompt.sh:1; scripts/test-render-specialist-prompt.sh:1
- **Concern**: The plan targets nonexistent render-specialist files under skills/review/scripts. Scenario: Reviewer-testing will not receive the implementation plan for the folded plan-fidelity scan if the implementer follows the listed paths; the real renderer and harness live under scripts/
- **Proposed resolution**: Update the plan entries to scripts/render-specialist-prompt.sh, scripts/test-render-specialist-prompt.sh, and the sibling .md contracts, then keep the same reviewer-testing-specific plan-injection test scope

### FINDING_15:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: .cache/larch/sessions/claude-design-larch4-wl4jNr/plan.txt:28,41-43,147-148; scripts/dispatch-with-waterfall.sh:405-453,566-578; skills/review/scripts/review-core.sh:446-456
- **Concern**: The no-fallback plan does not say how dropped peer rows feed the >50% failure threshold. Scenario: dispatch-with-waterfall --no-fallback omits dropped slots from ALL_OUTPUT_FILES and marks STATIC_DISPATCH_OK=false; review-core currently hard-fails on that flag, so one failed Cursor peer in an 8-slot panel can fail the round instead of counting as 1 of 8, or if the bypass is removed the failure can disappear from collector results
- **Proposed resolution**: Specify the minimal plumbing: surface no-fallback dropped static rows as failed threshold records, do not make any single dropped peer an unconditional dispatch-failed hard stop, and add a review-core/dispatch test where one peer drops but the 8-slot threshold still passes while >4 drops fail

### FINDING_16:
- **Reviewer(s)**: Cursor-dyn-denominator-tracing
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:41-43; plan.txt:141-142; skills/review/scripts/review-core.sh:451-452
- **Concern**: `test-review-core.sh` contract text says `--intended-slots` is availability-derived, contradicting the plan’s STATIC_SLOT_COUNT single-source rule and today’s only `--launched-slots` pass-through. Scenario: An implementer following the test bullet reintroduces `CODEX_AVAILABLE`/`CURSOR_AVAILABLE` arithmetic in `review-core.sh` (or stubs that assert it), recreating phantom never-launched padding or an 8-vs-4 denominator mismatch versus emitted manifest rows
- **Proposed resolution**: Align `test-review-core.sh` / `test-review-core.md` with `dispatch-panel.sh` + `review-core.sh`: assert `check-reviewer-failure-threshold.sh` receives `--intended-slots` and `--launched-slots` both set from parsed `STATIC_SLOT_COUNT` (e.g. 4 single-vendor, 8 both-vendor), not from availability flags

### FINDING_17:
- **Reviewer(s)**: Codex-dyn-denominator-tracing
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/review-core.sh:446-456; scripts/dispatch-with-waterfall.sh:436-449; <TMPDIR>/plan.txt:28,41-43
- **Concern**: The plan preserves review-core's static_dispatch_ok short-circuit while relying on no-fallback peer rows for denominator scaling. Scenario: With both vendors available, one failed Cursor peer under global --no-fallback makes dispatch-with-waterfall set STATIC_DISPATCH_OK=false, so review-core hard-stops before the intended 8-slot >50% threshold; without no-fallback, the same failed Cursor row can still run Codex despite its Codex peer
- **Proposed resolution**: Specify the minimal no-duplicate path: add row-level fallback suppression or equivalent in dispatch-with-waterfall, and ensure dropped static peer failures are counted by check-reviewer-failure-threshold instead of bypassing it via static_dispatch_ok; add a 1-of-8-failed test that remains OK and a >4-of-8-failed test that stops

### FINDING_18:
- **Reviewer(s)**: Cursor-dyn-vendor-mirror-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/dispatch-panel.sh:398-406
- **Concern**: Plan says Cursor rows with a Codex peer pass `--no-fallback` / equivalent, but `dispatch-with-waterfall.sh` only exposes a single call-level `--no-fallback` (scripts/dispatch-with-waterfall.sh:53); there is no per-manifest-row flag and `fallback_group` was removed. `/design` applies `--no-fallback` to the whole panel when both vendors are present (skills/design/scripts/dispatch-plan-review-panel.sh:239-247); both-absent plan-review bypasses the waterfall entirely (skills/design/scripts/dispatch-plan-review-panel.sh:97-165). Review both-absent must keep Phase-3 Claude fallback (plan.txt Edge cases; dispatch-panel.md:5-6). Passing `--no-fallback` unconditionally (or only on static rows in prose) disables Phase 2/3 for every manifest row—including both-down Cursor-primary rows and single-vendor panels—so failed Cursor static/dynamic slots can neither fall back to Claude nor match the documented both-down behavior; passing it only in static emission prose cannot work because one waterfall call dispatches static and dynamic rows together (dispatch-panel.sh:386-406).. Scenario: Both vendors up: a failed `cursor-specialist-*` or `dyn-*` row Phase-2-retries on Codex while the peer `codex-specialist-*` / `dyn-*-codex-output.txt` row already ran, duplicating the archetype (plan Failure modes #2). Both vendors down or one vendor down: global `--no-fallback` drops failed primaries with no Claude backfill, silently shrinking coverage below the plan’s “one Cursor-primary row per archetype that waterfalls to Claude” contract.
- **Proposed resolution**: In `dispatch-panel.sh` (and `dispatch-panel.md`), specify the `/design`-equivalent contract explicitly: append `--no-fallback` to the single `dispatch-with-waterfall.sh` invocation only when `CODEX_AVAILABLE=true` and `CURSOR_AVAILABLE=true`; omit it for single-vendor and both-down manifests so Phase-2/3 remain available; set `--codex-present` from `CODEX_AVAILABLE` (replace `codex_present_for_waterfall=false` at dispatch-panel.sh:398). Add harness checks (per skills/design/scripts/test-dispatch-plan-review-panel.sh:108) that stub logs include `--no-fallback` for both-vendor cases and exclude it for both-down / single-vendor cases. Dynamic Codex twins inherit the same rule via the shared manifest—no separate per-row mechanism.

### FINDING_19:
- **Reviewer(s)**: Codex-dyn-vendor-mirror-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:8,25-28,159-160,176; scripts/dispatch-with-waterfall.sh:32-53,436-463; skills/design/scripts/dispatch-plan-review-panel.sh:239-246
- **Concern**: Plan describes row-specific no-fallback for Cursor rows with Codex peers, but the existing dispatcher only has a global --no-fallback switch and the plan does not add row-level support or specify an exact global/split-manifest strategy.. Scenario: Dynamic and static Cursor rows can still Phase-2 into Codex if --no-fallback is omitted; if the global flag is applied too broadly, rows without peers lose intended Claude fallback.
- **Proposed resolution**: Simplest fix: explicitly mirror /design by passing global --no-fallback only for a manifest whose Cursor rows all have same-run Codex peers, and use the normal waterfall path for both-down or peerless rows; otherwise add a small row-level no_fallback field to dispatch-with-waterfall.sh and test static plus dynamic Cursor-fails-with-Codex-peer cases.

### FINDING_20:
- **Reviewer(s)**: Cursor-dyn-reversal-risk-audit
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/dispatch-panel.sh:398-399
- **Concern**: #2449 guard `codex_present_for_waterfall="false"` is named in Decisions but not in the dispatch-panel edit list. Scenario: Manifest `tool:"codex"` rows are skipped in phase 1 because `present_for_tool` requires `--codex-present true` (scripts/dispatch-with-waterfall.sh:175-178,418-426); panel stays Cursor-only despite re-added Codex rows
- **Proposed resolution**: In `dispatch-panel.sh` set `codex_present_for_waterfall="$CODEX_AVAILABLE"` (mirror dispatch-plan-review-panel.sh:241) and assert in test-dispatch-panel.sh that the waterfall argv passes `--codex-present true` when Codex is available
