# Review Round 1

- Mode: `diff`
- 10 accepted, 3 rejected (2 neutral)

## Accepted Findings

### FINDING_1: Missing plan-required Step 0/1 wrapper pytest coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-lifecycle-parity-output.txt, dyn-launcher-cutover-output.txt, dyn-retirement-coverage-output.txt
- **Severity**: important
- **Concern**: Deleted Step 0/1 shell harness coverage was not ported to pytest. Replacement tests cover only a small subset (parse cache, template literal, step0c pause ordering with mocked pause-save, step1e sentinel cleanup). Plan-required behavioral cases are largely absent: step0-session parse-KV ordering and degraded-tools BOTH_DOWN_SEEN/STEP0_STATUS, step0-route cancel-pause-load abort and flag forwarding, step0-init route-result gating and stdout capture, clarify-hard-halt argv forwarding, step1d5 collect idempotency/dirty-tree/launch-failure paths, pause-save terminal semantics without mocking, route/init stderr relay, and verbal metacharacter round-trip. Regressions can merge while `make test-design-step0-init` / `make test-design-step1d5` stay green because those targets run the whole module without exercising the missing contracts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port deleted harness scenarios into pytest with monkeypatched subprocess/gh stubs per the plan test list.
  - From codex-specialist-correctness-output.txt: Add the specified monkeypatched tests for the Step 0/1 wrapper contracts without requiring real gh or network.
  - From cursor-specialist-edge-cases-output.txt: Add plan-listed pytest cases with monkeypatched subprocess/gh for step0-session, step0-route, step0-init, step1d5 collect, clarify-hard-halt, and pause terminal semantics before merge.
  - From cursor-specialist-testing-output.txt: Add monkeypatched subprocess tests per the plan acceptance list: session parse-KV ordering and BOTH_DOWN_SEEN cases, route cancel-pause-load no ROUTE= stdout, init route-result gating without INIT_STATUS= leak, clarify-hard-halt argv forwarding, step1d5 collect pause and launch-failure sentinel idempotency, pause-save terminal semantics on each verb.
  - From codex-specialist-testing-output.txt: Port the required shell harness cases into pytest, especially real pause-save argv, route/init title preservation, degraded-gate relay, and collect idempotency.
  - From dyn-lifecycle-parity-output.txt: add the plan's monkeypatched subprocess tests before merge; pin the stderr-relay and `%q` round-trip cases first.
  - From dyn-launcher-cutover-output.txt: Add the plan's pytest cases (especially pause-save terminal semantics without mocking, route `cancel-pause-load`, and session degraded-gate relay) so `make test-design-step0-init` / `make test-design-step1d5` exercise contracts, not just file presence.
  - From dyn-retirement-coverage-output.txt: Port the deleted harness cases into `python/test_design_lifecycle.py` with monkeypatched subprocess stubs, and wire Makefile targets to scoped selectors (for example `pytest python/test_design_lifecycle.py -k 'step0_init or step1d5_collect'`) so `make test-design-step0-init` and `make test-design-step1d5` actually run the intended subsets.


### FINDING_10: PUBLIC_ARGV_WORDS substring false positive in verbal POSITIONAL_VALUE
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-lifecycle-parity-output.txt
- **Severity**: important
- **Concern**: `_validate_parse_result` treats `PUBLIC_ARGV_WORDS` appearing anywhere in `POSITIONAL_VALUE` as an unexpanded template literal, not just in parse stderr. A legitimate verbal feature description containing that substring aborts Step 0 despite valid argv expansion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Restrict the check to stderr_text and/or explicit unexpanded template tokens only.
  - From dyn-lifecycle-parity-output.txt: restrict the check to stderr and/or an explicit sentinel argv token (e.g. `${PUBLIC_ARGV_WORDS}`), not substring search in verbal text.


### FINDING_11: check_pause_and_exit passes CLI domain/verb tokens to pause_save_main
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-launcher-cutover-output.txt
- **Severity**: important
- **Concern**: `_pause_args` / `check_pause_and_exit` includes the CLI domain and verb when calling `pause_save_main` in-process. `pause_save_main` / `_parse_args` only accept `--design-tmpdir`, `--issue`, and optional `--repo`. On `.pause-requested`, `_parse_args` returns `None`, `pause_save_main` prints Usage and returns 1, and pause state is never saved. Every ported Step 0/1 verb using this helper at bash pause boundaries is affected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Pass only pause-save option argv to pause_save_main, or invoke the full CLI via subprocess.
  - From codex-specialist-testing-output.txt: Remove the leading design and pause-save tokens for in-process calls, or invoke the CLI subprocess; add a non-monkeypatched pause test.
  - From dyn-launcher-cutover-output.txt: Drop the `"design"` / `"pause-save"` prefix from `_pause_args` (or call `pause_save_main` with only the flag tail), add an integration test that does not monkeypatch `pause_save_main` and asserts `PAUSE_OK=true` / marker write on real argv, and mirror bash `exec` semantics: no post-pause stdout beyond pause-save KVs.


