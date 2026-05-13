# Rebase + Re-bump Sub-procedure

**Consumer**: `/implement` Steps 8 and 8b only — invoked from Step 8's `apply-bump.sh` same-version failure branch and Step 8b's `rebase-push.sh --no-push` exit 1 (auto-recovery from concurrent bump conflicts in the 8a→9 window). Steps 10 and 12 `ACTION=rebase` and `ACTION=rebase_then_evaluate` are now handled internally by `run_rebase_rebump()` in `scripts/ship-pr.sh` and no longer reach this sub-procedure. Includes the "Continue after child returns" anti-halt micro-reminder that travels with the `/bump-version` Skill-tool call per `${CLAUDE_PLUGIN_ROOT}/skills/shared/subskill-invocation.md`.

**Contract**: Authoritative source for the drop/rebase/fast-forward/bump/push/version-bump-reasoning log refresh sequence (the committed `version-bump-reasoning` batch, per `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/summary-comment-template.md`; the slim PR body no longer carries a Version Bump Reasoning block). Active `caller_kind` tokens (`step8b_rebase`, `step8_apply_bump_same_version`, `step12_phase4`) are contract tokens — do NOT rename. The `step10_*` and `step12_rebase*` tokens are no longer emitted by `ship-pr.sh`; they remain in this file for historical reference only. The #172 STATUS-first evaluation ordering is the degraded-git fail-closed enforcement point for Step 12 Phase 4 (Load-Bearing Invariant #3 in SKILL.md).

**When to load**: before invoking the sub-procedure from Step 8b (`rebase-push.sh --no-push` exit 1 handler), or at the entry of Step 12 Phase 4's `rebase-push.sh --continue` exit-0 handler. Do NOT load when Step 8b's `rebase-push.sh --no-push` returns exit 0 / 3 / other (only exit 1 enters the sub-procedure).

Early Rebase Checkpoint Macro conflicts (Steps 1.r / 4.r / 7.r / 7a.r) do not enter this sub-procedure; they invoke `conflict-resolution.md` directly with `caller_kind=early_rebase`, skip Phase 3, continue with `--no-push`, and perform no re-bump because no version bump exists at those checkpoints.

---

After the initial version bump in Step 8, every subsequent rebase of the feature branch onto latest `origin/main` must be followed by a fresh `/bump-version` run so the merged state reflects the version in latest main **at merge time**, not at PR-creation time. This sub-procedure consolidates the drop/rebase/fast-forward/bump/push/log-refresh sequence so that Steps 10 and 12 can invoke it from multiple places without duplication.

