## Final Design Plan

The plan is very large. Showing the full plan body below.

## Plan

confidence: high

## Approach

- Add `bgjob adapt` as an additive command. Do not convert step scripts or change assessment and ship token vocabularies.
- Reuse `JobSpec`, registry identity checks, daemon startup, result-env parsing and emission, and atomic `larch.io` helpers.
- Resolve adapter inputs from explicit flags and existing session environment defaults. Accept the child command after `--`.
- In `adapt_main`, mirror `start_main` command handling: when the parsed command is non-empty and its first token is `--`, remove that token before validating the child command or passing argv to the adapter.
- Serialize each run-and-step decision with a confined lock. Hold it through the final result check, registry inspection, stale clearing, merge-env preparation, and daemon startup decision.
- Ensure the adapter lock is not retained by the forked daemon: use a fork-safe lock implementation or explicitly close the lock descriptor in the daemon child before it can retain ownership. A prompt second invocation must be able to acquire the lock and re-attach rather than block for job completion.
- Implement this state machine under the held lock:
  1. Return the existing result through the `BGJOB_STATUS=DONE` contract only when the result env passes the same safe-path checks as `wait_once`: it is a regular, non-symlink file and parses to include both `BGJOB_RC` and a `STEP` matching the requested step. Treat an empty, incomplete, malformed, unsafe, or mismatched result file as absent and continue the locked state machine.
  2. For a valid completed result, reuse the existing wait-result emission behavior: print `BGJOB_STATUS=DONE` followed by all readable result-env `KEY=value` rows, including `BGJOB_RC` and merged custom keys, and return success.
  3. Re-read and validate the result env immediately before every destructive action or `daemon.start_daemon` call. If a valid matching result appeared after the initial probe, emit the complete `DONE` result rows; never launch a daemon that could unlink a newly completed result.
  4. Start a new daemon when no registry entry exists after the final locked result check.
  5. Treat malformed, replaced, symlinked, unsafe, or identity-unverifiable registry state as fail-closed. Do not unlink or restart from it, because the recorded processes cannot be proven dead.
  6. Validate every reusable registry entry against requested run, step, tmpdir, and `clone_path == Path.cwd().resolve()` before applying liveness policy.
  7. Use one ownership-safe liveness policy: a valid, in-budget entry is reusable only while its validated daemon is live. The daemon owns child monitoring and final result publication. A live child with a dead daemon is not a safe re-attach state without a verified takeover/finalization protocol, which this additive change does not introduce.
  8. Re-attach to a valid, in-budget entry with a live daemon. Emit exactly `BGJOB_STATUS=STARTED STEP=<step> PGID=<pgid>`, where `<pgid>` is the validated child PGID from the registry, matching `bgjob start` wire semantics.
  9. Fail closed without unlinking or restarting when a valid, in-budget entry has a dead daemon, including both-dead and child-only-live states.
  10. Clear and restart an expired entry only when the registry entry is structurally valid, identity-matched, and both recorded processes are verified dead. Fail closed if either recorded process remains live or identity cannot be verified.
- Document the ownership rationale in code: daemon liveness is required because the daemon monitors the child, merges/publishes the result, and makes the existing wait protocol reliable. Do not introduce an `and`/`or` fork in the new module.
- Derive and validate the adapter merge-env path under the bgjob tmpdir. Reject symlinks and non-regular files. Initialize it with an atomic, mode-restricted write before a fresh launch.
- Assign the validated adapter merge-env path to `JobSpec.merge_result_env` before calling `daemon.start_daemon`, so daemon result publication includes accumulated merge rows.
- Add the adapter-owned child flags and merge-env path to the child argv. Rehydrate `CLAUDE_PLUGIN_ROOT` from persisted session state before daemon launch so the child inherits the runtime plugin root.
- Keep the user-facing entry point at `python3 python/cli.py`. Register the command in the canonical `python/larch/cli.py` dispatcher because `python/cli.py` is only a shim.
- Register `("bgjob", "adapt")` in both `_REGISTRY` and `_MACHINE_STDOUT_KEYS` so `LARCH_QUIET_DISABLE=1` is set and adapter `BGJOB_STATUS` / `BGJOB_ERROR` output remains parseable.

