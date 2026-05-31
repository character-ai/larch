### OOS_1: [OUT_OF_SCOPE] Branch mixes #3227 stderr-tail with #3229 cleanup
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-contracts-output.txt, dyn-stderr-tails-output.txt
- **Severity**: latent
- **Concern**: The branch bundles unrelated #3229 cleanup retention work, run-log churn, and broad doc/skill changes alongside #3227 stderr-tail behavior. Isolated review or revert of stderr-tail-only work is harder; plan-to-diff tracing shows substantial unrelated churn.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Split PRs or single feature commit series per issue.
  - From cursor-specialist-plan-fidelity-output.txt: Split or label commits so #3227 PR scope matches the implementation plan surface.
  - From dyn-bash-contracts-output.txt: Commits `2f375cd1e` / `475777f42` carry cleanup (#3229) and run-log churn unrelated to #3227 stderr-tail behavior; the bash-contract review above targets the stderr-tail producer/consumer edits in `3de7ceaaf` and follow-up `f3b107fa6`.
  - From dyn-stderr-tails-output.txt: The branch bundles unrelated #3229 cleanup retention work (`skills/cleanup/scripts/cleanup.sh`, docs, tests). It does not affect stderr-tail integration but widens review surface beyond #3227.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_10: [OUT_OF_SCOPE] Recovery waterfall leaves launcher stdout temp files
- **Reviewer(s)**: dyn-shippr-waterfall-output.txt
- **Severity**: nit
- **Concern**: `run_recovery_waterfall` may leave up to three `recovery-*-launcher-$$.out` files per invocation under `$IMPLEMENT_TMPDIR` without explicit cleanup. Low impact given tmpdir lifecycle.
- **Suggested revisions (informational for voters; coder decides)**:

Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_2: [OUT_OF_SCOPE] Cursor auth preflight tail gap noted as follow-up only
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Cursor auth preflight does not write stderr-tail; only the model-args path does. Preflight failures may have `SIDECAR_LOG` but no `${TRANSCRIPT}.stderr-tail` for step2 emit. Marked out of scope for the #3227 plan as a follow-up if desired (same behavioral gap as in-scope FINDING_1, framed as plan boundary).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: follow-up write_failed_agent_stderr_tail on preflight branch if desired


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] `_collect_rc` dead state (plan-review collector)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-contracts-output.txt
- **Severity**: latent
- **Concern**: `_collect_rc` in `plan-review-loop.sh` is assigned but never read after the tee/`set -e` fix. Not a surfacing regression by itself; dead state may confuse future readers expecting collector-rc-driven branching.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Remove variable or branch on it if future logic needs explicit collect failure handling.
  - From cursor-specialist-plan-fidelity-output.txt: Use _collect_rc in downstream failure handling or drop the variable with a comment that only the assignment prevents set -e abort.
  - From dyn-bash-contracts-output.txt: `_collect_rc` is assigned but never read; collector failure handling appears unchanged aside from not aborting the assignment under `set -e`. The new harness case still validates the tee path; this is dead state, not a surfacing regression by itself.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_4: [OUT_OF_SCOPE] Double `write_failed_agent_stderr_tail` on Codex path
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-stderr-tails-output.txt
- **Severity**: nit
- **Concern**: `run_codex` / launcher may double-write `${run_dir}/codex.log.stderr-tail` via `run-external-agent` `--stderr-sink` and an explicit `write_failed_agent_stderr_tail`. Redundant work on the same source; low clobber risk with current wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Optional: skip launcher write when run-external-agent already produced tail.
  - From dyn-stderr-tails-output.txt: `run_codex` may double-write `${run_dir}/codex.log.stderr-tail` (via `run-external-agent.sh` with `--stderr-sink` and the explicit `write_failed_agent_stderr_tail`); redundant but same source, not a clobber risk like `cursor.wrapper.log`.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_5: [OUT_OF_SCOPE] Step 5 harness gap as accepted plan coverage deferral
- **Reviewer(s)**: dyn-stderr-tails-output.txt
- **Severity**: latent
- **Concern**: Plan acceptance called for Step 5 harness coverage of parse-before-`rm` and terminal-arm surfacing; the branch updates `review-implement-step5-loop.sh` but adds no dedicated offline test (plan allowed documenting the gap). Framed as coverage gap, not a proven runtime wiring bug in the diff.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_6: [OUT_OF_SCOPE] Cleanup depth-bound tradeoff (pre-existing, documented)
- **Reviewer(s)**: dyn-cleanup-retention-output.txt
- **Severity**: latent
- **Concern**: Activity deeper than five levels does not protect a session directory from deletion. Documented in docs and `SECURITY.md` as intentional conservative disk reclamation, not a branch regression.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_7: [OUT_OF_SCOPE] Asymmetric `/tmp` vs cache enumeration (pre-existing)
- **Reviewer(s)**: dyn-cleanup-retention-output.txt
- **Severity**: latent
- **Concern**: Cache pass lists all non-symlink top-level entries; `/tmp` pass only considers entries with `-mtime +N`. A `/tmp` directory with fresh top-level mtime but stale contents may never enter removal evaluation, unlike cache shape with the same interior staleness.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### OOS_8: [OUT_OF_SCOPE] Top-level cache non-directories never removed (pre-existing)
- **Reviewer(s)**: dyn-cleanup-retention-output.txt
- **Severity**: nit
- **Concern**: `should_remove_by_age` returns immediately for non-directories; loose files under `larch/sessions/` are never removed. Docs describe directory-oriented removal; not introduced by this branch.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_9: [OUT_OF_SCOPE] Cleanup branch delta is mostly test/doc alignment
- **Reviewer(s)**: dyn-cleanup-retention-output.txt
- **Severity**: nit
- **Concern**: `cleanup.sh` logic is largely unchanged aside from comments; branch fixes prior doc drift and improves `write_stub_find_failure` (fail only on `-maxdepth 5`). Informational scope note for reviewers tracing #3229 vs runtime behavior.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

