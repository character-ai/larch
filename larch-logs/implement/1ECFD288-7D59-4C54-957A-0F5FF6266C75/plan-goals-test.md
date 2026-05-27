## Goal
Implement issue #2971: [IMPLEMENTING] dispatch-with-waterfall.sh: reuse_slot_result cp abort under set -e when stale ledger row points at deleted source file\n\n## Out-of-Scope Observation.

## Implementation Plan
## Plan

# Plan: dispatch-with-waterfall.sh — fall back to relaunch when `reuse_slot_result` cp fails

## Background

`scripts/dispatch-with-waterfall.sh` runs under `set -euo pipefail`. The grouped-dedup
fallback in the phase-2 loop (`scripts/dispatch-with-waterfall.sh:498-501`) consults
`find_group_ok_for_tool` for a ledger row matching the group and fallback tool. When a
match is found, `reuse_slot_result` (`scripts/dispatch-with-waterfall.sh:316-338`) copies
the source output to the slot's target via `cp -p "$source_output_path" "$target"` and
emits the dedup sidecar + ledger row. If the source file no longer exists on disk (stale
ledger row from a prior run whose outputs were deleted, manual operator cleanup, or any
other vector outside the PR #2962 same-TMPROOT ledger truncation), `cp` exits non-zero
and `set -e` aborts the entire dispatcher.

Step 1c clarifications: the fix must handle **all** `cp` failure modes (not just missing
source) and must include a regression test.

## Files to modify/create

### UPDATED: `scripts/dispatch-with-waterfall.sh`

- Modify `reuse_slot_result` so each I/O step that can plausibly fail (sidecar write,
  ledger append, and the existing `cp -p`) is guarded with `|| { …cleanup…; return 1; }`.
  The cp guard is the canonical shape:
  `cp -p "$source_output_path" "$target" || { rm -f "$target" 2>/dev/null || true; return 1; }`.
  Each later guard cleans the partial target and sidecar with the same `2>/dev/null || true`
  best-effort pattern before returning. This explicitly avoids relying on `set -e` inside
  the function body, because the caller invokes the function in an `if` test which
  suppresses `errexit` propagation for the whole function call (Bash manual).
  `emit_kv` and array assignments at the tail are not guarded (no realistic failure mode
  beyond write-to-FD-3, which would already have surfaced earlier in the run).
- In the phase-2 grouped loop near line 499, change the unconditional call into
  `if reuse_slot_result ...; then continue; fi` so a non-zero return falls through to the
  existing relaunch block (`reset_phase`, `output_for_phase`, `launch_slot`,
  `collect_phase`). No other structural change.
- Add a brief comment near the new conditional documenting that reuse failure (most
  commonly a stale ledger row whose source output has been deleted) falls through to the
  standard phase-2 relaunch path.
- Modify `find_group_ok_for_tool` (`scripts/dispatch-with-waterfall.sh:305-314`) so it
  returns the **most recent** matching `ok` row instead of the first. Awk shape:
  ```awk
  { line = $2 "\t" $4 "\t" $3 }
  END { if (line) print line }
  ```
  with the matching-row guard kept inside the body. This ensures that once a fresh `ok`
  row is appended after a stale-row relaunch, later grouped slots in the same group
  select the new row and dedup correctly instead of re-tripping the stale row.

### UPDATED: `scripts/dispatch-with-waterfall.md`

- In the "Grouped dedup" section, append one sentence documenting that when the phase-2
  reuse copy fails (for any `cp` failure mode — most commonly a stale ledger row pointing
  at a deleted source output), the dispatcher falls through to a normal phase-2 relaunch
  on the fallback tool rather than aborting under `set -e`.
- In the same section, document the most-recent-ok-row selection rule for
  `find_group_ok_for_tool`, so a fresh post-relaunch `ok` row supersedes a stale one.

### UPDATED: `scripts/test-dispatch-with-waterfall.sh`

- Append one new test scenario after the existing fallback_group dedup tests. The scenario
  must exercise the cp-failure path **after** dispatcher startup ledger truncation — not
  by pre-seeding the ledger TSV (the dispatcher truncates it on entry). Two viable shapes
  (the implementer picks whichever fits the existing stub harness cleanest):
  1. **PATH `cp` wrapper**: A stub `cp` shim under `$STUB_BIN/` that exits non-zero on
     its first invocation (or whenever the source path matches a sentinel pattern), and
     passes through to real `cp` thereafter. Because `reuse_slot_result:line 320` is the
     **only** `cp` call inside `dispatch-with-waterfall.sh`, the first failing invocation
     is guaranteed to be the reuse copy.
  2. **Mid-run donor delete**: Configure the stubs so a two-slot grouped manifest is
     handled normally in phase 1 (the donor produces a real `ok` row), then arrange for
     the donor output file to be deleted between phase-1 settlement and phase-2 reuse
     (e.g. via a phase-1 stub side-effect after returning a valid output, or a wrapper
     around the second stub invocation).
- Assertions: dispatcher exits 0; `DISPATCH_OK=true`; the fallback tool's launch counter
  is **strictly greater** than the equivalent counter in the happy-path dedup test,
  proving relaunch fired; each grouped slot's final output contains the fresh output
  content (not the stale donor content); no `.dedup` sidecar exists for the slot that
  relaunched.
- Existing tests (happy-path dedup, phase-1 OK reuse, cap-hit reuse, cross-group, mixed,
  bad-group) must still pass unchanged.

## Approach

Surgical local change. The caller wraps `reuse_slot_result` in an `if` test, so the
function's `return 1` on any guarded I/O failure routes to the existing phase-2
relaunch path. Because Bash disables `errexit` for the entire function-call body when
the function is invoked in an `if` condition, the function explicitly guards each
critical I/O step with `|| { …; return 1; }` rather than relying on `set -e` inside its
own body — otherwise a later sidecar or ledger write failure would be swallowed and
the caller would believe reuse succeeded.

`find_group_ok_for_tool` switches from "first match" to "last match" so a fresh relaunch
`ok` row supersedes a stale one for subsequent grouped slots; this prevents the
relaunch+cp-fail cycle from repeating for every slot in a group.

## Edge cases

- **Source missing**: `cp` exits non-zero before touching the target; the guarded
  `rm -f` cleanup is a no-op. Caller falls through to relaunch.
- **Source unreadable (permission)**: same as missing source; `cp` exits non-zero, no
  target written; cleanup is a no-op.
- **ENOSPC mid-copy**: `cp` may have written a partial target. The guarded
  `rm -f "$target" 2>/dev/null || true` clears it so the subsequent `launch_slot` writes
  into a clean path.
- **Sidecar/ledger write failure after a successful cp**: rare (would imply FS error or
  disk full mid-run). The function cleans up the freshly copied target + any partial
  sidecar and returns non-zero so the caller relaunches.
- **Subsequent grouped slots in the same group when the relaunch produces a new ok row**:
  thanks to the most-recent-ok-row selection rule in `find_group_ok_for_tool`, later
  slots prefer the fresh `ok` row and dedup against it normally. No repeated relaunches.
- **Subsequent grouped slots before any successful relaunch ok row exists**: each slot
  independently consults the ledger, finds the same stale row, attempts reuse, falls
  through, and relaunches. Cost is one extra `cp` probe per grouped slot until the first
  relaunch succeeds (after which most-recent-ok-row picks up the new row).

## Failure modes

1. **Phase-2 relaunch cost is invisible to operators.** `FALLBACK_COUNT` /
   `LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD` (`scripts/dispatch-with-waterfall.sh:517-524`)
   counts **only** phase-3 Claude launches; phase-2 Cursor/Codex relaunches triggered by
   the new fall-through path are not surfaced. Earliest signal: external-tool spend rises
   anomalously across runs without a corresponding `WARN=cost-fallback-exceeded-threshold`
   line. Mitigation: out of scope for this minimum-change fix; tracked separately via OOS
   filing in Step 5b.
2. **`reuse_slot_result` returning non-zero outside the conditional context aborts the
   dispatcher.** If a future edit moves the call out of `if … then … fi`, `set -e` will
   abort again. Earliest signal: the regression test added in this plan would fail.
   Mitigation: the new regression test fixes the contract.
3. **Stale ledger persists across dispatcher invocations and never converges.** PR #2962
   addresses the same-TMPROOT case via ledger truncation. Cross-TMPROOT cases (shared
   storage, mirrored env) remain — this plan does not address them at the source. The
   in-run most-recent-ok-row selection rule mitigates the bug's immediate symptom by
   ensuring a fresh relaunch result wins, but a long-lived shared ledger with old rows
   and no fresh ones still requires per-slot cp-fail/relaunch. Earliest signal: repeated
   relaunches against a long-untouched ledger. Mitigation: deferred; out of scope.

## Testing strategy

- `make test-dispatch-with-waterfall` (or equivalent target via
  `bash scripts/relevant-checks.sh` after the edit) must pass.
- New regression scenario (see Files section) asserts the dispatcher does not abort and
  the fallback tool relaunches for the affected grouped slot when the reuse `cp` fails
  in-run.
- Existing tests in `scripts/test-dispatch-with-waterfall.sh` (happy-path dedup, phase-1
  OK reuse, cap-hit reuse, cross-group, mixed, bad-group) continue to pass unchanged.



## Acceptance

- `scripts/dispatch-with-waterfall.sh` no longer aborts under `set -e` when `reuse_slot_result` cannot copy a stale source file; the dispatcher falls through to the existing phase-2 relaunch path.
- `find_group_ok_for_tool` returns the most recent matching ok row, so a fresh relaunch ok row supersedes a stale one for subsequent grouped slots in the same group.
- All guarded I/O steps in `reuse_slot_result` (cp, sidecar write, ledger append) explicitly return non-zero on failure with best-effort cleanup; the caller wraps the call in an `if` test and falls through to relaunch on any non-zero return.
- A new regression scenario in `scripts/test-dispatch-with-waterfall.sh` exercises the cp-failure path after dispatcher startup ledger truncation (via PATH `cp` wrapper or mid-run donor delete) and asserts the affected grouped slot relaunches with the fallback tool.
- All existing tests in `scripts/test-dispatch-with-waterfall.sh` continue to pass unchanged.
- Sibling contract `scripts/dispatch-with-waterfall.md` documents the new reuse-failure fallback behavior and the most-recent-ok-row selection rule.
- `make lint` (or equivalent via `bash scripts/relevant-checks.sh`) passes after the edit.

diff_lines: 75

## Test plan
(no test plan section in plan-file)
