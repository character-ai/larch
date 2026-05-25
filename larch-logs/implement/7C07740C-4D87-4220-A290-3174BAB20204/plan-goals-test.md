## Goal
Tighten ship-pr.sh require_key and is_bool validators to match write_initial_state's full key set

## Implementation Plan
## Plan


## Files to modify/create

### UPDATED: `scripts/ship-pr.sh`

Expand the two validator loops at the bottom of the argv-validation block (the block that runs after `validate_state_syntax` and before the `MANIFEST_PATH` jq probe) so the runtime-required key set matches the writer.

- **`require_key` loop**: append these 7 keys to the existing list (`PHASE BRANCH_NAME ISSUE_NUMBER ... MANIFEST_PATH TOOL_LABEL`):
  - `BAIL_REASON`
  - `BAIL_FAILURE_DETAIL_LOG`
  - `DESIGN_ONLY_DONE`
  - `EXPECTED_SESSION_ID`
  - `EXPECTED_TMPDIR_BASENAME_PREFIX`
  - `NO_LOGS_COMMIT`
  - `IMPLEMENT_TMPDIR`
- **`is_bool` loop** (the loop that asserts `REPO_UNAVAILABLE FORKED_TARGET ... CI_PASSED OOS_PENDING` are `true`/`false`): append `DESIGN_ONLY_DONE` and `NO_LOGS_COMMIT`. Both keys are written by `write_initial_state` as `true`/`false` literals, so the same `die_usage` line shape already covers them.

No other code changes. Do not touch the `write_initial_state` writer block, the per-flag CR/LF validators above the for loops, or any of the `INIT_*_SET` plumbing.

### UPDATED: `scripts/ship-pr.md`

Update the `Schema note:` paragraph so the asymmetry is no longer described as intentional:

- Replace the "validates a subset so legacy state files missing newer informational keys are not rejected (asymmetry tracked in issue #2752)" wording with prose stating that `require_key` now validates the full key set written by `write_initial_state()`, and that mid-session `ship-pr.sh` upgrades against a state file written by an older version may need `--force-init-state true` to regenerate.
- Keep the references to issue #2742 and the drift-detection follow-up (#2753) intact — those track separate work and remain in scope only for the follow-up.
- Do not edit other paragraphs in `scripts/ship-pr.md`.

### UPDATED: `scripts/test-ship-pr.sh`

Extend the `write_state()` helper so the hand-composed state file satisfies the tightened `require_key` loop:

- Append `NO_LOGS_COMMIT=false` to the `cat <<EOF` heredoc that `write_state` emits. The heredoc already writes the other 6 of the 7 newly-required keys (`BAIL_REASON=`, `BAIL_FAILURE_DETAIL_LOG=`, `DESIGN_ONLY_DONE=false`, `EXPECTED_SESSION_ID=`, `EXPECTED_TMPDIR_BASENAME_PREFIX=claude-implement-test-`, `IMPLEMENT_TMPDIR=$state_tmpdir`); only `NO_LOGS_COMMIT` is missing today.
- The `false` literal mirrors `write_initial_state`'s `${NO_LOGS_COMMIT:-false}` default and matches the bool-only assertion this PR adds to the `is_bool` loop.
- Do not edit other helpers in `scripts/test-ship-pr.sh`. The included `scripts/test-ship-pr-fix-loop-2632.inc.sh` reuses the same `write_state` helper and is therefore covered by this single edit; no second test file changes.

## Approach

Surgical edit to two existing for loops in `scripts/ship-pr.sh`, one new line in `scripts/test-ship-pr.sh`'s `write_state` heredoc, and one paragraph in `scripts/ship-pr.md`. No new functions, no new helpers, no schema-drift automation (that is #2753). The require_key/is_bool patterns already exist immediately adjacent to each other in the same validator block — extending them is a one-token-per-key change.

Implementation order:

1. Edit `scripts/ship-pr.sh` `require_key` loop (append 7 keys, preserving line-break style of surrounding code).
2. Edit the same file's `is_bool` loop (append 2 keys).
3. Edit `scripts/test-ship-pr.sh`'s `write_state()` heredoc to add `NO_LOGS_COMMIT=false`.
4. Edit the `Schema note:` paragraph in `scripts/ship-pr.md` per the wording above.
5. Run `bash scripts/relevant-checks.sh` (or `make lint`) until clean.
6. Run `bash scripts/test-ship-pr.sh` to confirm the harness still passes — without the step-3 edit it would die on the first `run_subject` call after a `write_state`.

## Edge cases

