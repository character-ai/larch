### FINDING_1: Register `bgjob adapt` in `_MACHINE_STDOUT_KEYS`
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Innovation, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: The plan registers `("bgjob", "adapt")` in `_REGISTRY` but not in `_MACHINE_STDOUT_KEYS`. Existing `bgjob start`/`wait` entries set `LARCH_QUIET_DISABLE=1` before subcommand execution. Without the same registration, inherited quiet mode can suppress `BGJOB_STATUS` / `BGJOB_ERROR` machine stdout from `adapt`, breaking orchestrator parsing of the adapter wire contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `("bgjob", "adapt")` to `_MACHINE_STDOUT_KEYS` beside the other `bgjob` verbs; extend dispatcher registration test to assert machine-stdout membership.
  - From Cursor-Innovation: Add ("bgjob","adapt") to _MACHINE_STDOUT_KEYS and assert registry plus machine-stdout membership in the dispatcher tests
  - From Codex-Innovation: Add `("bgjob", "adapt")` to `_MACHINE_STDOUT_KEYS` and cover the canonical dispatcher path with an assertion that adapter output remains machine-readable.
  - From Codex-Pragmatic: Add `("bgjob", "adapt")` to `_MACHINE_STDOUT_KEYS` and include that assertion in the dispatcher test.
  - From Cursor-Requirements: Add ("bgjob", "adapt") to _MACHINE_STDOUT_KEYS alongside the existing bgjob verbs and cover it in dispatcher registration tests
  - From Codex-Requirements: Add `("bgjob", "adapt")` to `_MACHINE_STDOUT_KEYS` and assert this in the planned dispatcher test.


### FINDING_2: Re-attach identity validation omits `clone_path`
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: Registry identity checks in the plan cover run, step, and tmpdir but omit `clone_path`. `RegistryEntry` records `clone_path` at launch (`daemon.py` uses `Path.cwd().resolve()`), and `registry.has_live_entry()` treats a different clone as non-live. Re-attach without a `clone_path` match can reuse another clone's row when tmpdir/run_id collide.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Include `entry.clone_path == Path.cwd().resolve()` (or equivalent fail-closed check) in re-attach and reuse gates; add a test for clone mismatch refusal.


### FINDING_3: Re-attach STARTED PGID source and failure-mode wording conflict
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-dyn-Process Lifecycle Auditor
- **Severity**: major
- **Concern**: The plan requires `BGJOB_STATUS=STARTED ... PGID=<pgid>` on live re-attach (state 4) but also says "Never signal a persisted PID or PGID from this new path." The PGID source is unspecified for OR liveness (dead daemon + live child vs live daemon + dead child). Implementers may omit PGID, treat the failure mode as absolute, emit stale registry PGID on error paths, or use daemon PGID instead of the child PGID that `start_daemon` publishes—breaking wire parity with `bgjob start`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Scope the failure mode to fail-closed paths only; pin re-attach STARTED to child PGID from validated live child identity (same shape as `start_main`), and test it.
  - From Cursor-Innovation: Define re-attach PGID as the PGID of the validated live process (prefer child when child_liveness.live else daemon) and document that failure-mode wording forbids stale registry replay on error paths only; pin both OR cases in tests with exact one-line STARTED grammar
  - From Cursor-Pragmatic: Clarify that step 4 emits PGID only after live identity validation on re-attach; fail-closed branches (steps 5-6 live-refusal, lock/registry/plugin-root/merge-env failures) must not print PID/PGID. Pin the PGID source to the validated child identity (same as `daemon.start_daemon`).
  - From Cursor-dyn-Process Lifecycle Auditor: On re-attach, re-read the registry entry under the lock, re-run OR liveness on fresh identities, and emit PGID from the validated child identity (`entry.child.pgid`). Add a test with dead daemon + live child that expects the child PGID.


### FINDING_5: Nonzero `start_daemon` must emit `BGJOB_ERROR`
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: The failure contract does not preserve a machine-readable error when `daemon.start_daemon` returns a nonzero status without raising. Existing startup failures can return `2` after the child-side startup pipe closes or emits malformed data. If `adapt` simply returns that code, callers receive no `BGJOB_ERROR`, violating the plan's required adapter failure contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Translate every nonzero `start_daemon` result into a `BGJOB_ERROR=...` record before returning nonzero, and test pipe-close, malformed-pipe, and daemon-startup exception paths.


