### OOS_14: [OUT_OF_SCOPE] remaining Bash caller cutover still needed
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Some Bash callers, including snapshot-untracked paths and broader B1 consumer cutover/deletion work, remain outside this branch and should be completed with parity gates before wrapper removal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### OOS_15: [OUT_OF_SCOPE] stage_and_push aborts rebase after keep-on-conflict failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `stage_and_push` may abort an in-progress rebase after keep-on-conflict failure, potentially discarding conflict state during CI-fix defer rebase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### OOS_16: [OUT_OF_SCOPE] cli.py lacks holistic quiet_init dispatch
- **Reviewer(s)**: dyn-contract-parity-output.txt
- **Severity**: latent
- **Concern**: `python/cli.py` does not call `logging_util.quiet_init()` on dispatch, a broader quiet-routing gap to address if subprocess callers inherit quiet env during cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-parity-output.txt: Address the concern above.


### OOS_17: [OUT_OF_SCOPE] migration-lint headers have doc drift
- **Reviewer(s)**: dyn-migration-lint-logic-output.txt
- **Severity**: nit
- **Concern**: `python/migration_lint.py` and `python/migrated-scripts.tsv` headers still describe “full path only” matching after docs changed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-migration-lint-logic-output.txt: Address the concern above.