- **All emitted keys have valid initial values from `write_initial_state`.** `BAIL_REASON` and `BAIL_FAILURE_DETAIL_LOG` are emitted as empty (`KEY=`), `DESIGN_ONLY_DONE` and `NO_LOGS_COMMIT` as `false` literals, the `EXPECTED_*` keys from derived values, `IMPLEMENT_TMPDIR` from the validated argv. `require_key` checks key presence (`state_has_key`), not non-emptiness, so empty values pass naturally.
- **`is_bool` semantics.** Both keys added to the `is_bool` loop are unconditionally written as `false`/`true` by `write_initial_state` on cold start and never re-written to a non-bool value by any other code path in `ship-pr.sh`. The new assertions do not regress any production path.
- **Mid-session `ship-pr.sh` upgrade.** If a session's state file was written by an older `ship-pr.sh` lacking some of the 7 newly-required keys, a re-invocation under the new version will `die_usage state-file missing required key: <X>`. Recovery is documented (and pre-existing): re-run with `--force-init-state true` to regenerate the file. This narrow risk is documented in the updated `Schema note:` paragraph.
- **`MANIFEST_PATH` non-empty validator.** The existing `MANIFEST_PATH must be empty or a readable JSON file` check runs immediately after the new validators. It is unaffected because the new keys are added to the loops above it, not interleaved.
- **Test harness coverage.** The `scripts/test-ship-pr.sh` `write_state()` helper bypasses `write_initial_state` and would die in `require_key` without the heredoc update; the include file `scripts/test-ship-pr-fix-loop-2632.inc.sh` calls the same helper and is covered transitively. No other test files compose `ship-pr-state.sh` by hand.

## Failure modes

1. **Mid-session upgrade breakage.** Earliest signal: `ship-pr.sh` exits non-zero with `state-file missing required key: <X>` on the first invocation after a `larch:upgrade-larch` mid-`/implement` run. Mitigation: documented `--force-init-state true` recovery in `scripts/ship-pr.md`.
2. **Hidden caller that pre-composes `ship-pr-state.sh`.** Some external tooling may write a state file directly instead of letting `write_initial_state` run. Earliest signal: the same `die_usage` from `require_key` on the first ship-pr invocation. Mitigation: the documented `Backward compatibility:` paragraph already names this pre-composing pattern; callers must include all required keys, and the updated `Schema note:` makes the new requirements explicit. The in-repo example of this pattern is `scripts/test-ship-pr.sh`'s `write_state`, fixed by this PR.
3. **Scope creep into schema drift automation.** The fix must not start automating writer/doc drift detection (that is #2753). Earliest signal: review findings or commits that touch `skills/implement/SKILL.md` key tables or add new drift-check scripts. Mitigation: PR scope limited to the two for loops, the `write_state` heredoc, and the single `Schema note:` paragraph.

## Testing strategy

- Run `bash scripts/relevant-checks.sh` (Makefile `make lint` equivalent) and resolve any lint complaints before commit.
- Run `bash scripts/test-ship-pr.sh` to exercise both the cold-start `write_initial_state` -> `require_key` paths and the heredoc-composed paths through `write_state`. With the heredoc edit included, every `write_state` -> `run_subject` scenario continues to pass; without it, scenarios die on the new `NO_LOGS_COMMIT` requirement.
- The included `scripts/test-ship-pr-fix-loop-2632.inc.sh` is run as part of `test-ship-pr.sh` and reuses the same `write_state` helper, so it is covered without an additional edit.
- Run `bash scripts/test-ship-pr-rebase-phase14.sh` (it does not hand-compose a state file and therefore is unaffected by the heredoc edit; it still exercises the surrounding validators).
- Spot-check: temporarily remove one of the 7 newly-required keys from a test state file and confirm the new error message fires (manual one-off; no new committed test).
- No new test files are added — the existing harnesses already cover the tightened path once `write_state` includes `NO_LOGS_COMMIT`. A new test asserting the specific 7 keys would duplicate `write_initial_state`'s own coverage and add drift-prone literal lists; that drift-detection work belongs to #2753.


## Acceptance

- `scripts/ship-pr.sh` `require_key` for loop enforces all 7 newly-added keys (`BAIL_REASON`, `BAIL_FAILURE_DETAIL_LOG`, `DESIGN_ONLY_DONE`, `EXPECTED_SESSION_ID`, `EXPECTED_TMPDIR_BASENAME_PREFIX`, `NO_LOGS_COMMIT`, `IMPLEMENT_TMPDIR`) in addition to the existing 32.
- The same file's `is_bool` for loop extends to assert `DESIGN_ONLY_DONE` and `NO_LOGS_COMMIT` are `true`/`false`.
- `scripts/test-ship-pr.sh`'s `write_state()` helper heredoc emits `NO_LOGS_COMMIT=false`; `bash scripts/test-ship-pr.sh` passes (covers `test-ship-pr-fix-loop-2632.inc.sh` transitively).
- `scripts/ship-pr.md` `Schema note:` paragraph updated to remove the now-stale asymmetry justification and to document the `--force-init-state true` recovery for mid-session upgrades; references to issues #2742 and #2753 retained.
- `bash scripts/relevant-checks.sh` (or `make lint`) clean.

diff_lines: 17

## Test plan
(no test plan section in plan-file)
