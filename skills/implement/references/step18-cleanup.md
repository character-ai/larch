# /implement Step 18 cleanup and recovery

**Consumer**: `/implement` Step 18.

**Contract**: Normative cleanup, composite no-stall recovery-gate interpretation, escalation-success reporting, and teardown body prose for Step 18. `SKILL.md` retains live launcher fences, marker-source bindings, and the **Escalation recording owners** enumeration for mid-pipeline reachability.

**When to load**: **MANDATORY READ ENTIRE FILE** at Step 18 entry, after the Step 18 banner and before the composite `python/cli.py implement step-18-gate-finalize` fence. Standalone `step-18.sh --phase finalize` is loaded only on stall-recovery and escalation-filing breakout branches, not on the green path.

## Stall recovery gate details

Step 18a runs first on every Step 18 entry, before teardown. By the recover-then-report contract, stall paths and Step 12d bails skip directly to Step 18, so Step 18a recovery also runs before the Step 16/17 final report on those paths. The dominant no-stall path uses one composite fence. That composite owns the stall-layer read, `STALL_RECOVERY_REQUIRED` / `STALL_TRACKING_*` emission, `normalize-outcome`, Step 18a.5 eligibility, and green-path finalize.

Standalone `step-18.sh --phase finalize` remains only on stall-recovery and escalation-filing breakout branches. Do not reintroduce the retired two-fence no-stall sequence of `--phase gate` followed by prompt-side Step 18a.5 followed by `--phase finalize`.

Resolve `STALL_TRACKING` from four layers: the in-memory orchestrator variable, `$IMPLEMENT_TMPDIR/ship-pr-state.sh`, `$IMPLEMENT_TMPDIR/finalize-state.sh`, then `$IMPLEMENT_TMPDIR/session-env.sh` via `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" session read-key` semantics.

Treat the four layers under the inverted all-false-or-empty rule: a layer is active when it is not `false` and not empty. Skip active-stall recovery only when all four layers are false or empty. The composite emits `⏩ 18a: stall recovery — no stall detected` when `STALL_RECOVERY_REQUIRED=false` on the green path.

Parse `STALL_RECOVERY_REQUIRED` and `STALL_TRACKING_*` from captured composite stdout. Route active stall work on `NEXT_ACTION=stall-recovery`, not by re-entering a separate gate phase. `STALL_RECOVERY_REQUIRED=true` is diagnostic confirmation for that branch.

When `NEXT_ACTION=stall-recovery`, the inline SKILL handoff to `stall-recovery.md` owns the active-stall procedure. Do not front-load that conditional reference through this file.

## Step 18a.5 escalation-success report gate

On the green path, the composite owns Step 18a.5 skip predicates and escalation evidence detection. It calls `stall-recovery normalize-outcome` with the resolved memory layer and requires `IMPLEMENT_OUTCOME_SUCCEEDED=true` before it can emit `NEXT_ACTION=escalation-filing`.

Prompt-side Step 18a.5 still runs after successful stall recovery (`CLEARED=true`) and when the composite emits `NEXT_ACTION=escalation-filing`. On the `NEXT_ACTION=finalize-done` green path, prompt-side Step 18a.5 does not run.

For ordinary success paths, do not run `clear-stall`. When a real later stall is active, do not run `clear-stall`. After an explicit recovery success with `CLEARED=true`, call `normalize-outcome` with `--in-memory-stall-tracking false`; otherwise preserve the ambient in-memory stall-tracking value.

Skip when any predicate is true:

- `stall-recovery-terminal-report.env` exists.
- `stall-recovery-escalation-success.env` exists.
- `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" stall-recovery normalize-outcome` does not emit `IMPLEMENT_OUTCOME_SUCCEEDED=true`.
- Any observed `STALL_TRACKING` layer is true.
- No escalation evidence exists.

Escalation evidence is only:

- non-empty canonical ledger
- non-empty fallback ledger
- non-empty record-failure marker
- tagged `record-escalation` Tool Failure entries

Generic Tool Failures do not count. Missing attempts history is initialized as zero attempts.

When all skip predicates are false and escalation evidence exists, **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/step18a5-filing.md` completely. That conditional reference owns the eligible-path filing procedure and sentinel write.

## Step 18b teardown

Green-path teardown is owned by `python/cli.py implement step-18-gate-finalize`, which invokes the existing finalize wrapper internally after the no-stall gate and green-path Step 18a.5 checks. Normal teardown is owned by `step-18.sh --phase finalize` on stall-recovery and escalation-filing branches. Prompt-side Step 18a.5 runs before the standalone finalize fence only on `NEXT_ACTION=escalation-filing` and post-`CLEARED=true` stall recovery. It does not run on `NEXT_ACTION=finalize-done`.

The wrapper runs `python/cli.py final-report step18b --implement-tmpdir "$IMPLEMENT_TMPDIR"`, refreshes token/final-report artifacts through that live Python path only, optionally emits the final body between stable markers, then runs closing marks, `_restore_finalize`, and teardown.

Repeat any external reviewer warnings from earlier. Mode-specific reminders (`--draft`, `--merge`, fork CI dry-run notes, upstream design issue, fork-mode OOS appendix) are emitted by `python/cli.py final-report write` into the same markdown block as the run summary when applicable. Do not duplicate them as free-form Step 18 prose.

`step-18.sh --phase finalize` runs marker emission under `set +e`, so a failed `cat` of `summary-final.md` cannot skip the closing marks, `_restore_finalize`, or teardown. It also runs `final-report step18b` under `set +e`, relays `EMIT_BODY`, `WFR_RC`, `STEP17_EMITTED_PRESENT`, and `SNAPSHOT_OK`, and continues to teardown even when Step 18b exits non-zero.

## Closing token/timing marks

The `larch-tokens-&lt;slug&gt;.jsonl` token ledger and `timing-ledger.tsv` timing ledger live **inside** `$IMPLEMENT_TMPDIR`, and `resolve_ledger_path()` in `python3 python/cli.py token` / `python3 python/cli.py timing` requires `$IMPLEMENT_TMPDIR` to be a live directory root. The `--since-last-mark` reports and the closing `Step 18 — done` mark MUST run before `python/cli.py implement-finalize teardown` deletes the tmpdir. Running them after teardown fails with `no per-run ledger root set`; the `pwd-hash` fallback in `resolve_session_id()` only affects the filename slug, never the directory root.
