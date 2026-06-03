### OOS_1: [OUT_OF_SCOPE] Stale sibling docs cite active rebase-rebump sub-procedure consumers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/ci-wait.md` and related sibling docs still cite active rebase-rebump sub-procedure consumers; future edits could reintroduce sub-procedure calls from stale documentation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Refresh sibling `.md` files in a docs-only pass (Phase 5 or earlier).


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_10: [OUT_OF_SCOPE] `installation-and-setup.md` / `SECURITY.md` still describe active bump hook hygiene
- **Reviewer(s)**: dyn-hook-neutralization-integrity-output.txt
- **Severity**: nit
- **Concern**: Prose still describes `hook-post-bump-version.sh` as active resume hygiene / halt protection alongside `hook-stop-fail-close.sh`; not updated in the hook-focused diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-hook-neutralization-integrity-output.txt: should be swept in the docs-sync pass called out in the plan.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_11: [OUT_OF_SCOPE] Observation — `run_rebase_rebump` skipping `ship-branch-guard` is intentional
- **Reviewer(s)**: dyn-shell-state-residue-output.txt
- **Severity**: nit
- **Concern**: Reviewer marked as observation only: inline comment documents intentional omission of `ship-branch-guard` in `run_rebase_rebump`; not introduced by Phase 1 writers. Listed for traceability; in-scope FINDING_8 captures the actionable edge-case concern from specialist review.
- **Suggested revisions (informational for voters; coder decides)**:

Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### OOS_2: [OUT_OF_SCOPE] `launch-codex-ci.md` documents retired bump/changelog CI roles
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Launcher docs still list `bump-classify` and `changelog-draft` roles no longer used by `ship-pr.sh`, creating confusion when wiring new CI roles.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Prune roles from launcher docs when bump/changelog CI paths are deleted in Phase 5.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] `docs/linting.md` points ci-wait sync policy at retirement stub
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `docs/linting.md` still references the retirement stub `rebase-rebump-subprocedure.md` for ci-wait synchronous-invocation policy; readers find no live contract there.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Point `linting.md` at SKILL.md or `ship-pr.md` for ci-wait contract.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_4: [OUT_OF_SCOPE] `skills/alias/SKILL.md` still says implement includes version bump
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Alias skill prose still describes implement as including version bump; same drift as `docs/skills.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Same wording fix as `docs/skills.md` when touching alias docs.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_5: [OUT_OF_SCOPE] PR body template still references version-bump-reasoning batch
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `skills/implement/references/pr-body-template.md` still lists version bump reasoning in larch-logs ownership; Step 9a authors may assume a batch new runs no longer produce.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Qualify or remove version-bump-reasoning from the larch-logs ownership list.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_6: [OUT_OF_SCOPE] `--changelog-bullets-file` parsed but unused in `run_postbump`
- **Reviewer(s)**: dyn-shell-state-residue-output.txt
- **Severity**: nit
- **Concern**: `implement-finalize.sh` still parses and path-validates `--changelog-bullets-file` but never reads it in `run_postbump` after Step 8a removal; harmless for `ship-pr.sh` but stale vs usage string and `SECURITY.md`.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_7: [OUT_OF_SCOPE] `step10_rebase_then_evaluate` dead branch in evaluate-failure dispatch
- **Reviewer(s)**: dyn-shell-state-residue-output.txt
- **Severity**: nit
- **Concern**: `scripts/ship-pr.sh` evaluate-failure dispatch still includes `step10_rebase_then_evaluate` with no in-repo writer after sub-procedure removal (unless external tooling injects `CALLER_KIND`).
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_8: [OUT_OF_SCOPE] `hook-post-bump-version.sh` still registered on every Skill PostToolUse
- **Reviewer(s)**: dyn-hook-neutralization-integrity-output.txt
- **Severity**: nit
- **Concern**: Stub hook remains registered on every Skill invocation until Phase 5 removal; side-effect-free but pays a spawn per Skill call.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_9: [OUT_OF_SCOPE] No replacement harness asserting PostToolUse bump hook stays inert
- **Reviewer(s)**: dyn-hook-neutralization-integrity-output.txt
- **Severity**: nit
- **Concern**: `test-implement-anti-halt.sh` structural checks for bump hooks were removed without a small regression test that the PostToolUse hook stays inert before Phase 5 deletion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-hook-neutralization-integrity-output.txt: e.g., invoke the hook and assert empty stdout / exit 0


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

