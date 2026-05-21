## Goal
Wire step8b_rebase into Phase 1-4 conflict resolution to prevent stalls on non-bump file conflicts before PR creation

## Implementation Plan

**Goal**: Fix issue #2531 — step8b_rebase stalls on non-bump file conflicts by wiring it into the existing Phase 1–4 Conflict Resolution Procedure (same mechanism already used by early_rebase at Steps 1.r/4.r/7.r/7a.r).

**Scope**: Doc-only changes to two markdown files. No script edits.

### Files to change

#### 1. `skills/implement/references/conflict-resolution.md`

**Current state** (line 7 — "When to load" section):
- Contains: `"do NOT load for step8b-family callers (step8b_rebase deliberately does not enter Phase 1–4 — see Inputs Conflict fallback path in rebase-rebump-subprocedure.md)"`
- Caller families list (lines 13-15) has only two entries: `step12_phase4` family and `early_rebase`.

**Changes**:
1. Line 7 — "When to load" section: Remove the step8b exclusion. Add step8b_rebase as an included caller alongside the two existing callers. The new sentence should describe the three entrypoints: Step 12 family, early_rebase, and step8b_rebase.

2. Caller families list: Add a third `caller_kind=step8b_rebase` entry with these semantics:
   - Run Phase 1 (conflict classification and resolution)
   - Run Phase 2 (user escalation for uncertain conflicts)
   - **Skip Phase 3 entirely** (same as early_rebase — no reviewer panel pre-PR)
   - Run Phase 4 in local-only mode: `rebase-push.sh --continue --no-push --keep-on-conflict`
   - Phase 4 exit 0: dispatch the Rebase + Re-bump Sub-procedure with `rebase_already_done=true, caller_kind=step8b_rebase` (mirrors the existing `step12_phase4` pattern)
   - Bail paths: abort rebase, set `STALL_TRACKING=true`, skip to Step 18 (same as early_rebase)
   - No reviewer panel, no re-bump dispatch by Phase 4 itself (the Sub-procedure owns re-bump), no push by Phase 4

3. Phase 4 section: The existing `early_rebase` block in Phase 4 handles `--continue --no-push --keep-on-conflict`. Add `step8b_rebase` to this block with the same exit-code handling as `early_rebase`, but Phase 4 exit-0 dispatches the Rebase + Re-bump Sub-procedure with `rebase_already_done=true, caller_kind=step8b_rebase` instead of returning to the macro's M3 path.

#### 2. `skills/implement/references/rebase-rebump-subprocedure.md`

**Current state**:
- Inputs Conflict fallback path (line 23): says step8b deliberately does NOT enter Phase 1–4 with rationale that "Phase 1–4's user-escalation and reviewer-panel machinery is post-PR-only".
- Step 2 (line 57): step8 family uses `rebase-push.sh --no-push` (without `--keep-on-conflict`).
- Step 2 exit 1, step8 family branch (line 67): immediately sets `STALL_TRACKING=true` and skips to Step 18.
- Phase 4 caller path section (line 175): only covers `caller_kind=step12_phase4`.

**Changes**:
1. Inputs Conflict fallback path (line 23): Replace the "step8 deliberately does NOT enter Phase 1–4" rationale with the new dispatch description:
   - Correct the factual error: Phase 1–4 is NOT post-PR-only; it's already used pre-PR by early_rebase.
   - Describe the new behavior: step8b_rebase now dispatches to Phase 1–4 (same as early_rebase for Phases 1–2, Phase 3 skipped; Phase 4 uses --continue --no-push --keep-on-conflict and on exit 0 dispatches back into the sub-procedure with rebase_already_done=true).
   - On Phase 1–4 bail: existing step8 family behavior (STALL_TRACKING=true → Step 18) unchanged.

2. Step 2 invocation (line 57), step8 family: Change from `rebase-push.sh --no-push` to `rebase-push.sh --no-push --keep-on-conflict` so `CONFLICT_FILES` is populated and the rebase stays in progress for Phase 1–4 to operate on.

3. Step 2 exit 1, step8 family branch (line 67): Replace the immediate-stall text with Phase 1–4 dispatch:
   - Print conflict detection message and dispatch to Phase 1–4 with `caller_kind=step8b_rebase`
   - On Phase 1–4 success (Phase 4 exit 0 already dispatches back via `rebase_already_done=true`): sub-procedure continues at step 3
   - On Phase 1–4 bail: existing step8 family behavior (STALL_TRACKING=true → Step 18)
   - Load `conflict-resolution.md` before dispatch (MANDATORY READ ENTIRE FILE directive)

4. Phase 4 caller path section (line 175): Extend to include `caller_kind=step8b_rebase`:
   - Same skip-steps-1-2 / run-steps-3-7 semantics as `step12_phase4`
   - Step 4 (re-bump) uses step8-family failure semantics: STALL_TRACKING=true + skip to Step 18 on hard failure (NOT bail to 12d)
   - Step 5 (push) is SKIPPED for step8b_rebase (same exemption as on the normal rebase_already_done=false path)
   - Step 7 return: `step8b_rebase` → return control to `implement-finalize.sh postbump`'s force-push gate phase (same as the existing step8b_rebase return in step 7)


## Test plan

1. Run `/relevant-checks` after editing (pre-commit + agent-lint).
2. Read the changed files to verify the text is logically consistent:
   - conflict-resolution.md: step8b_rebase appears in caller families, Phase 4 handles it alongside early_rebase, "When to load" no longer excludes it.
   - rebase-rebump-subprocedure.md: Inputs fallback path is corrected, step 2 uses --keep-on-conflict, exit 1 step8 branch dispatches to Phase 1–4, Phase 4 caller path covers step8b_rebase.
3. Verify cross-references are consistent: conflict-resolution.md references the new sub-procedure behavior, sub-procedure references conflict-resolution.md for Phase 1–4.
