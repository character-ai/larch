### FINDING_1: Makefile/agent-lint wire untracked `test-ship-pr-rebase.sh`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `Makefile` and `agent-lint.toml` register `scripts/test-ship-pr-rebase.sh` for `make test-harnesses-13` / `make lint`, but the harness is not committed in `HEAD`. A clean clone or CI run fails with a missing script path even though Phase 1 acceptance expects green harnesses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add and commit `scripts/test-ship-pr-rebase.sh` (and sibling `.md`), or remove Makefile/agent-lint references until the harness ships.
  - From cursor-specialist-testing-output.txt: git add and commit `scripts/test-ship-pr-rebase.sh` before merge
  - From cursor-specialist-edge-cases-output.txt: Commit `scripts/test-ship-pr-rebase.sh` or remove Makefile and agent-lint references until it ships.
  - From cursor-specialist-plan-fidelity-output.txt: Commit `scripts/test-ship-pr-rebase.sh` (and sibling contract doc if used) so the registered target exists in the repo.


### FINDING_11: `docs/skills.md` still claims `/implement` includes version bump
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The `/docs/alias` bullet still describes the implement pipeline as including a version bump. After Phase 1, operators may expect per-PR `plugin.json` bumps from `/implement` when versioning is `/release` or manual `bump-version` only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Update the bullet to match `workflow-lifecycle.md`: implement does review and PR; versioning is `/release` or manual bump-version only.


### FINDING_12: `docs/review-agents.md` still lists version-bump reasoning as normal run-log output
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Run-log description still treats `version-bump-reasoning.md` as normal `/implement` output. Readers may treat its absence on new runs as regression or incomplete logging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Revise the sentence to note Phase 1 removal on the ship path and legacy pre–Phase 1 runs only.


### FINDING_13: Fork `main` may pass `ship-pr` but fail `validate_postbump_state_branch`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Fork dry-run with `BRANCH_NAME=main` can die at postbump load in `validate_postbump_state_branch` despite fork carve-outs earlier in `ship-pr.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add `FORKED_TARGET` carve-out to `validate_postbump_state_branch` and test it.


### FINDING_2: `implement-finalize.md` invariants disagree with Phase 1 SKILL postbump semantics
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `scripts/implement-finalize.md` still documents Step 8 conflict-resume / force-push-gate behavior that `skills/implement/SKILL.md` has replaced with stall-only postbump 8b conflicts and legacy-checkpoint-only resume. Maintainers may “fix” SKILL or finalize against the wrong contract, leaving resume/checkpoint behavior ambiguous.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Update `implement-finalize.md` invariants and Edit-in-sync footer to match SKILL.md postbump stall semantics and legacy-checkpoint-only resume.


### FINDING_20: `sessionstart-health.sh` still advises obsolete post-`/bump-version` recovery chain
- **Reviewer(s)**: dyn-hook-neutralization-integrity-output.txt
- **Severity**: important
- **Concern**: Phase 1 retired bump halt protection in `hook-stop-fail-close.sh` and neutralized `hook-post-bump-version.sh`, but SessionStart still warns about a pending post-`/bump-version` boundary when `.bump-version-armed` exists without `postbump-state.sh`, directing operators through `check-bump-version.sh --mode post` and the old postbump chain. Legacy or manually armed tmpdirs get misleading recovery text with no mechanical backstop on the current hot path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-hook-neutralization-integrity-output.txt: Retire the bump-boundary block in `sessionstart-health.sh` (and the paired cases in `scripts/test-sessionstart-health.sh` / `sessionstart-health.md`) the same way `hook-stop-fail-close.md` documents Phase 1 retirement, leaving only the post-/review advisory aligned with the preserved Stop hook.


### FINDING_21: `hook-stop-fail-close.sh` header still mentions post-bump-version protection
- **Reviewer(s)**: dyn-hook-neutralization-integrity-output.txt
- **Severity**: nit
- **Concern**: Script header still describes “post-review and post-bump-version halt protection” though only the post-review block remains; incident debugging may expect a mid–Step 8 stop block that no longer exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-hook-neutralization-integrity-output.txt: Reword the header (and optionally the `hook-stop-fail-close.md` intro if needed) to state post-/review protection only, matching the retired bump note already in the sibling contract file.


