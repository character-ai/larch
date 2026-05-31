# Review Round 2

- Mode: `diff`
- 7 accepted, 11 rejected (11 exonerated)

## Accepted Findings

### FINDING_10: test gap: ship-pr `_surface_lint_fix_stderr_tail` CODER_LOG_FILE fallback
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `CODER_LOG_FILE` fallback in `_surface_lint_fix_stderr_tail` is untested. Older lint-fix-loop output without `STDERR_TAIL_PATH` would not surface tails to chat if fallback parsing regressed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Stub lint-fix stdout with only `CODER_LOG_FILE=` and seeded `${stem}.stderr-tail`; assert caller stderr via `run_lint_fix_loop_capture`.


### FINDING_11: test gap: Step 5 `step5_surface_lint_stderr_tail` CODER_LOG_FILE fallback
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `step5_surface_lint_stderr_tail` `CODER_LOG_FILE` fallback untested. Step 5 terminal arms could lose backward-compatible surfacing when only `CODER_LOG_FILE` is present in capture file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add parsers case with `CODER_LOG_FILE` only and assert `step5_surface_lint_stderr_tail` emits seeded tail.


### FINDING_13: test gap: recovery waterfall surfacing when only `${output}.stderr-tail` exists
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Recovery waterfall test does not isolate surfacing when only `${output}.stderr-tail` exists. CI launcher exit 0 with `LAUNCHER_EXIT=0` but non-empty tail could fail to surface if gating regresses to `launcher_exit` only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Stub launcher exit 0 with `LAUNCHER_EXIT=0` and non-empty `${output}.stderr-tail`; assert caller stderr probe.


### FINDING_23: Step 5: whitespace word-splitting truncates path-valued KV tails
- **Reviewer(s)**: dyn-kv-parse-robustness-output.txt
- **Severity**: important
- **Concern**: `step5_parse_kv_tokens` splits capture lines with `for tok in $line`, truncating `STDERR_TAIL_PATH` / `CODER_LOG_FILE` values at the first space. Step 5 can miss valid `${stem}.stderr-tail` files that `run_lint_fix_loop_capture` / ship-pr (`substr` after `=`) would surface for the same stdout block. `emit_kv` allows spaces in values (`scripts/lib-quiet.sh:166-178`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-kv-parse-robustness-output.txt: Parse path-valued keys from the full line, not whitespace tokens — e.g. `case "$line" in STDERR_TAIL_PATH=*) stem="${line#STDERR_TAIL_PATH=}" ;; esac`, or the same `awk '$1 == key { print substr($0, index($0,"=")+1); exit }'` pattern used by `scripts/ship-pr.sh:570-572` / `scripts/test-lint-fix-loop.sh:25-27`. Add a harness case with a space (and optionally `=`) in `STDERR_TAIL_PATH`.


### FINDING_6: plan-review-loop: `collect` subshell `|| true` swallows collector failure
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Collector invocation uses `|| true`, so non-zero collect exit no longer aborts the loop under `set -e`. When `collect-agent-results.sh` exits non-zero (including exit 1 with empty stdout for bad args/paths), the loop continues, parses no or partial records, and may take a degraded/zero-findings path instead of failing closed—exceeding Decision 7’s authorized minimal tee-only change and altering panel-failed handling beyond stderr surfacing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Restrict `|| true` to cases that need stderr teed without abort; fail closed when collect rc != 0 and `_collect_out` is empty/unparseable.
  - From cursor-specialist-plan-fidelity-output.txt: Remove `|| true` if the FD-2 harness passes without it; if `set -e` must be satisfied, capture collector rc without swallowing failure semantics, and add a harness assertion for the expected loop status on collector failure.


### FINDING_8: test gap: first-fixer-non-health early return without stderr-tail assertion
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No test for stderr-tail surfacing on first-fixer-non-health early return despite plan choke-point requirement. `run_ci_fix_vendor` can return 1 with `BAIL_REASON=first-fixer-non-health` while a tier stderr-tail exists; without a test, a refactor could move or drop `_surface_ci_stderr_tail` before that return and regress Step 8+ chat diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add or extend a #3134-style case: stub first tier non-health failure, seed `${tier_out}.stderr-tail`, assert probe on caller stderr before first-fixer bail.


### FINDING_9: test gap: codex implementer agent-failure lacks redacted bounded tail assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Agent-failure test does not assert redacted bounded tail per plan testing strategy. A multi-kilobyte or secret-bearing stderr sidecar could slip through without line/byte/redaction checks; only content presence is verified (harness could pass with unbounded or unredacted `${TRANSCRIPT}.stderr-tail`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Reuse test-lib-failed-agent-stderr-tail patterns: cap lines via `LARCH_FAILED_AGENT_STDERR_TAIL_LINES` and assert fence plus size bounds on `${TRANSCRIPT}.stderr-tail`.
  - From cursor-specialist-plan-fidelity-output.txt: Assert tail line/byte caps (and optionally redaction) using existing lib harness patterns or seeded sensitive content in `$SIDECAR_LOG`.