### FINDING_11: Adapter lock must not be inherited by forked daemon
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: The plan does not prevent the adapter lock from being inherited by the forked daemon. If the lock uses a file descriptor, `daemon.start_daemon` forks while the lock is held. The daemon can retain that lock until the job finishes, so a second `bgjob adapt` call blocks instead of re-attaching.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Use a lock whose ownership is not inherited across `fork`, or explicitly close the adapter lock in the daemon child. Add a real-fork test that starts a job and promptly re-attaches.


### FINDING_13: Lock-guarded result re-check missing before `start_daemon`
- **Reviewer(s)**: Cursor-dyn-Process Lifecycle Auditor
- **Severity**: major
- **Concern**: The edge case only requires re-checking the result env under lock before clearing or failing, not immediately before `start_daemon`. A caller can miss a completed result on a pre-lock probe, acquire the lock, see no registry, and still launch. `_daemon_child` always unlinks the step result file before spawning, so a duplicate launch can delete a valid completed result.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Process Lifecycle Auditor: Add an explicit state-machine step under the held lock: re-read and validate the result env immediately before stale clearing and before any `start_daemon` call. Return `BGJOB_STATUS=DONE` when present. Add a test where the result appears after the first probe but before the locked start path.


### FINDING_14: Child-only-live OR re-attach lacks takeover or finalization protocol
- **Reviewer(s)**: Codex-dyn-Process Lifecycle Auditor
- **Severity**: major
- **Concern**: The OR liveness policy treats a live child with a dead daemon as safely re-attachable, but the daemon owns monitoring and result publication. After the daemon exits while the child continues, `adapt` re-attaches because child liveness is true. The existing wait path then treats the dead daemon as terminal and can report DEAD while the child still runs, or leave an orphaned child with no result env.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Process Lifecycle Auditor: Use daemon liveness as the ownership requirement, or add an explicit, verified takeover/finalization protocol for the child-only-live branch before treating it as reusable. Pin that branch in the state-machine tests.


### FINDING_15: Malformed registry must not be cleared without verified-dead identities
- **Reviewer(s)**: Codex-dyn-Process Lifecycle Auditor
- **Severity**: major
- **Concern**: The plan permits malformed registry state to be cleared before a fresh start, even though malformed state cannot prove that its recorded processes are dead. This can unlink a registry row whose identities are unreadable or whose file was replaced, then launch a duplicate child while the original job remains live—violating the stated fail-closed requirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Process Lifecycle Auditor: Do not clear malformed or identity-unverifiable entries. Recheck the registry under the lock and fail closed unless the entry is structurally valid and both recorded identities are verified dead; reserve clearing for that proven-dead case.


### FINDING_1: Define valid completed-result detection
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The State-1 DONE short-circuit does not define what makes a result environment valid. An empty or incomplete result file can cause `adapt` to emit `BGJOB_STATUS=DONE` without `BGJOB_RC`, skipping a fresh launch even when the registry entry is dead or fail-closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin completed-result detection to the same regular-file/symlink checks as wait plus required keys (`BGJOB_RC` and matching `STEP`) before any DONE return. Treat empty or incomplete files as absent and continue the locked state machine.


### FINDING_2: Strip the leading `--` in `adapt_main`
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: `adapt_main` does not explicitly require the same leading `--` child-argument stripping contract as `start_main`. Without it, orchestration calls can forward `["--", ...]` to `Popen`, causing startup failure or incorrect argv.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In adapt_main, mirror start_main exactly: if `args.command` is non-empty and first token is `--`, drop it before missing-command validation and before handing argv to adapt.


### FINDING_3: Preserve DONE result-row output parity
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The DONE branch may emit only `BGJOB_STATUS=DONE` instead of the complete result-environment rows emitted by `wait_once`. Callers that parse `BGJOB_RC` or merged custom keys would then receive incomplete output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Reuse the same emission helper as `wait_once` (or call into it): print `BGJOB_STATUS=DONE` followed by all readable result-env KVs on exit 0. Extend `python/tests/bgjob/test_bgjob_adapt.py` to assert `BGJOB_RC` and at least one merged custom key, mirroring `test_wait_done_prints_result_rows`.


### FINDING_5: Populate `JobSpec.merge_result_env`
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: The adapter-owned merge-env path is specified for child-argv construction but may not be assigned to the `JobSpec` passed to the daemon. If the field remains unset, `daemon.write_result` will omit accumulated merge rows from the completed result.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Explicitly assign the validated adapter merge-env path to `JobSpec.merge_result_env` before calling `daemon.start_daemon`, and test the resulting DONE output with preseeded and child-written merge rows.


