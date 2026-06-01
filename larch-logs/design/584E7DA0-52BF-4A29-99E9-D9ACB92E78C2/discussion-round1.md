# Round 1 — Scope & Hard Constraints (issue #3299)

## Decision 1: Scope of this design
- **Question**: Cover both proposal parts, or just one?
- **Resolution**: Both parts — (1) absorb the remaining prompt-side rebase/re-bump handoff into `ship-pr.sh`, and (2) fold `CLONE_TAG_FULL` into `ship-pr.sh` argv-init.
- **Source**: user

## Decision 2: Disposition of the two reference docs
- **Question**: After absorption, delete or retain `rebase-rebump-subprocedure.md` and `bump-verification.md`?
- **Resolution**: Retain both. They remain the historical/internal contract; `bump-verification.md` Blocks α/γ stay live for Step 8's direct bump path.
- **Source**: user

## Decision 3: Risk posture for step8-family semantics
- **Question**: Strict behavior parity, or allow consolidation?
- **Resolution**: Allow safe consolidation — reuse the existing internal `run_rebase_rebump` machinery where step8-family semantics already coincide, accepting a slightly larger refactor for less duplication.
- **Source**: user

## Decision 4: Current state correction (wrong premise in issue body)
- **Question**: Do BOTH `step8b_rebase` and `step8_apply_bump_same_version` still drive the sub-procedure prompt-side, as the issue claims?
- **Resolution**: NO. `step8_apply_bump_same_version` is **already absorbed** — `_run_step8_same_version_mechanically()` (ship-pr.sh, landed in #2649 / Fixes #2395, before #3299 was filed) runs the same-version recovery internally with a one-retry `STEP8_SAME_VERSION_RETRY_COUNT` guard and never `exit 5`s. The line-1413 `CALLER_KIND step8_apply_bump_same_version` set is vestigial. The ONLY remaining prompt-side rebase/re-bump handoff is `step8b_rebase` (ship-pr.sh line 1469 `exit 5`). Part 1 therefore narrows to: absorb `step8b_rebase`, plus retire the now-dead `step8_apply_bump_same_version` exit-5 references (SKILL.md exit-5 handler prose + vestigial state set).
- **Source**: codebase (`scripts/ship-pr.sh`, `git log -S`)

## Decision 5: Hard constraints (must not break)
- **Question**: What invariants and tokens must the absorption preserve?
- **Resolution**:
  - Preserve contract `caller_kind` tokens (`step8b_rebase`, `step8_apply_bump_same_version`, `step12_phase4`, `ship_pr_pre_push`) — do NOT rename.
  - Keep `conflict-resolution.md` Phase 1–4 (LLM) prompt-side via the `exit 5` + `CALLER_KIND` mechanism, mirroring the `ship_pr_pre_push` / `--resume-phase ship-pr-rrr-phase14` precedent. Do NOT script conflict resolution.
  - Preserve version-bump-freshness (Load-Bearing Invariant #1) and degraded-git fail-closed (Invariant #3): pre/post `check-bump-version.sh` STATUS-first gating, classify-bump version-regression correction, reasoning-artifact rewrite.
  - Preserve step8-family failure semantics: hard failure → `STALL_TRACKING=true` → Step 18 (no bail-to-12d, no CI loop), and the `step8_apply` one-retry guard.
  - Preserve the `postbump` force-push-gate ownership (`implement-finalize.sh postbump` Phase 4 via `check-remote-branch.sh` trichotomy + `.postbump-phase` checkpoint resume).
  - Update the heavy test surface (`test-ship-pr.sh`, `test-ship-pr-rebase-phase14.sh`, `test-implement-rebase-macro.sh`, `test-step2-dispatch.sh`, bump-verification regression coverage).
  - Keep edits disjoint from the parallel "Step 18" `ship-pr.sh` issue (no concurrent two-issue edits to `ship-pr.sh`).
- **Source**: codebase + issue body
