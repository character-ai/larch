## Proposed Design Outline

### Goals
- Absorb the last prompt-side rebase/re-bump handoff (`step8b_rebase`) into `ship-pr.sh`, reusing the internal `run_rebase_rebump` machinery, so the SKILL.md Step 8+ surface shrinks.
- Fold the inline `CLONE_TAG_FULL` computation into `ship-pr.sh` argv-init; derive `--expected-tmpdir-basename-prefix` internally.
- Retire the now-dead `step8_apply_bump_same_version` exit-5 prose (already mechanical via `_run_step8_same_version_mechanically`, since #2649).

### Non-goals
- Do NOT script `conflict-resolution.md` Phase 1–4 — keep it prompt-side via `exit 5` + `CALLER_KIND` (the `ship_pr_pre_push` precedent).
- Do NOT delete `rebase-rebump-subprocedure.md` or `bump-verification.md` (retain; Blocks α/γ stay live for Step 8's direct bump).
- Do NOT rename contract `caller_kind` tokens or change `postbump` force-push-gate ownership.

### Approach sketch
- On postbump `STATUS=conflict` / `RESUME_PHASE=force-push-gate`, run drop/rebase/re-bump **internally** (reuse `run_rebase_rebump` / `_run_rebase_rebump_from_step3`) instead of `exit 5` to the Markdown sub-procedure.
- Keep the Phase 1–4 escape: non-bump conflict → `exit 5` `CALLER_KIND=ship_pr_pre_push` + `--resume-phase ship-pr-rrr-phase14`, with a new resume route back to the postbump force-push-gate.
- Apply step8-family failure semantics internally: hard failure → `STALL_TRACKING=true` → `exit_stall 8b` (Step 18); no CI loop, no 12d.
- Compute `CLONE_TAG_FULL` (CLONE_TAG env, else `basename $PWD`) inside argv-init; keep `--expected-tmpdir-basename-prefix` as an optional override for back-compat/tests.
- Trim the SKILL.md Step 8+ `Invoke:` block and exit-5 handler for the absorbed `step8b_rebase` + dead `step8_apply_bump_same_version`.

### Surfaces in scope
- `scripts/ship-pr.sh` (postbump conflict handler, argv-init, resume dispatch) + `scripts/ship-pr.md`
- `skills/implement/SKILL.md` (Step 8+ Invoke block, exit-5 handler, CLONE_TAG_FULL)
- Tests: `scripts/test-ship-pr.sh`, `scripts/test-ship-pr-rebase-phase14.sh`, `scripts/test-implement-rebase-macro.sh`
- Retained (cross-referenced only): `rebase-rebump-subprocedure.md`, `bump-verification.md`

### Open questions
- Keep `--expected-tmpdir-basename-prefix` as an optional override after internal derivation (recommended, back-compat for tests), or remove it for full simplification?
