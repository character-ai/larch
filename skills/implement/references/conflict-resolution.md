# Conflict Resolution Procedure

**Consumer**: Rebase Checkpoint Macro early checkpoints (Steps 1.r, 4.r, 7.r, 7a.r) and the active Python Step 8+ driver `run_rebase_rebump` CI-fix rebase conflicts. Early checkpoints enter when the macro's `python/cli.py push rebase --no-push --skip-if-pushed --keep-on-conflict` exits 1 with a rebase still in progress. `run_rebase_rebump` and the pre-PR postbump gate hand off when conflict resolution must move to the main agent. **`--keep-on-conflict` / exit-4 routing**: this file owns Markdown procedure routing only for a `python/cli.py push rebase` exit **1** that leaves a rebase in progress, covering macro `early_rebase` and `ship_pr_pre_push` **exit-4** handoff. When the driver needs a main-agent conflict handoff, it persists `RESUME_PHASE` / `CALLER_KIND` / `CONFLICT_FILES` to `ship-pr-state.sh`; `ship route-exit` emits `NEXT_ACTION=conflict-fix` for orchestrator Phase 1-4. Retired in Phase 1 (#3364): `step8b_rebase`, `step12_phase4`, `step8_apply_bump_same_version`, and the Rebase + Re-bump Sub-procedure.

**Contract**: Authoritative Phase 1-4 conflict resolution procedure. Preserve the upstream (main) / feature branch commit labels, never "ours"/"theirs". Preserve the `early_rebase` Phase 3 skip, the `ship_pr_pre_push` Phase 3 main-agent self-review for non-trivial resolutions, the per-file context block format in 3c, and no-push Phase 4. Phase 3 for `ship_pr_pre_push` is main-agent self-review only: no external reviewer panel, voting, or external fallback. Phase 4 exit 0 for `early_rebase` returns to the macro. For `ship_pr_pre_push`, run the foreground stale-handoff clear from SKILL.md Step 8+ in the same turn, then re-invoke `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-8-ship.sh` with `run_in_background: true`, `timeout: 21600000`, and a `<task-notification>` wait so `run_rebase_rebump` can finish verification and force-push.

**When to load**: when `python/cli.py push rebase` exits 1 in the Rebase Checkpoint Macro's `--no-push --skip-if-pushed --keep-on-conflict` early_rebase path, or when the Python ship driver emits `NEXT_ACTION=conflict-fix` with `RESUME_PHASE=ship-pr-rrr-phase14` and `CALLER_KIND=ship_pr_pre_push` in `.ship-route-exit-handoff.env`. Read this file before Phase 1-4. Do NOT load on any other `python/cli.py push rebase` exit code or ship routing token.

---

When `python/cli.py push rebase` exits 1, conflicts paused the rebase. Resolve them with user escalation when needed. Non-trivial `ship_pr_pre_push` resolutions get main-agent self-review in Phase 3, not an external panel.

**Caller families**:

- `caller_kind=early_rebase`: run Phase 1, Phase 2, skip Phase 3, then Phase 4 local-only. Bail paths abort the rebase, set `STALL_TRACKING=true`, and skip to Step 18. No panel and no push occur; Step 5 normal review covers correctness later, and no version bump exists yet.
- `caller_kind=ship_pr_pre_push`: run Phase 1, Phase 2, Phase 3 main-agent self-review when non-trivial resolutions exist, then Phase 4 local-only. The trivial-all gate still skips Phase 3 when every conflict was trivial. No push occurs in Phase 4. **Phase 4 exit 0 re-invokes the active Step 8+ selector**: first run the foreground stale-handoff clear from SKILL.md Step 8+ in the same turn, then launch `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-8-ship.sh` with `run_in_background: true`, `timeout: 21600000`, and a `<task-notification>` wait. The Python driver continues `run_rebase_rebump` post-rebase verification and CI-fix force-push. **Phase 4 bail** matches `early_rebase`: abort, set `STALL_TRACKING=true`, skip to Step 18.

**Bail invariant**: Any bail from any phase below must call `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" git rebase-abort` before the caller-family bail destination, because the rebase stays in progress throughout.

## Phase 1 - Conflict Classification and Resolution

The caller supplies `CONFLICT_FILES` as a comma-separated list. For `caller_kind=early_rebase`, use the `CONFLICT_FILES=...` line from the macro M1 `python/cli.py push rebase --no-push --skip-if-pushed --keep-on-conflict` stdout. For `caller_kind=ship_pr_pre_push`, use the conflict list from `.ship-route-exit-handoff.env`; `python/ship.py` writes the same list into `$IMPLEMENT_TMPDIR/ship-pr-state.sh` via `--state-file`. If absent, fall back to `git diff --name-only --diff-filter=U`. **Multi-hop rebase / Phase 4 exit 1**: on each Phase 4 `--continue --no-push --keep-on-conflict` exit 1, re-capture `CONFLICT_FILES` from that latest invocation's stdout. Do not reuse an initial M1 list.

For each file in `CONFLICT_FILES`:

