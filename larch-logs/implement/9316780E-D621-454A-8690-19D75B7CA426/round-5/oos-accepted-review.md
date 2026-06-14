### OOS_71: [OUT_OF_SCOPE] Absorbed bash helpers still present alongside Python cutovers
- **Reviewer(s)**: dyn-migration-parity-output.txt
- **Severity**: nit
- **Concern**: Absorbed bash helpers (`oos-issue-cap.sh`, `stall-recovery-report.sh`, etc.) remain alongside Python cutovers. Incomplete migration cleanup rather than a runtime defect introduced by the new modules alone.
- **Suggested revisions (informational for voters; coder decides)**:


### OOS_72: [OUT_OF_SCOPE] test_step_7a.py missing bash harness diagram cases
- **Reviewer(s)**: dyn-migration-parity-output.txt
- **Severity**: latent
- **Concern**: `python/test_step_7a.py` does not cover diagram-rejected cleanup, diagram-failure exit `0`, or warning append paths that `test-step-7a.sh` still asserts.
- **Suggested revisions (informational for voters; coder decides)**:


### OOS_73: [OUT_OF_SCOPE] implement-finalize.sh parallel bash authority remains
- **Reviewer(s)**: dyn-callsite-routing-output.txt
- **Severity**: nit
- **Concern**: `scripts/implement-finalize.sh` is still a full bash implementation (~1100 lines) while `ship-pr.sh` and `step-18-finalize.sh` call `python/cli.py implement-finalize`. Parallel authorities predate full deletion; not introduced by this branch's Python wrappers alone.
- **Suggested revisions (informational for voters; coder decides)**:


### OOS_74: [OUT_OF_SCOPE] SECURITY.md still documents implement-finalize.sh postbump
- **Reviewer(s)**: dyn-callsite-routing-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md:346` still documents `implement-finalize.sh postbump`; unchanged in this diff. `ship-pr.sh` already calls `python/cli.py implement-finalize postbump`.
- **Suggested revisions (informational for voters; coder decides)**:


### OOS_75: [OUT_OF_SCOPE] materialize-manifest-oos.md lists stale consumers
- **Reviewer(s)**: dyn-callsite-routing-output.txt
- **Severity**: nit
- **Concern**: `materialize-manifest-oos.md` still lists `ship-pr.sh` `pr-prep` and `python/ship.py` `_oos_gate` as consumers without matching call sites. The "ship pre-trigger" gap exists on `main` too; this branch only swapped script names in sibling docs without adding wiring.
- **Suggested revisions (informational for voters; coder decides)**:


### OOS_76: [OUT_OF_SCOPE] C4c deletion/manifest work incomplete (lint-retired-scripts passes)
- **Reviewer(s)**: dyn-lint-readiness-output.txt
- **Severity**: nit
- **Concern**: Absorbed bash still ships (`implement-finalize.sh`, `stall-recovery-report.sh`, `flush-execution-issues.sh`, etc.), and `python/migrated-scripts.tsv` has no C4c rows for those paths yet. `make lint-retired-scripts` passes because the files still exist on disk.
- **Suggested revisions (informational for voters; coder decides)**:


### OOS_77: [OUT_OF_SCOPE] Retired oos-disposition-gate.sh remains in tree
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Retired gate shell remains though checkpoint uses Python. Dual-implementation drift risk only; delete after confirming no live callers per plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Delete after confirming no live callers per plan.


