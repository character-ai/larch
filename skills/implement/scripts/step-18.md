# step-18.sh

`step-18.sh` is the active two-phase Step 18 wrapper for `/implement`.
It replaces the retired Step 18a gate, Step 18b final-report, and Step 18 finalizer shell wrappers.

## Invocation

Gate phase:

```bash
bash "$IMPLEMENT_TMPDIR/larch-run.sh" skills/implement/scripts/step-18.sh --phase gate --stall-tracking-memory "${STALL_TRACKING:-false}"
```

Finalize phase:

```bash
bash "$IMPLEMENT_TMPDIR/larch-run.sh" skills/implement/scripts/step-18.sh --phase finalize --step17-emitted "${STEP17_EMITTED_FOR_STEP18:-false}"
```

Step 18a.5 remains prompt-side between gate clearance and `--phase finalize`.
The no-stall path therefore uses two Bash calls, down from the three retired wrappers.
The stall path exits after the gate so the orchestrator can run `stall-recovery.md`.
After terminal recovery, the orchestrator must not re-run `--phase gate`; it proceeds to Step 18a.5, usually skipped, and then `--phase finalize` even when disk `STALL_TRACKING=true` remains.

## Gate phase

The gate resolves four layers: memory, `ship-pr-state.sh`, `finalize-state.sh`, and `session-env.sh`.
It emits these KVs on stdout without `larch_quiet_init`:

- `STALL_TRACKING_MEMORY=...`
- `STALL_TRACKING_DISK=...`
- `STALL_TRACKING_FINALIZE=...`
- `STALL_TRACKING_SESSION=...`
- `STALL_RECOVERY_REQUIRED=true|false`

The helper `_stall_layer_active` is the pinned predicate.
A layer is active when its value is non-empty and not exactly `false`.
Values such as `true`, `1`, `yes`, and arbitrary non-empty strings are active.
Only empty and `false` are inactive.

## Finalize phase

The finalize phase never re-runs the active-stall gate.
When `--step17-emitted true` is passed, the wrapper writes `$IMPLEMENT_TMPDIR/.step17-emitted` before calling Step 18b so `EMIT_BODY` sees the prompt-side Step 17 emission.

The wrapper calls the live Step 18b path only:

```bash
python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" final-report step18b --implement-tmpdir "$IMPLEMENT_TMPDIR"
```

When `.step16-16a-done` is absent (terminal stall recover-then-report path), Step 18b runs rejected-findings replay and best-effort Slack notify through `python/cli.py implement step-16-16a` before `final-report write`. Green-path Step 16-17 runs write `.step16-16a-done` after Step 16/16a even when Step 17 fails, so Step 18b does not duplicate those side effects.

That call runs under `set +e` with explicit rc capture.
The wrapper relays `EMIT_BODY`, `WFR_RC`, `STEP17_EMITTED_PRESENT`, and `SNAPSHOT_OK` on stdout.
A non-zero Step 18b rc is appended to `execution-issues.md` best-effort, but it does not prevent closing token/timing marks or teardown.
The retired wrapper's dormant `cleanup.sh --help`, `token report --full`, and `Step 18 — cleanup` telemetry mark are not part of this path.

## Marker body handoff

When `EMIT_BODY=true`, `WFR_RC=0`, and `summary-final.md` is non-empty, `print_summary_markers` prints the body between whole-line markers before teardown:

- `---LARCH-SUMMARY-FINAL-BEGIN---`
- `---LARCH-SUMMARY-FINAL-END---`

The marker helper mirrors `implement step-16-17` and runs under `set +e`.
A failed `cat` of `summary-final.md` must not prevent closing marks, restore-finalize-state, or teardown (#3425).
On successful marker emission, the wrapper touches `$IMPLEMENT_TMPDIR/.step17-emitted` for harness parity.
The orchestrator owns top-chat emission by parsing captured finalize stdout only.
There is no post-teardown Read fallback.
If `EMIT_BODY=true` and `WFR_RC=0` but markers are absent or invalid, the orchestrator prints `**⚠ Step 18: EMIT_BODY=true but marker pair missing from finalize stdout.**`.

## Closing marks, safety nets, restore, and teardown

Closing token and timing reports and `Step 18 — done` marks run before teardown because teardown removes `$IMPLEMENT_TMPDIR`, which is the ledger root (#3425).
Before the safety nets run, the wrapper resolves `RUN_ID` from `read_session_key LARCH_RUN_ID`, matching production `session-env.sh` and the closeout path.
After the closing marks, the wrapper runs both Step 18 safety nets when `RUN_ID` is available:

```bash
python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" execution-issues flush-safety-net --log-root "$IMPLEMENT_TMPDIR/larch-logs" --run-id "$RUN_ID" --issue-log "$IMPLEMENT_TMPDIR/execution-issues.md"
python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" run-log capture-transcript --source-file "$LARCH_CLAUDE_SOURCE_FILE" --log-root "$IMPLEMENT_TMPDIR/larch-logs" --skill implement --run-id "$RUN_ID" --defer-commit true --execution-issues-log "$IMPLEMENT_TMPDIR/execution-issues.md" --warning-step-label "18"
```

Both safety nets are best effort and append-only.
The transcript capture uses `--defer-commit true`; publishing paths decide whether staged logs are committed.
Step 7a remains the primary green-path transcript and execution-issues capture point.
Step 18 covers bail and stall paths that reach finalization before Step 7a.
Then the copied `_restore_finalize=false` gate compares `ship-pr-state.sh` and `finalize-state.sh`.
The compare reads use guarded `session read-key` defaults, so malformed or unreadable state files do not abort teardown under `set -e`.
It invokes `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" session restore-finalize-state --implement-tmpdir "$IMPLEMENT_TMPDIR"` when `finalize-state.sh` is missing, ship stall or bail state is truthy, or `STALL_STEP` differs.

Teardown uses the exact argv pin:

```bash
python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" implement-finalize teardown --state-file "$IMPLEMENT_TMPDIR/finalize-state.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR"
```

The wrapper relays teardown stdout tail records before teardown deletes the tmpdir.
The orchestrator relays `ISSUE_URL`, `RENAME_BRANCH`, `RENAME_STATUS`, `STASH_REF`, `SENTINEL_WRITTEN`, `FINALIZE_SUBCOMMAND`, `FINALIZE_WARNINGS`, and sibling tail KVs verbatim from captured finalize stdout.

## Stream contract

Do not call `larch_quiet_init` in this wrapper.
Stall KVs, `STALL_RECOVERY_REQUIRED`, Step 18b KVs, marker lines, and teardown tail records must remain on captured Bash stdout.

## Harness

`test-step-18.sh` covers gate predicates, Step 18b failure tolerance, marker non-abort behavior, marker emission, sentinel ownership, `_restore_finalize`, the execution-issues and transcript safety nets, exact teardown argv, ordering, post-terminal continuation, stream output, and no Read fallback.
Shell-wrapper cases previously housed in `test-write-final-report.sh` moved to this harness.

## Edit in sync

Update `skills/implement/SKILL.md`, `scripts/test-implement-structure.sh`, `scripts/test-implement-timing-rehydration.sh`, `scripts/test-implement-fence-shape.sh`, `scripts/test-render-cost-line-callsites.sh`, `skills/implement/scripts/test-write-final-report.sh`, `agent-lint.toml`, `python/migrated-scripts.tsv`, and `docs/linting.md` when this contract changes.