### FINDING_3: `rebase-push.md` still documents retired Re-bump Sub-procedure paths
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `scripts/rebase-push.md` still describes the Re-bump Sub-procedure for Steps 8b/10/12 and retired `step8`/`step10`/`step12` caller families. A maintainer following that contract could restore wrong orchestration or exit semantics after Phase 1.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Rewrite `rebase-push.md` per Phase 1: 8b plain `--no-push` abort+stall; CI via `run_rebase_rebump` + exit 4 `ship_pr_pre_push`; remove sub-procedure references.


### FINDING_5: Legacy `force-push-gate` checkpoint can skip postbump rebase on resume
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Resuming `implement-finalize.sh postbump` with a pre–Phase 1 `.postbump-phase` containing `force-push-gate` can run `git-force-push` without `run_step8b_rebase`, so an unrebased or conflict-paused branch may be pushed to the remote.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Clear or reject legacy `force-push-gate` checkpoints at postbump entry in Phase 1 (e.g., delete stale `.postbump-phase` or fail closed unless a new writer sets it after an explicit validated resume).
  - From cursor-specialist-edge-cases-output.txt: Invalidate stale `force-push-gate` checkpoints on Phase 1 entry or fail closed unless resume is explicitly valid.


### FINDING_6: Stale non–`force-push-gate` `.postbump-phase` values cause `postbump-state-corrupt` stall
- **Reviewer(s)**: dyn-shell-state-residue-output.txt
- **Severity**: important
- **Concern**: Phase 1 removed writers of `.postbump-phase` on postbump conflict (now `STATUS=rebase-failed` with no checkpoint), but `run_bump_phase` still enters `implement-finalize.sh postbump` without normalizing a pre-existing checkpoint. `read_postbump_checkpoint` accepts only `force-push-gate`; any other non-empty phase (legacy names, corruption, test debris) yields `STATUS=postbump-state-corrupt` and `exit_stall 8b`, blocking shipping despite fresh `BUMP_TYPE=NONE` stubs — contrary to tolerate-and-ignore goals for resumed sessions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-state-residue-output.txt: At the start of `run_bump_phase` (before `write_postbump_state`), read `.postbump-phase` and either `rm -f` it when the phase is not exactly `force-push-gate`, or call `clear_postbump_checkpoint` unless you are intentionally resuming a legacy force-push-gate checkpoint; optionally add a harness case that seeds `bogus-phase` and asserts a clean rebase+push rather than `postbump-state-corrupt`.


### FINDING_7: Stale `CALLER_KIND` on resumed `ship-pr-state.sh` can misroute `evaluate-failure`
- **Reviewer(s)**: dyn-shell-state-residue-output.txt
- **Severity**: latent
- **Concern**: Resume is mostly safe for extra bump keys, but legacy `CALLER_KIND=step8b_rebase` or `step8_apply_bump_same_version` from pre–Phase 1 Exit-5 handoffs is never cleared on bump re-entry. At `PHASE=evaluate-failure`, the switch can still branch on `step10_rebase_then_evaluate` and call `run_evaluate_failure ci-initial` with a stale kind that no live writer sets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-state-residue-output.txt: Clear `CALLER_KIND` (and clear or normalize `RESUME_PHASE` when it is a retired bump-recovery token) at the start of `run_bump_phase` or immediately after a successful postbump, so resumed state cannot carry pre–Phase 1 orchestration tokens into CI evaluation.


### FINDING_8: `run_rebase_rebump` omits `ship-branch-guard` present in `run_bump_phase`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `run_rebase_rebump` deliberately skips the `ship-branch-guard` checks in `run_bump_phase` (empty branch, name mismatch, non-forked main/master). CI-fix rebase may run on the wrong branch or detached HEAD without the bump-phase safety checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Share `ship-branch-guard` (or equivalent) at `run_rebase_rebump` entry.


