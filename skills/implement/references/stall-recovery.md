# Stall Recovery Reference

Step 18a loads this file only when `STALL_TRACKING` is true in any layer. It is orchestrator-facing procedure; `skills/implement/scripts/stall-recovery-report.sh` owns classification, attempt bookkeeping, dev-clone detection, and sanitized report composition. Retry caps live only in `skills/implement/scripts/stall-recovery-report.md`.

## Procedure

1. **Resolve `STALL_TRACKING`.** Check the in-memory orchestrator value first, then `$IMPLEMENT_TMPDIR/ship-pr-state.sh`, then `$IMPLEMENT_TMPDIR/session-env.sh` via `scripts/read-session-env-key.sh`. Truthy means the same allowlisted values as `stall-recovery-report.sh` (`1`, `true`, `TRUE`, `True`, `yes`, `YES`, `Yes`, `on`, `ON`, `On`); every other value is false. If every layer is false or empty, print `⏩ 18a: stall recovery — no stall detected` and continue to Step 18b. If any layer is true, continue to attempt initialization.

2. **Initialize attempts.** Run `stall-recovery-report.sh init-attempts --implement-tmpdir "$IMPLEMENT_TMPDIR" --attempts-file "$IMPLEMENT_TMPDIR/stall-recovery-attempts.env"` before classification, issue filing, or dispatch. Continue to classification.

3. **Classify.** Read `BAIL_FAILURE_DETAIL_LOG` from `$IMPLEMENT_TMPDIR/ship-pr-state.sh` first; when that key is non-empty, it is the canonical Step 18a failure-detail path to pass through `--failure-detail-log` after validating it with `realpath`/physical directory resolution, a non-symlink check, a regular-file check, a tmpdir-prefix check, and the 64 KiB cap. Then run `stall-recovery-report.sh classify --implement-tmpdir "$IMPLEMENT_TMPDIR" --in-memory-stall-tracking "${STALL_TRACKING:-false}" --bail-reason "${IMPLEMENT_BAIL_REASON:-}" --attempts-file "$IMPLEMENT_TMPDIR/stall-recovery-attempts.env"`. When a validated failure-detail log is present, treat it as the primary evidence surface; do not let stale full-state/session notes override it. Persist stdout to `$IMPLEMENT_TMPDIR/stall-recovery-classification.env`. Continue to first-detection issue filing or terminal handling based on the classified outcome.

4. **First-detection issue filing.** Only when `attempt_count==0` **and** `FAILURE_CLASS` is not terminal (`contract-failure` or `unrecoverable`), call `stall-recovery-report.sh is-larch-dev-clone --implement-tmpdir "$IMPLEMENT_TMPDIR"`, then `bug-body`, then evaluate `DRY_RUN_DECISION`. If dry-run is true, keep `$IMPLEMENT_TMPDIR/stall-recovery-bug-body.dry-run.md` and skip GitHub. If this is a non-forked larch dev clone, call `/larch:issue --input-file <generated>` and capture stdout only; persist `ISSUE_URL` and `ISSUE_NUMBER` to `$IMPLEMENT_TMPDIR/stall-recovery-issue.env`. In a consumer repo, including `--forked` runs from a larch checkout, print the body verbatim under `## Action required — file larch bug`. Terminal classes skip this step and continue directly to terminal-failure handling.

5. **Dispatch on `RESUME_HINT`.** Branch exhaustively:
   - `step2-impl`: main Claude reads `$IMPLEMENT_TMPDIR/plan.txt`, performs the implementation edits inline, runs the relevant-checks helper, commits as Step 4 does, then continues into `step5-review` and `step8-shippr`.
   - `step5-review`: invoke `${CLAUDE_PLUGIN_ROOT}/scripts/run-step5-review.sh --implement-tmpdir "$IMPLEMENT_TMPDIR" --mode loop --starting-round <next>` using the Family B background+monitor pair with the six `LARCH_*` breadcrumb paths under `$IMPLEMENT_TMPDIR/breadcrumbs/`. On success, continue into `step8-shippr`.
   - `step8-shippr`: re-invoke `${CLAUDE_PLUGIN_ROOT}/scripts/ship-pr.sh` with the same Step 8+ background+monitor envelope. Exit 6 maps to a `transient-infra` retry. Exit 4 maps to `same-cause-repeat` once when the signature matches; the follow-up classification emits `RESUME_HINT=none`, so do not redispatch the same step automatically.
   - `none`: when `FAILURE_CLASS=same-cause-repeat`, do not dispatch yet; continue to Step 6 so the one-time alternate strategy runs before terminal handling. Otherwise, do not dispatch and continue directly to terminal-failure handling.
   Any dispatch path that reaches a successful review+ship continuation must then proceed to Step 7 so `STALL_TRACKING` is cleared before Step 18b teardown observes the run as complete.

