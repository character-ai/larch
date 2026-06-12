# Review Round 2

- Mode: `diff`
- 10 accepted, 6 rejected (6 neutral)

## Accepted Findings

### FINDING_10: Invalid boolean CLI values are coerced to false
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Invalid boolean strings like `--forked-target tru` proceed as false instead of failing fast. This can route a forked run onto the wrong repo or branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Add choices or explicit validation in invoke_main, and return usage exit 1 for invalid boolean flag values.


### FINDING_13: Bootstrap invoke, coder, and routing contracts lack targeted tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-contract-preservation-output.txt, dyn-test-target-drift-output.txt
- **Severity**: important
- **Concern**: The live Step 0 bootstrap entrypoint, coder waterfall, routing parser, env precedence, exit-code envelope, and resume coder preservation paths have little or no pytest coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add invoke_main tests with monkeypatched run_bootstrap covering exits 0/1/2, env fallback precedence, and routing-file edge cases
  - From cursor-specialist-testing-output.txt: Add _phase_coder unit tests per plan test_coder_select_* matrix
  - From codex-specialist-testing-output.txt: Port the missing plan-named bootstrap tests, including subprocess tests for python3 python/cli.py bootstrap invoke and skills/implement/scripts/step-0-bootstrap.sh.
  - From dyn-contract-preservation-output.txt: Add `test_routing_parser_preserve_coder_on_resume` asserting that `--resume true` output contains no `coder=`/`unset coder` lines while still exporting other keys from file-first merge.
  - From dyn-test-target-drift-output.txt: Port the highest-risk retired harness scenarios first: full `bootstrap invoke` initial/resume paths, env-vs-flag precedence, coder selection matrix, routing-envelope write/parse edge cases, emergency-bypass variants, and `STEP_FAILED` stderr mapping; keep Makefile targets partitioned until each group has dedicated tests.


### FINDING_14: Admission gate and fork-env matrices are under-tested
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-contract-preservation-output.txt, dyn-test-target-drift-output.txt
- **Severity**: important
- **Concern**: Admission gate exits, resume ordering, blocker behavior, skip-clean sentinel handling, and fork-env success or failure paths lack parity tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add stubbed gh/parent-issue tests for gate exits 4-7, resume ordering, and fork_env success/failure paths
  - From codex-specialist-testing-output.txt: Add the plan-listed python/test_admission.py cases before relying on the deleted Bash harness coverage.
  - From dyn-contract-preservation-output.txt: Implement the plan’s `python/test_admission.py` matrix at minimum for resume sentinel + gh-failure ordering, managed/missing-designed/audit-label/report-title exits, blocker fail-open, and fork-env atomic caller-env write.
  - From dyn-test-target-drift-output.txt: Add the plan’s `test_fork_env_success`, `test_fork_env_no_upstream`, `test_fork_env_parse_failure`, and `test_fork_env_caller_env_atomic` at minimum; add resume-sentinel and blocker fail-open gate tests before deleting further Bash references; consider a dedicated `test_fork_env.py` or `-k fork_env` Makefile pin so `test-implement-fork-env` cannot pass vacuously.


### FINDING_15: Dirty-tree baseline and marker behavior are under-tested
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-test-target-drift-output.txt
- **Severity**: important
- **Concern**: Dirty-tree baseline, checkpoint, sidecar, missing-baseline, git-failure, and scope-marker contracts lack parity tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add git-fixture baseline tests for dirty/clean/ambiguous-missing-baseline and sidecar emission
  - From codex-specialist-testing-output.txt: Add the plan-listed baseline, checkpoint, sidecar, missing-baseline, git-failure, and scope-marker tests.
  - From dyn-test-target-drift-output.txt: Port the retired `test-check-mid-run-dirty-tree.sh` and `test-check-scope-reduction-marker.sh` scenarios into the named pytest functions from the plan; keep `test-check-scope-reduction-marker` and `test-check-mid-run-dirty-tree` Makefile targets on disjoint `-k` subsets until both suites are non-empty.