### FINDING_12: Post-session verbs treat missing DESIGN_TMPDIR as current directory
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Post-session verbs treat missing `DESIGN_TMPDIR` as the current directory. A stale or missing session env can create or delete `.completed` files under the repository while returning success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Require a non-empty absolute existing design tmpdir before pause checks or filesystem mutations.


### FINDING_14: clarify-hard-halt relevant-check mapping removed without replacement
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-launcher-cutover-output.txt, dyn-retirement-coverage-output.txt
- **Severity**: important
- **Concern**: The `_DIRECT_TARGET_RULES` row for retired `design-step0-clarify-hard-halt.sh` was removed without a replacement keyed on `python/design_lifecycle.py` / `step0_clarify_hard_halt_main`. Edits confined to the ported clarify-hard-halt verb may no longer pull `test-design-stage-terminal-state` and `test-design-failure-report` through relevant-checks, even though `design_lifecycle.py` still shells out to `design-stage-terminal-state.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add test_step0_clarify_hard_halt_* pytest cases and wire design_lifecycle clarify-hard-halt edits to that selector in checks.py.
  - From dyn-launcher-cutover-output.txt: Add a `python/design_lifecycle.py` rule (or narrow `-k` selector) that still runs `test-design-stage-terminal-state` and `test-design-failure-report` when clarify-hard-halt / terminal-state glue changes.
  - From dyn-retirement-coverage-output.txt: Add a `_DIRECT_TARGET_RULES` entry for `python/design_lifecycle.py` (or a narrow path pin) that maps clarify-hard-halt edits to `test-design-stage-terminal-state`, `test-design-failure-report`, and the new pytest cases once they exist.


### FINDING_16: step0_route_main swallows design route stderr on failure
- **Reviewer(s)**: dyn-lifecycle-parity-output.txt
- **Severity**: important
- **Concern**: `step0_route_main` runs `design route` with `capture_output=True` and never relays `proc.stderr` on failure. Bash redirected only stdout to a capture file and left stderr on the terminal. stderr-only diagnostics (e.g. `issue-body-file must be a readable regular file`, configuration errors) are hidden; the wrapper emits a generic Step 0b abort line instead.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-lifecycle-parity-output.txt: mirror session setup: use `stderr=subprocess.STDOUT` or print `proc.stderr` to stderr before returning on non-zero exit.


### FINDING_17: step0_init_main swallows init-runparams subprocess stderr on failure
- **Reviewer(s)**: dyn-lifecycle-parity-output.txt
- **Severity**: important
- **Concern**: Same stderr swallowing in `step0_init_main` for the captured `design init-runparams` subprocess. Init failure paths lose stderr-only operator text that bash surfaced live.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-lifecycle-parity-output.txt: relay combined or stderr output on non-zero exit before the generic abort messages.


### FINDING_3: bash printf %q encode/decode round-trip is incorrect
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-lifecycle-parity-output.txt
- **Severity**: important
- **Concern**: Custom `_bash_percent_q` plus `shlex` decode does not reproduce bash `printf '%s=%q\n'` semantics. Newlines are emitted as inline `$'\n'` tokens that `shlex.split` cannot decode; other metacharacters use ad hoc escaping. Verbal `POSITIONAL_VALUE` strings with spaces, quotes, `$`, or newlines can round-trip incorrectly through `.design-step0-parsed.env`, breaking Step 0b issue binding and feature-description materialization in step0-route/step0-init.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add metacharacter round-trip tests; match bash printf %q semantics for writes.
  - From cursor-specialist-edge-cases-output.txt: Use a bash-%q-compatible decoder (or printf-based round-trip) and add metacharacter/newline round-trip tests.
  - From dyn-lifecycle-parity-output.txt: generate cache files with a real shell `printf '%q'` subprocess (or a tested `%q` encoder), and add round-trip tests for spaces, quotes, `$`, and newlines.


### FINDING_6: step0_init_main truncates multi-word ISSUE_TITLE from route-state env
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `step0_init_main` loads raw route-state env with the shell/%q decoder. A multi-word `ISSUE_TITLE` from `.design-step0-route-state.env` (e.g. `Add retry support`) is parsed as `Add`, so `feature-description.txt` loses most of the title.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Load route-state with an allowlisted raw KV reader such as phase_driver_read_result_env, or otherwise keep raw route-state compatibility while avoiding shell decoding.
  - From codex-specialist-edge-cases-output.txt: Load route-state with phase_driver_read_result_env or a raw result-env loader that preserves spaces.
  - From codex-specialist-testing-output.txt: Read route-state with raw RHS read-result-env semantics, or write route-state quoted; add a spaced-title route/init test.


### FINDING_7: Route result WARN/ERROR breadcrumbs suppressed on abort
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_read_result_pairs` / route wrapper logic suppresses WARN and ERROR breadcrumbs from route results. A corrupt pause block can produce `ROUTE=cancel-pause-load` plus ERROR breadcrumbs, but the wrapper exits with only a generic message that refers to missing breadcrumbs, hiding pause-load diagnostics the operator needs to repair resume state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Replay WARN and ERROR from the selected route result source in the route wrapper before aborting, without replaying ROUTE or init-runparams KVs.
  - From codex-specialist-edge-cases-output.txt: Replay WARN and ERROR lines from the selected route result source before aborting cancel-pause-load.