## Files to modify/create

### NEW: python/larch/bgjob/adapt.py

- Define the typed start-or-re-attach request and decision helpers.
- Add the per-run-and-step lock and validate its path under the registry root.
- Make lock ownership fork-safe so the daemon cannot retain the adapter decision lock after `start_daemon` forks.
- Centralize completed-result detection using the same regular-file, no-symlink, parseability, required-`BGJOB_RC`, and matching-`STEP` requirements as the wait contract.
- Reuse or share the wait result-emission helper so successful completed-result handling emits `BGJOB_STATUS=DONE` followed by all readable result-env rows, rather than a status-only shortcut.
- Centralize the final locked result re-check, registry classification, daemon-ownership liveness, proven-dead stale clearing, and dead-entry refusal.
- Validate registry identity against requested run, step, tmpdir, and current resolved clone path before reusing, clearing, or reporting an entry.
- Fail closed for malformed, unsafe, replaced, or identity-unverifiable registry entries; only clear structurally valid entries with both validated identities dead.
- Re-attach only to a valid, in-budget entry with a validated live daemon. Emit `STARTED` with the validated registry child PGID; never replay persisted PID or PGID on failure paths.
- Treat child-only-live as a fail-closed ownership loss rather than a reusable entry, because no child takeover or result-finalization protocol exists.
- Prepare the merge env atomically, assign its validated path to `JobSpec.merge_result_env`, and construct the adapter-owned child argv.
- Rehydrate the plugin root without trusting ambient cwd.
- Delegate fresh launches to `daemon.start_daemon`.
- Translate every nonzero `start_daemon` return into a machine-readable `BGJOB_ERROR` before returning nonzero, including closed startup-pipe, malformed startup-pipe, and raised startup-exception paths.
- Emit only existing `KEY=value` wire shapes. Return distinct `BGJOB_ERROR` values for malformed input, unsafe paths, dead or ownership-lost registry state, expired-live state, lock or registry failures, and daemon startup failures.

### UPDATED: python/larch/bgjob/cli.py

- Add `adapt_main(argv) -> int`.
- Parse `--step`, `--budget-s`, optional start-compatible identity and path flags, and the command after `--`.
- Strip one leading `--` from the parsed child-command list exactly as `start_main` does, before missing-command validation and adapter dispatch.
- Resolve the tmpdir from an explicit value or `IMPLEMENT_TMPDIR`. Fail with `BGJOB_ERROR=missing-tmpdir` when neither exists.
- Reuse `_build_spec` where its start semantics match. Keep adapter-only merge-env and child-argv preparation in `adapt.py`.
- Catch the same bounded error classes as the existing bgjob commands and return exit code 2 for contract or integrity failures.
- Ensure every nonzero adapter startup outcome still prints one machine-readable `BGJOB_ERROR` record.

### UPDATED: python/larch/cli.py

- Register `("bgjob", "adapt")` to `larch.bgjob.cli.adapt_main`.
- Add `("bgjob", "adapt")` to `_MACHINE_STDOUT_KEYS` beside existing bgjob verbs.
- Leave the root `python/cli.py` shim unchanged.

### NEW: python/tests/bgjob/test_bgjob_adapt.py