6. **Retry loop.** Record every attempt with `record-attempt --implement-tmpdir "$IMPLEMENT_TMPDIR"`, re-classify after failures to detect `same-cause-repeat`, and enforce the per-class caps from `skills/implement/scripts/stall-recovery-report.md` via `stall-recovery-report.sh retry-policy --class "$FAILURE_CLASS"`. Use `scripts/sleep-seconds.sh 5` only for `transient-infra` retry delays. For `same-cause-repeat`, take the documented alternate strategy once before terminal failure: reread `larch:plan`, restart the failed step from scratch, and persist that attempt outcome. `contract-failure` and `unrecoverable` remain terminal even when the signature matches a previous attempt. Continue to success or terminal failure.

7. **Success path.** Clear disk before memory:
   1. Compose new `ship-pr-state.sh` content with `STALL_TRACKING=false` and `STALL_STEP=` cleared.
   2. Write to `ship-pr-state.sh.tmp.<rand>` in the same directory.
   3. Re-read the temp with `read-session-env-key.sh --file "$tmp" --key STALL_TRACKING`; assert `false`.
   4. `mv -f` the temp over `ship-pr-state.sh`.
   5. Re-read the destination with `read-session-env-key.sh --file "$IMPLEMENT_TMPDIR/ship-pr-state.sh" --key STALL_TRACKING`; assert `false`.
   6. Only then clear the in-memory orchestrator variable.
   7. If the temp read, `mv -f`, or destination read fails, leave both layers true and route to terminal failure.
   Continue to Step 18b teardown.

8. **Terminal-failure path.** Before comment generation, ensure `STALL_TRACKING=true` is durable on disk, not memory-only:
   1. If `$IMPLEMENT_TMPDIR/ship-pr-state.sh` exists, rewrite it with a key-based update that preserves the canonical Step-8 state shape, keeps `STALL_TRACKING=true`, and refreshes the current `STALL_STEP` / `PHASE`.
   2. Otherwise seed the canonical minimal Step-8-shape `ship-pr-state.sh` used by the pre-Step-8 stall paths so Step 18b's on-disk `[STALLED]` rename gate can observe the stall even when the run bailed before `ship-pr.sh` wrote a state file.
   3. Re-read the resulting state file and confirm `STALL_TRACKING=true` before continuing.
   Then run `bug-comment --attempts-file "$IMPLEMENT_TMPDIR/stall-recovery-attempts.env"`, evaluate `DRY_RUN_DECISION`, then either post `gh issue comment` in the larch dev clone path or print the comment in chat for consumer repos. Before any GitHub comment call, load `ISSUE_NUMBER` from `$IMPLEMENT_TMPDIR/stall-recovery-issue.env` when that file exists so the exhaustion comment targets the recovery-created issue instead of any unrelated in-memory issue number. If that file is absent or `ISSUE_NUMBER` is empty, do not reuse an unrelated consumer/tracking issue number as a fallback; print the terminal comment for manual filing instead. Leave `STALL_TRACKING=true`. Continue to **Step 18b — Teardown** for the title-prefix terminal transition.

9. **Continue to teardown.** Regardless of success or terminal failure, continue to the existing Step 18b teardown body: token/timing refresh, `restore-finalize-state.sh`, then `implement-finalize.sh teardown`. Teardown branches on the on-disk `STALL_TRACKING` value unchanged.

## Safety Constraints

- NEVER spawn Agent-tool subagents for code-writing work during stall recovery; main Claude owns recovery edits.
- NEVER mutate `$IMPLEMENT_TMPDIR/finalize-state.sh`; use the existing Step 18 restore path only.
- NEVER call `ScheduleWakeup`.
- ALWAYS use the Family B background+monitor pair when invoking `run-step5-review.sh` or `ship-pr.sh`.
- NEVER recurse into Step 18 from inside the recovery loop.