### FINDING_18: Routing-file write failure can break stdout envelope
- **Reviewer(s)**: dyn-subprocess-safety-output.txt
- **Severity**: latent
- **Concern**: `invoke_main` writes the routing file before printing the envelope and does not catch `OSError`. A write failure can produce a traceback and no stdout envelope even after `run_bootstrap` succeeds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-subprocess-safety-output.txt: Wrap the routing-file write in `try/except OSError`; on failure, still print the filtered envelope to stdout, emit a stderr warning, and return a documented exit code (or match the symlink-refusal path and return `0` with envelope-only output).


### FINDING_19: `fork_env_main` atomic write failures are unhandled
- **Reviewer(s)**: dyn-subprocess-safety-output.txt
- **Severity**: latent
- **Concern**: `fork_env_main` can raise an unhandled `OSError` while writing `caller-env.sh`, aborting before expected KVs and exit-code mapping.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-subprocess-safety-output.txt: Wrap the atomic write in `try/except OSError`, map failures to exit `2` with a stderr diagnostic, and use `tempfile.mkstemp` in the destination directory (same pattern as `tokens._atomic_text` / `session_env._atomic_write`) to avoid predictable temp-path races.


### FINDING_2: Deleted Bash harnesses were replaced by thin pytest coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-contract-preservation-output.txt, dyn-test-target-drift-output.txt, dyn-subprocess-safety-output.txt
- **Severity**: important
- **Concern**: The branch retargets retired Bash harnesses to a small pytest set. CI can pass while bootstrap, admission, fork-env, dirty-tree, routing, and subprocess-safety contracts remain untested or under-tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port critical cases from deleted harnesses per plan manifest before merge; prioritize gate resume, invoke env precedence, baseline ambiguous-untracked, scope-marker Concern/severity paths
  - From cursor-specialist-testing-output.txt: Migrate the plan's enumerated test_* cases (or equivalent contract tests) before treating acceptance as satisfied
  - From codex-specialist-testing-output.txt: Port the missing plan-named bootstrap tests, including subprocess tests for python3 python/cli.py bootstrap invoke and skills/implement/scripts/step-0-bootstrap.sh.
  - From dyn-contract-preservation-output.txt: Port the plan’s named test list into the three pytest modules (or restore targeted harness slices until parity is proven), and split Makefile targets so each domain runs its own scoped pytest selection instead of re-running the same minimal file under multiple names.
  - From dyn-test-target-drift-output.txt: Either restore parity by implementing the plan’s named pytest cases (below) and/or split Makefile targets to run disjoint test subsets (e.g. `-k` filters per retired harness), and add a manifest test that asserts each retired harness name maps to a non-empty, non-overlapping pytest selection until parity is reached.
  - From dyn-subprocess-safety-output.txt: Add the missing pytest cases, including symlink/non-regular routing targets, failed `replace` handling, and fork-env atomic-write failure mapping.


### FINDING_5: Tracking rename failure now stalls bootstrap
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Rename-to-`[IMPLEMENTING]` failure now triggers tracking bail and prevents plan or coder phases from running.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Make rename failure warning-only again and continue to run-log init, persist-run-flags, and post-tracking-issue.sh.


### FINDING_8: Explicit external coder fallback misses required warning
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: If an explicitly requested external coder is unavailable but another external coder is available, fallback can occur silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Emit and append a warning whenever an explicitly requested external coder is unavailable, while keeping coder_fallback=true only for Claude fallback.


### FINDING_9: Admission error can leak `gh` stderr
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: On `gh issue view` failure, Python emits stderr inside `ADMISSION_ERROR` stdout KV. Bash discarded stderr, so auth or token diagnostics can now leak into orchestrator-captured stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: On failure emit stdout-only or redact via python/cli.py redact secrets before _emit_kv; add pytest asserting stderr is not echoed.


