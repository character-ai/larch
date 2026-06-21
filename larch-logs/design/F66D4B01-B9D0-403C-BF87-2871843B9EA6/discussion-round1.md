## Decision 1: Lib retirement aggressiveness
- **Question**: After G1-G13 merged, most terminal libs still have live consumers from the deliberately-kept bash surface. How aggressive should E3 be about retiring shared libs?
- **Resolution**: Retire ONLY libs proven to have zero live consumers (verified across .sh/.md/.py/.tsv/.json, excluding larch-logs and self). `lib-prune-decision.sh` is confirmed orphaned. Document every other lib as legitimately kept by hooks/linters/thin-wrappers/test-harnesses. Do NOT repoint or edit the kept surface to force more retirements.
- **Source**: user

## Decision 2: Scope organization
- **Question**: Keep E3 as one plan or split the work-streams into separate issues?
- **Resolution**: One consolidated plan. No decomposition panel. With lib work trimmed (Decision 1) and CI deferred (Decision 3), the remaining work is mostly small doc/lint/topology edits. Rely on the Step 2b.5 plan-size gate to flag if it grows too large.
- **Source**: user

## Decision 3: CI test-harness shard rebalance
- **Question**: How should E3 handle the "rebalance CI test-harness shards" scope item?
- **Resolution**: Defer to the dedicated `/rebalance-tests` skill. Do NOT hand-edit shard manifests (`python/shard-assignments.json`, harness shard packer) in this plan. Note in the plan that `/rebalance-tests` should run separately if/when harness counts actually shift. The premise of "mass bash-harness deletion" did not materialize in this tree (92 test-*.sh remain).
- **Source**: user

## Decision 4: Hard constraints (must not break)
- **Question**: What existing behavior must be preserved?
- **Resolution**: The deliberately-kept bash surface must keep working: the 9 hooks, the 6 bash-targeting linters, sleep-seconds.sh (consumed by python/stall_recovery.py), the ~50 thin cli.py delegation wrappers, and the test harnesses. `make lint && make py-lint && make py-test` must stay green; `make lint-retired-scripts` must be clean. Linter scope-down narrows their target globs to the residual bash surface; it must not weaken guard coverage for files that still exist.
- **Source**: codebase + issue DoD

## Decision 5: Orphan-script deletion safety
- **Question**: How to handle "delete remaining orphaned utility scripts"?
- **Resolution**: Verify-first. Only delete a script proven to have zero consumption across all file types (.sh, .md, .py, manifests, CI workflows, Makefile), excluding larch-logs run artifacts. Do not assume orphan status from the issue text.
- **Source**: codebase + issue text