## Inputs
- `rebase_already_done` — if `true`, steps 1–2 are skipped (the rebase has already happened and been pushed by the caller, e.g., Step 12 Phase 4's `rebase-push.sh --continue`). If `false`, the sub-procedure performs the rebase itself.
- `caller_kind` — one of: `step12_rebase`, `step12_rebase_then_evaluate`, `step12_phase4`, `step10_rebase`, `step10_rebase_then_evaluate`, `step8b_rebase`, `step8_apply_bump_same_version`. Determines:
  1. **Post-return control flow** (re-invoke `ci-wait.sh`, fall through to 12c, fall through to Step 10's evaluate_failure handler, return to `implement-finalize.sh postbump`'s force-push phase, etc.)
  2. **Failure semantics** — grouped into three caller families:
     - **step12 family** (`step12_rebase`, `step12_rebase_then_evaluate`, `step12_phase4`): any hard failure below bails to **Step 12d**. Step 12 is the last-chance enforcement point for the version bump freshness invariant, so it must not silently proceed to merge.
     - **step10 family** (`step10_rebase`, `step10_rebase_then_evaluate`): any hard failure below logs a warning and **breaks out of Step 10's loop to Step 11**, matching Step 10's existing "never block the pipeline" philosophy. Step 12 will re-run this sub-procedure under strict semantics before merging, so Step 10 failures degrade gracefully.
     - **step8 family** (`step8b_rebase`, `step8_apply_bump_same_version`): any hard failure below logs a warning, sets `STALL_TRACKING=true` in parent scope, and **skips to Step 18** — matching the existing Step 8b bail behavior. Step 8 is pre-PR, so failures cannot break to a Step 11 loop (no Step 11 reachable from Step 8) or bail to Step 12d (no PR exists yet to bail under). The strict-vs-permissive trade is **strict**: Step 8b is the practical last enforcement point before PR creation (a `--merge=false` run, or a manually-merged PR, never reaches Step 12), so degraded STATUS / `HAS_BUMP=false` / `VERIFIED=false` paths fail closed (parallel to step12 family bail destinations, but routed to Step 18 instead of 12d). `step8_apply_bump_same_version` is the explicit `apply-bump.sh` same-version failure recovery from Step 8; it allows one fresh rebase + re-classification attempt before stalling.
  3. **Conflict fallback path** — `step12_*` falls back to a full `rebase-push.sh` + the Conflict Resolution Procedure (Phase 1–4, defined in `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/conflict-resolution.md`) when `--no-push` exit 1 happens; `step10_*` logs a warning and breaks out of Step 10 to Step 11 (Step 10 has no Phase 1–4); `step8b_rebase` and `step8_apply_bump_same_version` log a warning, set `STALL_TRACKING=true`, and skip to Step 18 (Step 8 deliberately does NOT enter Phase 1–4 — Phase 1–4's user-escalation and reviewer-panel machinery is post-PR-only and inappropriate before PR creation; the typical concurrent-bump case is already resolved by step 1's `drop-bump-commit.sh` removing the local bump before re-rebasing, so Phase 1–4 reachability is not required for the issue's stated scope).

## Happy path (`rebase_already_done=false`)

1. **Drop existing bump commit**:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/scripts/drop-bump-commit.sh
   ```
   Parse `DROPPED`. If `DROPPED=false`, log to `$IMPLEMENT_TMPDIR/execution-issues.md` under `Warnings`: `Step <N> — drop-bump-commit.sh reported DROPPED=false before rebase; HEAD was not a bump commit (CI fix commit may have landed on top, worktree had uncommitted tracked changes, or the commit touched files outside the configured bump-file set — see LARCH_BUMP_FILES in docs/configuration-and-permissions.md). Re-bump will still run but branch history may temporarily contain two bump commits and the rebase may encounter a bump-file conflict routed through Phase 1–3.` Continue to step 1b. (The guard in `drop-bump-commit.sh` is defense-in-depth — the sub-procedure does not treat `DROPPED=false` as a hard failure. Note: untracked-only worktree dirtiness does NOT cause `DROPPED=false` — Guard 1 uses `--untracked-files=no` since `git reset --hard` does not affect untracked files.)

1b. **Refresh token/timing log batches** (step10/step12 family only; best-effort, non-fatal):

   **step8 family — SKIP this step entirely** (same exemption as step 5 — push and log flush ownership belong to `implement-finalize.sh postbump`).

   **step10 / step12 family**: after dropping the bump commit, re-write the token/timing batches with updated data and create a new log-flush commit. Running this BEFORE the rebase (step 2) serves two purposes: (1) it cleans up any uncommitted larch-log writes from Steps 9a.1/11 that would otherwise cause `rebase-push.sh --no-push` to fail on a dirty working tree; (2) it keeps the log-flush commit below the fresh bump commit so `drop-bump-commit.sh` can correctly drop the bump on subsequent retries. The `--no-push` is correct because step 5 performs the push.

   ```bash
   LARCH_TOKEN_SESSION_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID --default "")
   LARCH_CLAUDE_SOURCE_FILE=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_CLAUDE_SOURCE_FILE --default "")
   export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE
   "${CLAUDE_PLUGIN_ROOT}/scripts/token-report.sh" --full --output "$IMPLEMENT_TMPDIR/token-report-rendered.md" || true
   "${CLAUDE_PLUGIN_ROOT}/scripts/timing-report.sh" --full --output "$IMPLEMENT_TMPDIR/timing-report-rendered.md" || true
   "${CLAUDE_PLUGIN_ROOT}/scripts/larch-log.sh" write --log-root "$IMPLEMENT_TMPDIR/larch-logs" --skill implement --run-id "$RUN_ID" --batch token-report --input-file "$IMPLEMENT_TMPDIR/token-report-rendered.md" || true
   "${CLAUDE_PLUGIN_ROOT}/scripts/larch-log.sh" write --log-root "$IMPLEMENT_TMPDIR/larch-logs" --skill implement --run-id "$RUN_ID" --batch timing-report --input-file "$IMPLEMENT_TMPDIR/timing-report-rendered.md" || true
   "${CLAUDE_PLUGIN_ROOT}/scripts/larch-log.sh" commit --log-root "$IMPLEMENT_TMPDIR/larch-logs" --skill implement --run-id "$RUN_ID" --no-push || true
   ```

   On any failure, log to `$IMPLEMENT_TMPDIR/execution-issues.md` under `Warnings` and continue — log refresh failure is non-fatal.

2. **Rebase without pushing**:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/scripts/rebase-push.sh --no-push
   ```
   - **Exit 0** (rebase clean, branch is local-only fresh — may include `SKIPPED_ALREADY_FRESH=true`): proceed to step 3.
   - **Exit 1** (conflict; this sub-procedure invokes plain `--no-push` without `--keep-on-conflict`, so on conflict `rebase-push.sh` has already called `git rebase --abort` and no rebase is in progress — the two invocations are independent, any fallback call restarts a fresh fetch + rebase. Distinct from the Rebase Checkpoint Macro's `--no-push --skip-if-pushed --keep-on-conflict` invocation, which deliberately leaves the rebase in progress for the early_rebase Conflict Resolution Procedure):
     - **step12 family**: **fall back to full `${CLAUDE_PLUGIN_ROOT}/scripts/rebase-push.sh`** (without `--no-push`). Enumerate all four exit codes of the fallback call:
       - **Fallback exit 0**: rebase succeeded cleanly AND the branch was force-pushed by the fallback call. Proceed to step 3. Note: `rebase_already_done` is NOT set here — that flag only gates sub-procedure steps 1–2 at entry, and by this point those steps have already executed. Step 5's push will land the new bump commit on top of the fallback's push (the intended double-push for the conflict-fallback path, necessarily two pushes because the fallback call couldn't avoid pushing).
       - **Fallback exit 1**: conflict; rebase is in progress. Enter the **Conflict Resolution Procedure** (Phase 1–4, defined in `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/conflict-resolution.md`). **Phase 4's `rebase-push.sh --continue` exit-0 handler (at the end of the Conflict Resolution Procedure) itself dispatches this sub-procedure with `rebase_already_done=true, caller_kind=step12_phase4`** — i.e., the post-conflict re-bump is owned entirely by Phase 4. **Control transfer is terminal**: the moment Phase 1 is entered, the current (fallback) sub-procedure invocation is conceptually suspended and its remaining steps 3–7 are NOT executed. All further action for this rebase (Phase 2, Phase 3, Phase 4, and the sub-procedure dispatched by Phase 4's exit-0 handler) runs under Phase 4's ownership. When Phase 4 completes (success or bail), it returns control directly to Step 12's outer loop via its own caller-return path — it does NOT return back into the current invocation. Do NOT continue executing steps 3–7 of the current invocation, regardless of whether Phase 4 succeeds or bails.
       - **Fallback exit 2**: `force-with-lease` push failure after a successful rebase. The rebase is complete locally but the branch has NOT been pushed. Do NOT skip steps 3–4: proceed to step 3 (fast-forward local main), then step 4 (re-bump), then step 5 (which will try to push the re-bumped branch and apply its own fetch + compare + retry + bail recovery on any subsequent push failure). Setting `rebase_already_done` is NOT appropriate here because step 5 still needs to push. This is the only way to guarantee the freshness invariant is enforced — skipping straight to step 5's recovery would push a rebased-but-unbumped branch, silently violating the invariant.
       - **Fallback exit 3**: non-conflict rebase failure; rebase already aborted. Read `REBASE_ERROR` and bail to 12d.
     - **step10 family**: print `**⚠ 10: CI monitor — rebase conflict, deferring to Step 12. Proceeding to Step 11.**` Log to `$IMPLEMENT_TMPDIR/execution-issues.md` under `CI Issues`. **Break out of Step 10's loop and proceed to Step 11.**
     - **step8 family**: print `**⚠ 8: rebase/re-bump recovery — conflict persisted after drop-bump-commit (non-bump files). Setting STALL_TRACKING=true and skipping to Step 18.**` Log to `$IMPLEMENT_TMPDIR/execution-issues.md` under `CI Issues`. Set `STALL_TRACKING=true` in parent scope and skip to Step 18. Do NOT enter the Conflict Resolution Procedure (Phase 1–4) — see Inputs `Conflict fallback path` above for the rationale.
   - **Exit 3** (non-conflict rebase failure in `--no-push` mode; rebase already aborted):
     - **step12 family**: read `REBASE_ERROR` and bail to 12d.
     - **step10 family**: print `**⚠ 10: CI monitor — rebase failed: $REBASE_ERROR. Proceeding to Step 11.**` Log to `CI Issues`. Break to Step 11.
     - **step8 family**: print `**⚠ 8: rebase/re-bump recovery — sub-procedure step 2 rebase failed (non-conflict): $REBASE_ERROR. Setting STALL_TRACKING=true and skipping to Step 18.**` Log to `CI Issues`. Set `STALL_TRACKING=true` in parent scope and skip to Step 18.

3. **Fast-forward local `main` to `origin/main`**:
   `rebase-push.sh` refreshes `origin/main` via `git fetch`, but local `main` is not automatically updated. `classify-bump.sh` prefers local `main` for its `merge-base` computation, so without this step `BASE` could point to an older commit than the one the branch was just rebased onto, causing the classifier's diff to include commits that belong to main (not the feature).
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/scripts/git-sync-local-main.sh
   ```
   The wrapper silently no-ops when the local `main` ref does not exist (expected in that case — `classify-bump.sh` has an `origin/main` fallback). It refuses to run if the caller is accidentally on `main` (exit 1) — defense against accidental self-update. Parse `RESULT=updated|absent|already_current` from stdout for telemetry.

4. **Re-bump**:
   Follow the same sequence as Step 8, with caller-family-specific error handling:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/scripts/check-bump-version.sh --mode pre
   ```
   Parse `HAS_BUMP`, `COMMITS_BEFORE`, and `STATUS`. The `STATUS=ok|missing_main_ref|git_error` field (#172) is authoritative for degraded-git detection — do NOT grep stderr for the old `WARN: ... neither local 'main' nor 'origin/main' exists` line.

   **Pre-check STATUS guard (#172)**: If pre-check `STATUS != ok`, `COMMITS_BEFORE` is the script's coerced 0 value, not a trustworthy baseline count. A subsequent post-check that recovers to `STATUS=ok` with a correct bump commit would compute `EXPECTED = 0 + 1 = 1` but would see the true `COMMITS_AFTER = N_prior + 1`, routing the sub-procedure to a bogus "wrong commit count" hard-bail. To prevent this mis-diagnosis:
   - **step12 family**: **HARD FAILURE** — bail to 12d immediately. Print `**⚠ 12: CI+merge loop — check-bump-version.sh reported pre-check STATUS=$STATUS (baseline untrustworthy). Cannot safely verify bump freshness. Bailing to 12d.**` Log to `$IMPLEMENT_TMPDIR/execution-issues.md` under `CI Issues`. Rationale: without a trustworthy baseline, the post-check comparison is meaningless — the merged version cannot be guaranteed correct.
   - **step10 family**: log warning `**⚠ 10: CI monitor — check-bump-version.sh reported pre-check STATUS=$STATUS (baseline untrustworthy). Skipping numeric-delta verification; Step 12 will re-verify.**` to `CI Issues`, then:
     - **If `HAS_BUMP=false`** (no `/bump-version` skill installed): skip the `/bump-version` invocation entirely and proceed directly to step 5 (push) → step 6 → step 7 — same as the `HAS_BUMP=false` path under `STATUS=ok` below. Do NOT attempt to call a skill that does not exist.
     - **If `HAS_BUMP=true`**: invoke `/bump-version` via the Skill tool anyway (the rebase still needs its re-bump commit), but **SKIP the post-check commit-delta verification below** since the baseline is untrustworthy. After `/bump-version` returns, skip directly to step 5 (push) → step 6 (`version-bump-reasoning` log refresh) → step 7 (return to caller). The post-check `STATUS`-first branches below and the numeric-comparison branches both rely on a trustworthy pre-check baseline that this invocation does not have.
   - **step8 family**: **HARD FAILURE** — set `STALL_TRACKING=true` in parent scope and skip to Step 18. Print `**⚠ 8: rebase/re-bump recovery — check-bump-version.sh reported pre-check STATUS=$STATUS (baseline untrustworthy). Cannot safely verify bump freshness. Setting STALL_TRACKING=true and skipping to Step 18.**` Log to `CI Issues`. Rationale: Step 8b is the practical last enforcement point before PR creation (a `--merge=false` run, or a manually-merged PR, never reaches Step 12 to re-verify); a transient git error that masks the count means the PR cannot be safely created.

   Only if pre-check `STATUS=ok`, proceed with the bump workflow below:
   - **If `HAS_BUMP=false`**:
     - **step12 family**: **HARD FAILURE**. Print `**⚠ 12: CI+merge loop — /bump-version not found, cannot re-bump. Bailing to 12d.**` Bail to 12d.
     - **step10 family**: Print `**⚠ 10: CI monitor — /bump-version not found, skipping re-bump. Proceeding to Step 11.**` Log to `Warnings`. Skip ahead to step 5 — the push still needs to happen because the rebase in step 2 rewrote branch history, and that rewritten history must be force-pushed so the remote PR branch reflects the new base (there is just no new bump commit stacked on top). Then fall through to step 6 (`version-bump-reasoning` log refresh — nothing new to refresh, so the batch write is skipped; see step 6's preservation rule) and step 7 (return to caller).
     - **step8 family**: **HARD FAILURE** — set `STALL_TRACKING=true` and skip to Step 18. Print `**⚠ 8: rebase/re-bump recovery — /bump-version not found, cannot re-bump. Setting STALL_TRACKING=true and skipping to Step 18.**` Log to `Warnings`. Rationale: same as the pre-check STATUS guard above — Step 8b is the last enforcement point before PR creation, so a missing bump skill cannot be deferred to a later step. (This branch is reachable on the normal `HAS_BUMP=false` path: when `/bump-version` is absent, Step 8's `HAS_BUMP=false` directive bypasses Step 8 / 8a and skips directly to Step 8b's rebase; if Step 8b's `rebase-push.sh --no-push` then exits 1, this sub-procedure is invoked under `step8b_rebase` and step 4's pre-check correctly reports `HAS_BUMP=false` here. Step 8 itself logs a permissive warning and proceeds when `/bump-version` is missing; this branch tightens behavior under the step8 family because Step 8's auto-recovery is the last enforcement point before PR creation, while a `--merge=false` or manual-merge run never reaches Step 12 to re-verify.)
   - **If `HAS_BUMP=true`**:

     > **Continue after child returns.** When `/bump-version` returns, execute the NEXT steps of this sub-procedure in order — do NOT end the turn, whether silently or after text output. **`APPLIED=true, COMMIT_SHA=<sha>` in the tool result is NOT a run-completion signal — the sub-procedure still has post-verification through step 7 to execute.** Your FIRST permitted external action MUST be `check-bump-version.sh --mode post --before-count $COMMITS_BEFORE`. Do NOT echo the parsed values as a comma-separated list ("CURRENT_VERSION=..., NEW_VERSION=..., BUMP_TYPE=..., REASONING_FILE=...") or the apply-bump.sh output ("APPLIED=true, COMMIT_SHA=...") — any turn end (with or without text output) before that Bash call is a halt in disguise. Only after the post-verification gates pass (commit-delta check via `check-bump-version.sh --mode post`, then the sentinel-file check) do you proceed to step 4a's CHANGELOG re-apply, step 5's push, step 6's `version-bump-reasoning` log refresh, and step 7's return to caller. See `${CLAUDE_PLUGIN_ROOT}/skills/shared/subskill-invocation.md` section Anti-halt continuation reminder.

     Invoke `/bump-version` via the Skill tool. If the skill invocation itself fails (returns an error, or bails internally):
     - **step12 family**: hard failure — bail to 12d.
     - **step10 family**: log warning and break out of Step 10 to Step 11.
     - **step8 family**: hard failure — set `STALL_TRACKING=true` and skip to Step 18. For `caller_kind=step8_apply_bump_same_version`, if the failure is again `ERROR=origin/main has already bumped to <NEW_VERSION>; re-classify needed`, set `FINAL_BAIL_REASON` to that literal error and do not retry the same recovery loop.
     After the skill returns successfully, run the post-verification — see `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/bump-verification.md` Block β for the full STATUS-handling matrix (step12 vs step10 family, STATUS-first ordering, sentinel-file defense-in-depth):
     ```bash
     ${CLAUDE_PLUGIN_ROOT}/scripts/check-bump-version.sh --mode post --before-count $COMMITS_BEFORE
     ```
     Apply the Block β decision matrix from `bump-verification.md`, then proceed to step 4a.

   **Rationale**: Step 8's permissive warnings are safe because Step 8 is pre-PR — no merge can happen based on a missing bump. Step 12 is pre-merge — missing bump means stale merge. Step 10 is post-PR but pre-merge (Step 12 does the merge) — any bump failure in Step 10 is recoverable by Step 12's mandatory re-bump, so Step 10 can afford to be permissive. **Step 12 is the last-chance enforcement point; Step 10 is best-effort optimization that improves freshness during the CI-wait phase.**

4a. **Re-apply CHANGELOG update** (mirrors Step 8a):
   If `CHANGELOG.md` exists in the project root (check via Read tool) and a new bump commit was created (`VERIFIED=true` from step 4), update the CHANGELOG entry to reflect the new version from the re-bump. Follow the same logic as `implement-finalize.sh postbump` Phase 2: read `CHANGELOG.md`, compose an entry with the `NEW_VERSION` from the re-bump and the same Summary bullets, insert it (or replace the existing entry for the prior version if present), stage, and amend the bump commit via `${CLAUDE_PLUGIN_ROOT}/scripts/git-amend-add.sh CHANGELOG.md`. If CHANGELOG.md does not exist or the bump was skipped, skip this sub-step silently. **This is best-effort and non-blocking** — failure to update CHANGELOG does not affect the bump or push. **Edit-in-sync note:** keep this step's CHANGELOG-update semantics aligned with `postbump` Phase 2 when category, idempotency, or insertion-order rules change.

5. **Push with recovery**:

   **step8 family — SKIP this step entirely**. For `step8b_rebase`, `implement-finalize.sh postbump` Phase 4 already encodes the correct remote-branch trichotomy through `${CLAUDE_PLUGIN_ROOT}/scripts/check-remote-branch.sh`: present → force-push, absent → skip push (fresh-branch path, `create-pr.sh` will perform the initial push at Step 9b), error → bail with `STALL_TRACKING=true` to Step 18. For `step8_apply_bump_same_version`, no PR exists yet and Step 9's create-PR path owns the first push. The shared `${CLAUDE_PLUGIN_ROOT}/scripts/git-force-push.sh` wrapper used by step12/step10 below has no "branch absent on origin" or "remote-check transport failure" outcome, so duplicating a push here would either lose the fresh-branch path or create drift. Proceed directly to step 6 (version-bump reasoning log refresh).

   **step10 / step12 family — push via the wrapper**:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/scripts/git-force-push.sh
   ```
   The wrapper performs `git push --force-with-lease` with the full recovery logic internally: on failure, it refreshes the local tracking ref, compares local HEAD vs `origin/<branch>`, returns success if they match (race landed), otherwise sleeps 5s and retries the push once. Parse stdout for `PUSHED=true|false` and `STATUS=pushed|noop_same_ref|diverged_retry_failed`. Exit code 0 on success (PUSHED=true), exit code 1 on `diverged_retry_failed`.

   - **On `STATUS=pushed` or `STATUS=noop_same_ref`** (PUSHED=true): proceed to step 6.
   - **On `STATUS=diverged_retry_failed`** (PUSHED=false): log to `$IMPLEMENT_TMPDIR/execution-issues.md` under `CI Issues`: `Step <N> — force-with-lease push failed twice; local and remote feature branches diverge after re-bump.` Then:
     - **step12 family**: bail to 12d with error `12: CI+merge loop — re-bump push failed twice, remote diverged. Manual intervention required.`
     - **step10 family**: print `**⚠ 10: CI monitor — re-bump push failed twice. Proceeding to Step 11 (may be stale).**` Break to Step 11.

   **Critical (step12 family only)**: Do NOT simply "log and return to caller" on push failure. That would let the merge loop proceed to `ACTION=merge` on a remote branch that does NOT contain the fresh bump commit, violating the feature's core invariant. `merge-pr.sh` reads local git state for its HEAD-OID precondition, branch-range bump-subject scan, `origin/main` refresh, and origin `plugin.json` same-version gate, while `ci-wait.sh` and the final `gh pr merge` operation still act on the remote PR / branch state. Unpushed local commits remain invisible to the merge itself.

6. **Refresh the `version-bump-reasoning` log batch** (best-effort, non-fatal):

   Umbrella #348 Phase 5 retargets this step from the PR body to the committed `version-bump-reasoning` batch under `larch-logs/implement/$RUN_ID/` (see `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/summary-comment-template.md` for the summary-comment contract). Unlike the old PR-body refresh, this step is a no-op when no run id is resolved for the session.

   a. **Read the session's tracking-issue sentinel**:
      ```bash
      ${CLAUDE_PLUGIN_ROOT}/scripts/tracking-issue-read.sh --sentinel "$IMPLEMENT_TMPDIR/parent-issue.md"
      ```
      Parse both the script's exit status and its `FAILED=true` / `ERROR=<msg>` stdout envelope. On success, extract `ISSUE_NUMBER` from the emitted KEY=value lines. Read `RUN_ID` from `$IMPLEMENT_TMPDIR/session-env.sh`.

   b. **Skip gate**: if non-zero exit OR stdout contains `FAILED=true` OR `ISSUE_NUMBER` is empty, log to `$IMPLEMENT_TMPDIR/execution-issues.md` under `Warnings`: `Step <N> — tracking-issue sentinel unusable (<reason>); version-bump reasoning log skipped.` Then skip to step 7.

   c. **Compose the fragment (preservation-aware)**: after `/bump-version` runs in step 4 above, it emits a `REASONING_FILE=<path>` line on stdout and that path is saved as `$BUMP_REASONING_FILE` (same semantics as Step 8 — see that step for details on why the path must be parsed from stdout rather than constructed from `$IMPLEMENT_TMPDIR`). Behavior branches on whether step 4 produced a fresh reasoning file:
      - **Fresh reasoning file available** (`$BUMP_REASONING_FILE` was set by THIS sub-procedure invocation's step 4 AND the file exists AND is non-empty): `mkdir -p "$IMPLEMENT_TMPDIR/larch-log-batches"` then copy the reasoning content into `$IMPLEMENT_TMPDIR/larch-log-batches/version-bump-reasoning.md`. Batch content flows verbatim; compose-time sanitization applies at the call-site layer (see SKILL.md "Compose-time sanitization").
      - **No fresh reasoning file** (HAS_BUMP=false degraded path or degraded-STATUS path where `/bump-version` did not run in this invocation): preserve the existing `$IMPLEMENT_TMPDIR/larch-log-batches/version-bump-reasoning.md` batch input unchanged. **Do NOT overwrite with a placeholder** — that would destroy information written at Step 8 of the prior bump cycle. This matches the documented "nothing new to refresh" semantics of the HAS_BUMP=false path.

   d. **Write the log batch** through `larch-log.sh`:
      ```bash
      ${CLAUDE_PLUGIN_ROOT}/scripts/larch-log.sh write \
        --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
        --skill implement \
        --run-id "$RUN_ID" \
        --batch version-bump-reasoning \
        --input-file "$IMPLEMENT_TMPDIR/larch-log-batches/version-bump-reasoning.md"
      ```
      Parse the standard `LOG_WRITTEN` envelope. Summary comments remain the responsibility of `tracking-issue-summary.sh`.

   e. **Non-fatal failure handling**: if the refresh step reports `FAILED=true` OR exits non-zero, print `**⚠ Step <N> — version-bump reasoning log refresh failed. Continuing.**` and log the specific `ERROR=<msg>` to `$IMPLEMENT_TMPDIR/execution-issues.md` under `Warnings`. **Log refresh failure is NOT a hard failure** — the bump is already pushed and the merge will be correct; the stale log batch is documentation-only and does not affect the merge.

7. **Return to caller based on `caller_kind`**:
   - **`step12_rebase`** (from 12a `ACTION=rebase`): increment `rebase_count`, `iteration`, reset `transient_retries`, **sleep 30s** via `${CLAUDE_PLUGIN_ROOT}/scripts/sleep-seconds.sh 30` (give GitHub CI time to register the force-push before polling again), then re-invoke `ci-wait.sh` in Step 12.
   - **`step12_phase4`** (from Phase 4 exit-0): increment `rebase_count`, `iteration`, reset `transient_retries`, **sleep 30s** via `${CLAUDE_PLUGIN_ROOT}/scripts/sleep-seconds.sh 30`, then re-invoke `ci-wait.sh` in Step 12.
   - **`step12_rebase_then_evaluate`** (from 12a `ACTION=rebase_then_evaluate`): increment `rebase_count`, `iteration`, reset `transient_retries`, then **fall through to 12c** to evaluate the CI failure. Do NOT re-invoke `ci-wait.sh` and do NOT sleep — 12c handles its own timing.
   - **`step10_rebase`** (from Step 10 `ACTION=rebase`): increment `rebase_count`, `iteration`, reset `transient_retries`, **sleep 30s** via `${CLAUDE_PLUGIN_ROOT}/scripts/sleep-seconds.sh 30`, then re-invoke `ci-wait.sh` in Step 10.
   - **`step10_rebase_then_evaluate`** (from Step 10 `ACTION=rebase_then_evaluate`): increment `rebase_count`, `iteration`, reset `transient_retries`, then **fall through to Step 10's `ACTION=evaluate_failure` handler**. Do NOT re-invoke `ci-wait.sh` and do NOT sleep.
   - **`step8b_rebase`** (from Step 8b's `rebase-push.sh --no-push` exit 1 handler): **return control to `implement-finalize.sh postbump`'s force-push gate phase.** The orchestrator re-invokes `postbump` with the same `--state-file` and `--implement-tmpdir` flags as the original invocation; the script reads `$IMPLEMENT_TMPDIR/.postbump-phase` and skips to phase 4 automatically. Do NOT increment `rebase_count` / `iteration` (those are CI-loop counters; Step 8b has no CI loop). Do NOT sleep. Do NOT re-invoke `ci-wait.sh` (no CI run is associated with Step 8b). The postbump force-push gate then proceeds to Step 9 on success or sets `STALL_TRACKING=true` and skips to Step 18 on its own remote-check transport-failure path.
   - **`step8_apply_bump_same_version`** (from Step 8's `apply-bump.sh` same-version failure handler): **return control to Step 8 immediately after the `/bump-version` invocation** with the freshly created bump commit. Step 8 then captures `REASONING_FILE`, runs `check-bump-version.sh --mode post`, writes the `version-bump-reasoning` log batch, and proceeds to Step 8a. Do NOT increment `rebase_count` / `iteration`, sleep, push, or re-invoke `ci-wait.sh`.

   **`ci-wait.sh` MUST be invoked synchronously** at every re-invocation site above (no `run_in_background: true`). Use `timeout: 1860000` on the Bash tool call to allow up to 31 minutes of blocking; do NOT background it. Backgrounding `ci-wait.sh` disconnects the orchestrator from its return code and creates a leaked-polling-loop risk if a later session-exit attempt force-kills the shell mid-poll (closes #842). See `${CLAUDE_PLUGIN_ROOT}/scripts/ci-wait.md` and `skills/implement/SKILL.md` Step 10 / Step 12a for the canonical wording.

## Phase 4 caller path (`rebase_already_done=true`, `caller_kind=step12_phase4`)

Phase 4 enters the sub-procedure AFTER `rebase-push.sh --continue` has already pushed the resolved rebase. **Skip steps 1–2 entirely.** Still run steps 3 (fast-forward local main), 4 (re-bump with step12 hard-failure semantics), 5 (push with recovery), 6 (`version-bump-reasoning` log refresh), 7 (return with `step12_phase4`). This path necessarily double-pushes (Phase 4 pushed the rebase, then step 5 pushes the new bump), but the Conflict Resolution Procedure is rare enough that the second push cost is acceptable.