- Cover fresh start and exact daemon spec construction, including assignment of the validated merge-env path to `JobSpec.merge_result_env`.
- Cover `adapt_main` stripping a leading `--` before validating and dispatching the child argv.
- Cover a second invocation re-attaching without another launch and emitting the exact one-line `BGJOB_STATUS=STARTED STEP=<step> PGID=<validated-child-pgid>` grammar.
- Cover daemon-live re-attach with child identity validation.
- Cover child-only-live, daemon-dead refusal: assert no restart, no unlink, no stale PGID output, and no unsupported takeover behavior.
- Cover valid, in-budget, both-dead fail-closed behavior. Assert that it neither unlinks nor restarts.
- Cover clone-path mismatch refusal, alongside run, step, and tmpdir identity mismatch cases.
- Cover malformed, replaced, symlinked, or identity-unverifiable registry entries failing closed without clearing or launching.
- Cover expired-and-verified-dead clearing followed by a fresh start.
- Cover expired-but-live refusal for both daemon-live and child-only-live states.
- Cover an existing completed result returning `DONE` without a launch, asserting `BGJOB_STATUS=DONE`, `BGJOB_RC`, and at least one merged custom result key are emitted with wait-compatible result-row parity.
- Cover empty, incomplete, malformed, symlinked, non-regular, or mismatched-step result envs as non-completed results: they must not produce `DONE` or suppress the locked registry state machine.
- Cover a result appearing after the initial probe but before the locked launch decision; assert the final locked re-check returns the complete `DONE` result rows and does not invoke `start_daemon`.
- Cover merge-env atomic initialization, child flag construction, rejection of symlink or non-regular paths, and final result publication containing both preseeded and child-written merge rows.
- Cover plugin-root rehydration and missing or malformed persisted state.
- Cover lock serialization so concurrent adapter decisions cannot launch duplicate jobs.
- Add a real-fork regression test: start a job, then promptly invoke `adapt` again and assert it re-attaches rather than blocking because the daemon inherited the adapter lock.
- Cover invalid budget, missing child command after leading-delimiter normalization, missing tmpdir, bad step slug, and daemon startup failure.
- Cover nonzero `start_daemon` outcomes for closed startup pipe, malformed startup pipe, and raised startup exception; assert a `BGJOB_ERROR` record accompanies every nonzero return.
- Exercise canonical dispatcher registration and assert `("bgjob", "adapt")` is present in both `_REGISTRY` and `_MACHINE_STDOUT_KEYS`, including a quiet-mode-compatible machine-output assertion.

## Edge cases

- A result is completed only when it is a safe regular non-symlink result file that parses with `BGJOB_RC` and a `STEP` matching the request; empty, incomplete, malformed, unsafe, or mismatched result files do not produce `DONE`.
- A valid completed result must preserve `wait_once` output parity by emitting `BGJOB_STATUS=DONE` plus all readable result-env rows, including merged custom keys.
- A result may appear between the initial probe and the launch decision. Re-check it under the held lock immediately before stale clearing and immediately before `start_daemon`.
- The daemon owns result finalization. A live child with a dead daemon is not safely reusable without an explicit takeover protocol; fail closed and preserve the entry.
- A valid, live daemon entry may be re-attached even if child-state observation is transient, provided the entry’s child identity and child PGID remain validated for wire-compatible output.
- A registry row may be malformed, symlinked, expired, replaced during inspection, or belong to another clone. Revalidate paths, clone path, and identities at use time.
- A live expired process must not be silently orphaned or duplicated.
- Existing merge or result paths may be symlinks, directories, or other special files. Refuse them.
- Repeated calls must preserve the same `STARTED` or complete `DONE` wire grammar.
- Failure paths must not emit a persisted PID or PGID; successful re-attach emits only the validated child PGID required by the existing `STARTED` contract.

## Failure modes

- Fail closed when process identity cannot prove that a registry entry is safely reusable or safely stale.
- Fail closed when the daemon is dead, even if the child remains live, because this version provides no verified takeover or finalization protocol.
- Do not unlink malformed, unsafe, identity-unverifiable, or valid-but-dead in-budget entries merely to make the next launch succeed.
- Do not treat an incomplete or unsafe result env as completed; continue state evaluation without emitting `DONE`.
- Do not start a child if lock acquisition, plugin-root rehydration, merge-env initialization, registry inspection, or the final locked result check fails.
- Preserve daemon startup errors as nonzero adapter failures with a machine-readable `BGJOB_ERROR`, including nonzero returns that do not raise.
- Never signal a persisted PID or PGID from a fail-closed or error path.

## Testing strategy

- Run the new focused suite:
  - `python3 -m pytest python/tests/bgjob/test_bgjob_adapt.py`
- Run existing bgjob regression suites to detect wire or lifecycle regressions:
  - `python3 -m pytest python/tests/bgjob`
- Run the accepted Python checks:
  - `make py-lint`
  - `make py-test`
- Confirm existing step scripts remain byte-unchanged and still call `bgjob start`.

difficulty: HARD
diff_added: 875
diff_deleted: 5
mechanical_churn: false
diff_lines: 880
