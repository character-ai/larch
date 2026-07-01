# /implement Step 18 cleanup and recovery

**Consumer**: `/implement` Step 18.

**Contract**: Normative cleanup, composite no-stall recovery-gate interpretation, and teardown body prose for Step 18. `SKILL.md` retains live launcher fences, marker-source bindings, and the **Escalation recording owners** enumeration for mid-pipeline reachability.

**When to load**: **MANDATORY READ ENTIRE FILE** at Step 18 entry, after the Step 18 banner and before the composite `python/cli.py implement step-18-gate-finalize` fence. Standalone `step-18.sh --phase finalize` loads only on the stall-recovery breakout branch, not on the green path.

## Stall recovery gate details

Step 18a runs first on every Step 18 entry, before teardown. By recover-then-report, stall paths and Step 12d bails skip directly to Step 18, so recovery runs before the Step 16/17 final report on those paths. The dominant no-stall path uses one composite fence. That composite owns the stall-layer read, `STALL_RECOVERY_REQUIRED` / `STALL_TRACKING_*` emission, `normalize-outcome`, Step 18a.5 eligibility, and green-path finalize.

Standalone `step-18.sh --phase finalize` remains only on the stall-recovery breakout branch. Do not reintroduce the retired no-stall two-fence sequence of `--phase gate` followed by `--phase finalize`.

Resolve `STALL_TRACKING` from four layers: in-memory orchestrator variable, `$IMPLEMENT_TMPDIR/ship-pr-state.sh`, `$IMPLEMENT_TMPDIR/finalize-state.sh`, then `$IMPLEMENT_TMPDIR/session-env.sh` via `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" session read-key` semantics. A fifth derived signal joins them: a dead-PID `.bg-wait-active` marker for a checks-commit-route site (`implement-step3-checks`, `implement-step5-self-review`), covering a process killed before it wrote `STALL_TRACKING`; see `stall-recovery.md` `RESUME_HINT=checks-commit-route-retry`.

Treat all five layers with the inverted all-false-or-empty rule: a layer is active when it is not `false` and not empty. Skip active-stall recovery only when every layer is false or empty. The composite emits `⏩ 18a: stall recovery — no stall detected` when `STALL_RECOVERY_REQUIRED=false` on the green path.

Parse `STALL_RECOVERY_REQUIRED` and `STALL_TRACKING_*` from captured composite stdout. Route active stall work on `NEXT_ACTION=stall-recovery`, not by re-entering a separate gate phase. `STALL_RECOVERY_REQUIRED=true` is diagnostic confirmation for that branch.

When `NEXT_ACTION=stall-recovery`, the inline SKILL handoff to `stall-recovery.md` owns the active-stall procedure. Do not front-load that conditional reference through this file.

## Step 18b teardown

Green-path teardown is owned by `python/cli.py implement step-18-gate-finalize`, which invokes the existing finalize wrapper internally after the no-stall gate. Breakout teardown is owned by `step-18.sh --phase finalize` on the stall-recovery branch only.

The wrapper runs `python/cli.py final-report step18b --implement-tmpdir "$IMPLEMENT_TMPDIR"`, refreshes token and final-report artifacts through that live Python path only, optionally emits the final body between stable markers, then runs closing marks, `_restore_finalize`, and teardown.

Repeat any external reviewer warnings from earlier. Mode-specific reminders (`--draft`, `--merge`, fork CI dry-run notes, upstream design issue, fork-mode OOS appendix) are emitted by `python/cli.py final-report write` into the same markdown block as the run summary when applicable. Do not duplicate them as free-form Step 18 prose.

`step-18.sh --phase finalize` runs marker emission under `set +e`, so a failed `cat` of `summary-final.md` cannot skip closing marks, `_restore_finalize`, or teardown. It also runs `final-report step18b` under `set +e`, relays `EMIT_BODY`, `WFR_RC`, `STEP17_EMITTED_PRESENT`, and `SNAPSHOT_OK`, and continues to teardown even when Step 18b exits non-zero.

## Closing token/timing marks

The `larch-tokens-&lt;slug&gt;.jsonl` token ledger and `timing-ledger.tsv` timing ledger live **inside** `$IMPLEMENT_TMPDIR`, and `resolve_ledger_path()` in `python3 python/cli.py token` / `python3 python/cli.py timing` requires `$IMPLEMENT_TMPDIR` to be a live directory root. The `--since-last-mark` reports and closing `Step 18 — done` mark MUST run before `python/cli.py implement-finalize teardown` deletes the tmpdir. Running them after teardown fails with `no per-run ledger root set`; the `pwd-hash` fallback in `resolve_session_id()` affects only the filename slug, never the directory root.
