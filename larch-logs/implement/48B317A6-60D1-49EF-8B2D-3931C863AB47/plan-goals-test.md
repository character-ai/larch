## Goal
Implement issue #6705: [IMPLEMENTING] [OOS] [OUT_OF_SCOPE] Predictable tmp-state write in hook can follow symlinks.

## Implementation Plan
## Plan

## Approach

Keep the hook advisory and fail-open. Do not change warning thresholds, state fields, hook registration, or the Bash-only surface.

Harden temp-state I/O in two layers: validate `$state_dir` before any filesystem mutation (including `mkdir -p`, `chmod`, and `state_file` access), and treat the leaf state file as untrusted on read and write. Pin hook order explicitly so a symlinked or non-regular `$state_dir` cannot be created, chmodded, or trusted before the guard fires. Tests must prove both layers on the happy path, not only that a poisoned target stayed unchanged.

## Files to modify/create

### UPDATED: scripts/hook-anti-read-poll.sh

- After `state_dir` is bound and before any filesystem mutation (`mkdir -p`, `chmod`, `state_file` read, `mktemp`, or promotion), run a pre-mutation directory guard:
  - If `$state_dir` is a symlink (`[ -L "$state_dir" ]`), exit 0 without reading prior state, creating a temp file, or promoting.
  - If `$state_dir` exists and is not a regular directory (`[ -e "$state_dir" ] && [ ! -d "$state_dir" ]`), exit 0 on the same no-read/no-write path.
- Only when the pre-mutation guard passes, run `mkdir -p "$state_dir"` and `chmod 700 "$state_dir"` (preserve existing fail-open `|| exit 0` / `|| true` behavior).
- Immediately after `mkdir`/`chmod` and before `state_file` is read or written, re-validate the directory:
  - Require `[ -d "$state_dir" ] && [ ! -L "$state_dir" ]`.
  - If the check fails, exit 0 without reading prior state, creating a temp file, or promoting.
- Guard the state-file read (only after `$state_dir` re-validation succeeds):
  - Read only when `$state_file` is readable, not a symlink, and a regular file (`[ -f "$state_file" ] && [ ! -L "$state_file" ]` or equivalent).
  - If the path is a symlink, directory, FIFO, or other non-regular entry, skip prior state and continue with `prev_count=0`.
- Replace the direct truncate write with a temp-and-promote flow:
  - Create a temp file with `mktemp` under the validated `$state_dir`.
  - Write the tab-separated state row into the temp file.
  - Cleanup the temp file on write or promote failure.
  - Promote with same-directory replacement (`mv` into `"$state_file"`) so a symlink at `$state_file` is not opened for truncation.
- Preserve exit-0 behavior on all failure paths.
- Keep Bash 3.2-compatible syntax.

### UPDATED: scripts/test-hook-anti-read-poll.sh

- Add a helper to compute the expected state path from cwd and session id, using the same `cksum` inputs as the hook (`read-${cwd_hash}-${session_hash}.state` under `$TMPDIR/larch-read-poll`).
- Add a helper to compute `path_hash` from the read path with the same `cksum | awk '{print $1}'` pipeline as the hook.
- Add a leaf symlink-poisoning regression:
  - Create `$TMPDIR/larch-read-poll/<key>.state` as a symlink to a writable target file.
  - Seed the target with a poison row that would produce a third-read warning if followed:
    - `path_hash` and `offset` must match the `run_hook` args for the test read.
    - `prev_count=2`.
    - `prev_time` must be within the 30s window of the chosen `HOOK_ANTI_READ_POLL_NOW` (for example `now - 5`).
  - Run the hook once for the matching path, offset, cwd, and session.
  - Assert exit 0, no reminder output, and target content unchanged.
  - On the happy path, require observable replacement: `[ ! -L "$state_path" ] && [ -f "$state_path" ]`.
  - Assert the replacement row matches the hook contract: tab-separated `path_hash`, `offset`, `count=1`, and `now` from the test run.
  - Fail the regression if promotion cannot be observed.
- Add a parent-directory symlink regression:
  - Explicit setup teardown before installing the attack path: remove any existing `$TMPDIR/larch-read-poll` tree (`rm -rf "$TMPDIR/larch-read-poll"`) or use a fresh isolated `TMPDIR` for this case so the symlink install cannot fail because a real directory already exists.
  - Replace `$TMPDIR/larch-read-poll` with a symlink to another writable directory before the hook runs.
  - Seed a poisoned leaf state file under the redirected tree using the same computed `path_hash`, `offset`, and in-window `prev_time` contract.
  - Run the hook and assert exit 0, no reminder, poison target unchanged, and no symlink-following write to the attacker-chosen location.
  - When the directory check passes and promotion succeeds, assert the expected state path under the real `$TMPDIR/larch-read-poll` becomes a regular file with the fresh row; when the directory check blocks temp creation, assert no new state file appears under the redirected target tree.
- Add a negative control for the read guard:
  - Re-run the leaf symlink case with the hook's `-L` / non-regular read guard temporarily removed or bypassed in test-only scaffolding.
  - Assert the test fails because the poisoned target state produces a reminder or the target content changes.
  - Restore the guard before the harness exits.
- Keep the existing pass/fail counter style.

### UPDATED: SECURITY.md

- Update the existing "Plugin-shipped hooks (generic repeated reads)" or "Read-poll reminder output" note.
- State that the read-poll hook treats its temp state file as untrusted local state, validates `$state_dir` before any filesystem mutation and again before read/write, does not follow symlinked state files for read or write, and rejects a symlinked or non-regular `$state_dir` before temp creation or promotion.

## Edge cases

- Missing `jq`, malformed hook JSON, invalid time, missing `mktemp`, unwritable temp dir, or an invalid/symlinked `$state_dir` still exit 0.
- First-time use when `$state_dir` does not yet exist: pre-mutation guard allows `mkdir -p`; post-mutation re-validation must still pass before any `state_file` access.
- Existing non-regular state entries do not block tool use.
- A symlinked state path must not cause target-file truncation.
- A stale symlinked state file must not be trusted as prior counter state.
- A symlinked parent `$state_dir` must not redirect temp creation or promotion.
- Directory-like destination behavior should fail open rather than moving the temp file into an attacker-chosen directory.

## Failure modes

- If the pre-mutation guard, post-mutation `$state_dir` re-validation, temp creation, state-row write, or promotion fails, remove the temp file best-effort and exit 0.
- If the state path or parent directory changes between checks, prefer losing the reminder state over following an unsafe path.
- If the negative-control scaffolding cannot be applied safely on a platform, document the skip in-test and keep the positive replacement assertions mandatory.

## Testing strategy

- Run `bash scripts/test-hook-anti-read-poll.sh`.
- Run `make test-hook-anti-read-poll`.
- Run `make shellcheck` or the scoped pre-commit shellcheck path for the changed shell files if available.
- Run `make lint-bash32` if the implementation changes shell control flow or redirection shape.

## Acceptance

- Run `bash scripts/test-hook-anti-read-poll.sh`.
- Run `make test-hook-anti-read-poll`.
- Run `make shellcheck` or the scoped pre-commit shellcheck path for the changed shell files if available.
- Run `make lint-bash32` if the implementation changes shell control flow or redirection shape.

diff_added: 104
diff_deleted: 12
mechanical_churn: false
diff_lines: 116

## Test plan
(no test plan section in plan-file)
