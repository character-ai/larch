# Review Round 3

- Mode: `diff`
- 8 accepted, 6 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Missing Step 0/1 wrapper regression tests (plan acceptance gaps)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-retirement-coverage-output.txt
- **Severity**: important
- **Concern**: Plan-mandated wrapper regression tests for `step0-route`, `step0-session`, degraded-gate edge cases, and related Step 0/1 abort paths are largely missing despite acceptance criteria listing them explicitly. Gaps include route-level re-validation of `POSITIONAL_KIND` (non-numeric issue positional, invalid kinds from `.design-step0-parsed.env`, verbal route without `ISSUE_NUMBER`), `BRAINSTORM_PREFIX`, resume `@` KVs, pre-set `REPO`, session stderr-only failure, `BOTH_DOWN_SEEN` negative guard, and other enumerated cases. Regressions in route positional re-validation, `REPO` preservation, `BRAINSTORM_PREFIX` handling, or session `PREFLIGHT` stderr relay could merge without pytest catching them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add the missing pytest cases enumerated in the plan (non-numeric issue positional, verbal without ISSUE_NUMBER, BRAINSTORM_PREFIX, resume@ KVs, pre-set REPO, session stderr-only failure, BOTH_DOWN_SEEN negative guard, etc.).
  - From dyn-retirement-coverage-output.txt: Add route-focused pytest cases that seed `.design-step0-parsed.env` with bad values and assert abort before subprocess/`gh` calls, matching the stderr messages at `python/design_lifecycle.py:1010-1017`.


### FINDING_12: No test that `step0-init` wrapper stdout stays clean
- **Reviewer(s)**: dyn-launcher-cutover-output.txt
- **Severity**: important
- **Concern**: Plan acceptance required that `step0-init` wrapper stdout not leak `INIT_STATUS=` / `RENAMED=` KVs from subprocess capture; implementation captures init-runparams stdout to a temp file (`python/design_lifecycle.py:1151-1204`), but no test asserts wrapper stdout is empty on the success path when the mocked subprocess returns those KVs. A future refactor that prints `proc.stdout` would break Step 0b orchestrator parsing under quiet mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-launcher-cutover-output.txt: Add a `capsys` test where `fake_init` returns `INIT_STATUS=ok\nRENAMED=false\n` on stdout and assert `step0_init_main` success leaves `captured.out` free of `INIT_STATUS=` / `RENAMED=`.


### FINDING_14: Missing `step1d5` entry/complete sentinel and pause-order tests
- **Reviewer(s)**: dyn-retirement-coverage-output.txt
- **Severity**: important
- **Concern**: Retired `design-step1d5.sh` entry/complete modes write `.completed/step-1c`, `.completed/step-1d`, and `.completed/step-1d.5` before pause-save (`python/design_lifecycle.py:1364-1398`), but pytest only covers `--mode collect`. There are no tests asserting entry/complete sentinel creation or pause ordering for those modes, so regressions in the folded Step 1d.5 prelude/completion boundaries would not be caught by `make test-design-step1d5`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retirement-coverage-output.txt: Add `test_step1d5_entry_writes_sentinels_before_pause` and `test_step1d5_complete_writes_step_1d5_before_pause` mirroring the existing `test_step0_ap_continue_writes_sentinels_before_pause` pattern.


### FINDING_15: No structural or relevant-check gate for `_DESIGN_LIFECYCLE_STDOUT_KEYS`
- **Reviewer(s)**: dyn-retirement-coverage-output.txt
- **Severity**: important
- **Concern**: Structural retirement pins verify `_REGISTRY` membership for the 11 verbs but not `_DESIGN_LIFECYCLE_STDOUT_KEYS` membership, which the plan acceptance criteria explicitly required. Quiet-mode suppression is only checked in `python/test_cli.py:161-164`, and that test is not in the `python/design_lifecycle.py` relevant-check target set (`python/checks.py:459`). A verb could remain registered while dropping out of `_DESIGN_LIFECYCLE_STDOUT_KEYS` without failing structural or relevant-check gates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retirement-coverage-output.txt: Add `contains "$CLI_PY" '_DESIGN_LIFECYCLE_STDOUT_KEYS'` checks for each ported verb in `scripts/test-design-structure.sh`, or include `py-test` / a focused cli selector in the `design_lifecycle.py` relevant-check rule.
### FINDING_4: Non-zero degraded-tools-gate exit treated as Step 0 success
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-generic-output.txt
- **Severity**: important
- **Concern**: `step0_session_main` treats a non-zero `agent degraded-tools-gate` exit as success and can emit `STEP0_STATUS=ok` from empty stdout. Empty degraded-tools-gate stdout with non-zero subprocess rc yields `STEP0_STATUS=ok` and session exit 0. A gate crash or argparse failure can be treated as healthy Step 0, skipping the degraded-tools operator prompt that the bash wrapper previously failed closed on.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: If gate.returncode != 0 or stdout lacks DEGRADED=, emit needs-degraded-decision or fail closed instead of ok.
  - From codex-generic-output.txt: Log the gate failure, then return non-zero before emitting a success status.


### FINDING_6: Narrow `test-design-step0-init` pytest `-k` filter omits ported contracts
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-retirement-coverage-output.txt
- **Severity**: important
- **Concern**: `make test-design-step0-init` `-k` filter omits ported contracts still living in `python/test_design_lifecycle.py`. At minimum, `test_resolve_repo_parses_ssh_url_remote` and `test_design_route_merges_flags_for_already_planned` do not match the current filter, so CI/relevant-checks can pass while `resolve_repo` gh-miss/origin-fallback and resumed router-flag merge behavior regress. The repointed target no longer exercises coverage that the deleted `test-design-step0-init.sh` covered indirectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add resolve_repo to the -k filter or rename the test to match an existing token
  - From dyn-retirement-coverage-output.txt: Extend the `-k` expression (for example add `resolve_repo or design_route`) or drop `-k` in favor of a dedicated marker/namespace for Step 0/1 wrapper tests so the Make target matches the old harness breadth.


### FINDING_7: Symlinked session env file yields empty env (blocks real `/design` Step 0)
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: blocking
- **Concern**: `_load_source_env` returns `{}` for symlinked session env files, but `session write-design-env` creates `current-design-env-$PPID.sh` as a symlink and the new launcher passes that symlink to every ported verb (`python/session_env.py:693,716-717,844-853`). In a real `/design`, `design-run-$PPID.sh step0-route` reaches `_require_design_tmpdir` with no `DESIGN_TMPDIR` and aborts before routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Allow the expected current-design-env symlink after validating its path and resolved target, or have the launcher pass the real `source-env.sh` path.


### FINDING_8: `%q` decoder corrupts non-ASCII verbal argv
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: The `%q` decoder at `python/design_lifecycle.py:607-624` does not handle ANSI-C octal escapes, so non-ASCII verbal argv is corrupted after parse persistence. For example, bash writes `café` as `$'caf\303\251'`, and this decoder loads it as `caf303251`, which can produce a wrong `feature-description.txt`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Implement octal, hex, and unicode escape decoding for `$'...'`, or avoid `%q` for Python-read env files with a safe format that round-trips Unicode.