1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" git conflict-files`. Parse each block of `FILE=<path>`, `STAGE_1=<bool>`, `STAGE_2=<bool>`, `STAGE_3=<bool>` lines.
2. **Unsupported conflict types**: if any required stage is missing, or the file is binary, classify as **uncertain**. Do not auto-resolve.
3. **Generated files**: if auto-generated and both sides are obvious, classify as **trivial** and auto-resolve. When upstream (main) is correct, run `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" git checkout-ours <file>`; during rebase this wrapper selects upstream (main). Stage with `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" git stage <file>`. Version files are ordinary conflicts; `/release` owns version bumps.
4. **Text conflicts with both sides available**: read both sides through wrappers:
   - `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" git show-stage --stage 2 --file <file>` → **upstream (main)** version. If it fails, classify as uncertain.
   - `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" git show-stage --stage 3 --file <file>` → **feature branch commit** version. If it fails, classify as uncertain.
   - Also read working-tree conflict markers for context.
5. **Classify confidence**:
   - **High-confidence**: non-overlapping regions, or conflict markers show only whitespace, import-order, or formatting differences. Both intents are clear and composable.
   - **Uncertain**: overlapping semantic changes to the same function/block, correctness needing domain knowledge, failed stage reads, or non-text/binary conflicts.
6. Auto-resolve trivial and high-confidence files. Stage resolved files with `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" git stage <file>`.
7. Always use upstream (main) and feature branch commit labels when describing sides; never use rebase-inverted labels.

## Phase 2 - User Escalation

If there are no uncertain conflicts: for `caller_kind=early_rebase`, skip to Phase 4; for `caller_kind=ship_pr_pre_push`, continue to Phase 3 so the trivial-all gate can skip or main-agent self-review can run.

Call `AskUserQuestion` once with the upstream (main) version, feature branch commit version, and proposed resolution for each uncertain file. Use explicit labels. Incorporate the answer, write the resolved file, and stage with `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" git stage <file>`. If the user says to abort or the conflict cannot be resolved, run `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" git rebase-abort` and bail with `STALL_TRACKING=true` + Step 18.

## Phase 3 - Main-Agent Conflict Resolution Self-Review

If `caller_kind=early_rebase`, skip Phase 3 entirely and proceed to Phase 4. If all conflicts were trivial, skip Phase 3 and proceed to Phase 4.

Otherwise, run main-agent self-review for non-trivial `ship_pr_pre_push` conflict resolutions:

**3a. Temp directory**: create `$IMPLEMENT_TMPDIR/conflict-review/`; if it exists from this rebase loop, remove and recreate it.

**3b. Trivial gate**: if every conflict was classified and resolved as trivial, skip the rest of Phase 3 and proceed to Phase 4.

**3c. Review context**: for each non-trivial conflicted file, prepare a per-file conflict context block:
```
### <file-path>
**Conflict type**: <text overlap / import reorder / etc.>
**Upstream (main) version** (relevant section):
<content from `cli.py git show-stage --stage 2 --file <file>`, focused on the conflicting region>

**Feature branch commit version** (relevant section):
<content from `cli.py git show-stage --stage 3 --file <file>`, focused on the conflicting region>

**Proposed resolution**:
<the resolved content that was staged>

**Intent**: <one-line description of what each side was trying to do>
```

The per-file conflict context blocks are sufficient for main-agent evaluation; no staged-diff capture is required.

**3d. Main-agent review loop**: review the staged resolutions directly against the context blocks and staged files. If you find a defect, re-resolve the affected file, stage it with `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" git stage <file>`, and repeat Phase 3 from the context block preparation. If no defect remains, proceed to Phase 4. Allow up to **2 total resolution-review rounds**. After 2 rounds with unresolved defects, run `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" git rebase-abort`, set `STALL_TRACKING=true`, and bail to Step 18.

**3e. Cleanup**: remove `$IMPLEMENT_TMPDIR/conflict-review/` after Phase 3 completes, on success and bail paths, before proceeding.

## Phase 4 - Continue Rebase

For `caller_kind=early_rebase`, run `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" push rebase --continue --no-push --keep-on-conflict`:

- **Exit 0**: local-only rebase succeeded. Return to the Rebase Checkpoint Macro success path (M3). Do NOT push.
- **Exit 1**: a later commit conflicted. Loop to Phase 1 with a fresh `CONFLICT_FILES` from this invocation's stdout.
- **Exit 3**: inspect `REBASE_ERROR`. If it indicates an empty or already-applied commit, run `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" git rebase-skip`; if skip fails, abort and bail to Step 18. Then run the same `push rebase --continue --no-push --keep-on-conflict` again and handle the same exit codes. Otherwise abort and bail to Step 18.

For `caller_kind=ship_pr_pre_push`, run the same `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" push rebase --continue --no-push --keep-on-conflict` and handle the same non-zero exits. On **Exit 0**, local-only rebase succeeded. Do not rerun Step 7a architectural-guidelines Phase A and do not call guideline invalidate or pin helpers here. The next `step-8-ship.sh` relaunch owns compose-time reassessment and will request a fresh `NEXT_ACTION=guidelines-assessment` when the final diff or `HEAD` changed. Run the foreground stale-handoff clear from SKILL.md Step 8+ in the same turn, then re-invoke the active Step 8+ selector through `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-8-ship.sh` with the Step 8+ immediate-background `Invoke:` contract: `run_in_background: true`, `timeout: 21600000`, and wait for `<task-notification>` before routing stdout/exit status per `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/ship-pr-exit-matrix.md`. Pass no resume phase; the Python driver reads scoped state internally. Do NOT invoke the retired Rebase + Re-bump Sub-procedure; the active selector continues `run_rebase_rebump` after the in-progress rebase is finished.
