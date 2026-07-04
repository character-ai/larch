## Goal
Implement issue #6213: [IMPLEMENTING] [BUG] Cross-clone process kill: kill-active-leg signals stale/recycled….

## Implementation Plan
## Plan

## Approach

Add a shared Python process-identity helper and route every kill of a persisted or post-reap-retained pid/pgid through it. Live `Popen` handles are safe by construction (the kernel pins a child's pid until the parent reaps it), so direct live-handle cleanup keeps its existing behavior.

Core rule: signal a persisted or retained pid/pgid only when its current identity still matches the recorded start time and command signature. Log before every larch-initiated kill.

For `/implement` active legs:

1. Replace `.active-leg-pgid` as the authority with a JSON record that includes:
   - `pid`
   - `pgid`
   - process start time from `ps`
   - command signature from `ps`
   - expected command signature from the launch argv
   - owner token from the `larch-run.sh` invocation
   - writer pid
   - created timestamp
2. Keep legacy `.active-leg-pgid` handling only as a safe cleanup path:
   - unlink malformed or legacy numeric records
   - do not signal them
   - log the refusal
3. Generate one owner token per `larch-run.sh` invocation, export it in the environment of the `.py` target so the leg publisher reads the same value, and pass that value to `implement kill-active-leg --owner-token`.
4. Make bystander `larch-run.sh` exits no-op for a live leg with a different owner token; the record is retained, not unlinked.
5. Consume order in the owning wrapper: validate ownership, then validate identity, then signal, then unlink.
6. In dispatcher `finally`, clear only the record with the matching owner token and identity, so one dispatcher cannot delete a newer record.

For `/design` Step 3:

1. Move retained-pid identity checks into Python instead of adding Bash logic.
2. Add a CLI helper that validates and terminates the Step 3 loop process group by recorded identity.
3. Immediately after `_loop_pid=$!`, call one quiet Python helper (for example `plan-review write-loop-identity --design-tmpdir "$DESIGN_TMPDIR" --pid "$_loop_pid"`, expected signature needle derived from the launch argv) to capture `ps` identity and atomically write the loop-identity sidecar (pid, pgid, `ps` start time, command signature, expected signature needle) to a non-symlink `$DESIGN_TMPDIR` path; the teardown helper validates against it and fails closed when the sidecar is missing or mismatched. Bash never parses `ps`.
4. Update the Bash wrapper to:
   - store `_loop_pid` only while the child is unreaped
   - clear `_loop_pid` and the identity sidecar immediately after `wait`
   - use the Python helper for pre-wait trap cleanup only
   - never run `kill -- -$_loop_pid` after `wait`

For finalize and other signal sites:

1. Add pre-kill logging to `kill_session_background_processes`.
2. Keep its tmpdir substring scoping unchanged.
3. Audit every `os.kill`, `os.killpg`, `kill --`, and `pkill`-family call site and classify it: persisted/retained (needs identity validation) or live-handle (safe by construction).
4. Apply identity validation only to the persisted/retained class: the active-leg record, the Step 3 loop teardown, and any other stale-capable path the audit finds.
5. Live-handle sites (`agent_waterfall.py`, `_run_external.py`, `design_dialectic.py`, research fetch teardown) keep existing terminate/kill behavior; the audit records the classification, optionally as a one-line safety comment at each kill site. No new validation there: fail-closed `ps` checks on live timeout paths could leave stalled external agents running.
6. Do not change the single-runner invariant or serialize clones.

## Files to modify/create

### NEW: python/larch/core/process_identity.py

Create the shared identity and kill helper.

Include frozen dataclasses for:

- recorded process identity
- validation result
- kill target snapshot
- kill log event

Provide helpers to:

- read identity from `ps -p <pid> -o lstart= -o command=` using the existing runner seam where possible
- normalize command signatures for comparison
- validate pid, pgid, start time, and command signature
- collect descendants
- render bounded command lines for logs
- append redacted JSONL or line logs to a supplied path
- terminate a validated process group with SIGTERM, wait, then SIGKILL only if still valid

Keep this module stdlib-only.

### UPDATED: python/larch/core/config.py

Add constants for new wire names and filenames:

- active-leg JSON filename
- legacy pgid filename if it remains referenced
- owner token env var (documented; read by both the leg publisher and cleanup)
- Step 3 loop-identity sidecar filename
- active-leg kill log filename
- Step 3 kill log filename
- finalize kill log filename

Use existing naming style.

### UPDATED: python/larch/implement/dispatch_leg.py

Replace pgid-only active-leg state with identity-backed state.

Required changes:

- publish a JSON active-leg record after `Popen`
- store the owner token from the config env var (same value the wrapper exported)
- store process identity from `ps`
- require `--owner-token` in `kill_active_leg_main`: when absent or empty, log the refusal and return 0 without reading, unlinking, or signaling JSON records (legacy numeric cleanup still runs)
- consume order: validate ownership, then identity, then signal, then unlink
- on owner-token mismatch for a live record, no-op without unlink
- refuse to signal missing, malformed, mismatched, or legacy records
- unlink only records this invocation owns, plus malformed records after logging why no signal was sent
- log every actual SIGTERM/SIGKILL target before signaling
- never SIGKILL after failed validation
- keep in-process timeout cleanup for the live `Popen`, but route it through the same logging helper

Preserve `start_new_session=True`.

### UPDATED: python/larch/implement/implement_dispatch.py

Re-export any renamed constants or helpers that tests or old imports still use.

Keep the shim behavior intact.

### UPDATED: python/larch/state/bootstrap.py

Update the generated `larch-run.sh` template.


- generate a per-invocation owner token before Python target execution
- export the token under the config env var before the `python3` target line so the leg publisher sees it
- pass the same value to `implement kill-active-leg --owner-token "$token" --implement-tmpdir "$IMPLEMENT_TMPDIR"`
- remove `2>/dev/null`
- keep the EXIT, INT, TERM trap
- keep `.sh` targets as `exec`
- keep `.py` targets non-`exec`

### UPDATED: python/larch/state/finalize.py

Add observability to `kill_session_background_processes`.


- log every pid selected for kill with pid, resolved command line, caller, tmpdir needle, physical needle, and reason
- log before `kill -TERM`
- keep current `_cleanup_target_ok` and tmpdir scoping logic unchanged
- keep return semantics unchanged

### UPDATED: skills/design/scripts/design-step3-review.sh

Remove raw retained-pid process-group killing.


- call the quiet Python identity-writer helper immediately after `_loop_pid=$!` to write the sidecar; Bash does no `ps` parsing and keeps pid bookkeeping, wait, and trap gating only
- replace `_step3_review_teardown_loop_group` with a thin call to a Python CLI helper that validates against the sidecar
- call it only while `_loop_pid` refers to an unreaped loop process
- clear `_loop_pid` and the sidecar immediately after `wait`
- keep fallback `session kill-background-processes`
- preserve current stdout envelope behavior

### UPDATED: skills/design/scripts/design-step3-review.md

Update the script contract so it no longer claims Bash owns raw `kill -- -"$!"`.

Describe the launch-time identity sidecar and the identity-validated Python teardown.

### UPDATED: python/cli.py

Register the new helper CLI verbs for Step 3: the quiet loop-identity writer and the identity-validated teardown.

Keep the existing `implement kill-active-leg` verb.

### UPDATED: python/tests/core/test_process_identity.py

Add focused unit tests for the new helper:

- captures `ps` start time and command
- rejects missing pid
- rejects start-time mismatch
- rejects command mismatch
- rejects pgid mismatch
- logs before kill
- does not SIGKILL after failed validation

### UPDATED: python/tests/implement/test_implement_dispatch.py

Update active-leg tests.

Add coverage for:

- JSON record write
- published record owner token equals the cleanup argv token
- owner-token match kills
- owner-token mismatch no-ops without unlink for live records
- missing `--owner-token` refuses without reading, unlinking, or signaling JSON records
- legacy `.active-leg-pgid` is refused and unlinked without kill
- recycled pid with mismatched start time is refused
- malformed record is refused
- dispatcher `finally` does not clear a record it does not own
- timeout cleanup logs SIGTERM and SIGKILL targets

### UPDATED: python/tests/state/test_bootstrap.py

Update `larch-run.sh` assertions.

Cover:

- owner token generation
- token exported to the `.py` target environment before the target line
- `--owner-token` forwarding with the same value
- no `2>/dev/null` silencing
- trap remains installed for `.py`
- `.sh` target stays `exec`

### UPDATED: python/tests/state/test_finalize.py

Update finalize reaper tests.

Add assertions that kill logging happens before `kill -TERM` while preserving current skip and return behavior.

### UPDATED: skills/design/scripts/test-design-step3-review.sh

Update Step 3 wrapper harnesses.


- no raw `kill -- -$_loop_pid`
- identity sidecar written at launch via the Python writer helper (no Bash `ps` parsing) and cleared after `wait`
- teardown helper is called before reaping on trap cleanup and fails closed without the sidecar
- no teardown helper is called after normal `wait`
- `_loop_pid` is cleared after wait
- fallback tmpdir cleanup still runs and remains ignored on failure

### UPDATED: scripts/test-implement-fence-shape.sh

Update the larch-run template pins; touch only the affected assertions.

Required pins:

- owner-token export before the target line
- `--owner-token`
- no stderr silencing
- trap still present
- Python target remains non-`exec`

### UPDATED: scripts/test-implement-structure.sh

Update structure pins for the new active-leg JSON, identity helper, and kill logging; touch only the affected assertions.

Remove or replace pins that require `os.killpg(pgid, signal.SIGKILL)` as an unvalidated literal.

### UPDATED: SECURITY.md

Add a short process-signaling safety note.

State that larch records process identity before signaling persisted or retained pids/pgids, refuses mismatches, and logs larch-initiated kills before sending signals.

### MAY_UPDATE: python/larch/agents/agent_waterfall.py

Audit outcome only: live `Popen` handle kills stay unchanged. Optionally add a one-line safety comment at the kill site recording the live-handle classification. No validation, no behavior change, no new tests.

### MAY_UPDATE: python/larch/agents/_run_external.py

Same audit-outcome treatment as `agent_waterfall.py`: optional one-line safety comment only.

### MAY_UPDATE: python/larch/design/design_dialectic.py

Same audit-outcome treatment: optional one-line safety comment only.

### MAY_UPDATE: python/ruff.toml

Update only if the new helper or touched functions trip existing complexity baselines.

Prefer simplifying code before adding any suppression.

### MAY_UPDATE: python/complexity-baseline.json

Regenerate only if a justified complexity baseline change is unavoidable.

## Edge cases

- Stale `.active-leg-pgid` from old versions must not kill anything.
- A recycled pid with a different start time must not be signaled.
- A matching pid with a different command must not be signaled.
- A bystander wrapper in the same `IMPLEMENT_TMPDIR` must not consume or unlink a live leg record it does not own.
- A `kill-active-leg` call without `--owner-token` must not consume JSON records.
- The owning wrapper must still clean up its leg when the dispatcher child dies.
- If `ps` output is unavailable or malformed, fail closed and do not signal.
- If the active-leg record is malformed, unlink it only after logging why no signal was sent.
- If logging fails, still avoid unsafe kills. Prefer fail-closed for identity failures and best-effort logging for already-validated emergency cleanup.
- Step 3 teardown with a missing or mismatched identity sidecar sends no signal.
- Bash stays Bash 3.2 compatible.

## Failure modes

- `ps` command differences across macOS and Linux can break identity capture. Keep parsing narrow and test with mocked runner output.
- Command lines can be truncated by `ps`. Use the widest portable form available and compare a stable expected substring or normalized signature, not an exact full argv when the platform cannot guarantee it.
- Over-tokenizing ownership can disable crash cleanup. The owner token should block bystanders, not the owning wrapper.
- Logging can spam normal `.py` exits if no-op paths log too much. Log actual kills and refusal of unsafe stale records, not every missing-file no-op.
- Moving Step 3 kill logic from Bash to Python can alter wrapper stdout. Keep helper stdout redirected or quiet so existing envelopes remain stable.

## Testing strategy

Run only changed-file checks first:

- `python3 -m pytest python/tests/core/test_process_identity.py`
- `python3 -m pytest python/tests/implement/test_implement_dispatch.py`
- `python3 -m pytest python/tests/state/test_bootstrap.py python/tests/state/test_finalize.py`
- `bash scripts/test-implement-fence-shape.sh`
- `bash scripts/test-implement-structure.sh`
- `bash skills/design/scripts/test-design-step3-review.sh`

Then run Python lint for touched modules:

- `make py-lint`
- `make py-test`

If `SECURITY.md` changes, run the relevant Markdown pre-commit path or `python3 python/cli.py checks run-relevant` on the final diff.

## Difficulty

This is cross-cutting process lifecycle and safety work on the `/implement` active-leg fence, `/design` Step 3 teardown, and finalize observability, with an audit of the remaining kill sites.

confidence: high
difficulty: HARD
diff_lines: 620

## Acceptance

- A persisted or retained pid/pgid is signaled only after ownership and identity (start time + command signature) validate; mismatches refuse with no signal and no SIGKILL escalation.
- `implement kill-active-leg` without `--owner-token` reads, unlinks, and signals no JSON record; legacy numeric records are logged and unlinked without kill.
- A bystander `larch-run.sh` exit leaves a live foreign leg record untouched; the owning wrapper still cleans up its own leg on normal exit and after dispatcher SIGKILL.
- `design-step3-review.sh` contains no raw `kill -- -$_loop_pid`; teardown signals only after sidecar identity validation and the sidecar is written by the quiet Python helper and cleared after `wait`.
- Every larch-initiated kill (active-leg, Step 3 teardown, finalize reaper) logs target pgid/pids, command line, caller, and reason before signaling; the fence call is no longer stderr-silenced.
- The kill-site audit classifies every `os.kill`/`os.killpg`/`kill --`/`pkill`-family site as persisted/retained (validated) or live-handle (unchanged), and live-handle timeout cleanup behavior is unchanged.
- Listed pytest suites, `scripts/test-implement-fence-shape.sh`, `scripts/test-implement-structure.sh`, `skills/design/scripts/test-design-step3-review.sh`, `make py-lint`, and `make py-test` pass.

diff_lines: 620

## Test plan
(no test plan section in plan-file)
