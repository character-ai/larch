### FINDING_1: **code-quality** `scripts/test-gh-run-logs.sh:73-78` — The `run_script` helper is defined but never invoked; tests duplicate the same `PATH=… gh-run-logs.sh … || rc=$?` pattern inline, so the helper is dead code on the branch. **Suggested fix:** Remove `run_script` or refactor the four tests to call it so the harness stays minimal and easier to maintain.
- **Reviewer**: dyn-caller-integration-output.txt
- **Concern**: - **code-quality** `scripts/test-gh-run-logs.sh:73-78` — The `run_script` helper is defined but never invoked; tests duplicate the same `PATH=… gh-run-logs.sh … || rc=$?` pattern inline, so the helper is dead code on the branch. **Suggested fix:** Remove `run_script` or refactor the four tests to call it so the harness stays minimal and easier to maintain.
- **Suggested revision**: Address the concern above.

### FINDING_2: **correctness** `scripts/gh-run-logs.sh:43-49` — Capturing all of `gh run view … --log-failed` with `raw=$(… 2>&1)` materializes the **entire** transcript as one bash string before `tail -100`, so peak memory stays proportional to the full log for the rest of the script. The old `gh … | tail -100` pipeline still had `tail` read to EOF, but it never forced bash to hold the whole transcript in a single expandable variable while re-printing it; on very large Actions logs this change can **amplify memory pressure, slow the step sharply, or hit practical size limits** compared to streaming to `tail` from a file or FIFO. **Suggested fix:** keep the stderr/stdout merge and sentinel detection, but avoid storing the full log in `$raw`—for example write `gh` output to a `mktemp` file (or a `> >( … )` process substitution that only buffers enough to detect the sentinel), `grep -q` on that file, then `tail -100` the same file, unlinking afterward; alternatively probe with a bounded read for the in-progress message before fetching logs.
- **Reviewer**: dyn-shell-capture-safety-output.txt
- **Concern**: - **correctness** `scripts/gh-run-logs.sh:43-49` — Capturing all of `gh run view … --log-failed` with `raw=$(… 2>&1)` materializes the **entire** transcript as one bash string before `tail -100`, so peak memory stays proportional to the full log for the rest of the script. The old `gh … | tail -100` pipeline still had `tail` read to EOF, but it never forced bash to hold the whole transcript in a single expandable variable while re-printing it; on very large Actions logs this change can **amplify memory pressure, slow the step sharply, or hit practical size limits** compared to streaming to `tail` from a file or FIFO. **Suggested fix:** keep the stderr/stdout merge and sentinel detection, but avoid storing the full log in `$raw`—for example write `gh` output to a `mktemp` file (or a `> >( … )` process substitution that only buffers enough to detect the sentinel), `grep -q` on that file, then `tail -100` the same file, unlinking afterward; alternatively probe with a bounded read for the in-progress message before fetching logs.
- **Suggested revision**: Address the concern above.

### FINDING_3: **correctness** `scripts/gh-run-logs.sh:44-50` — On non-matching failures the script ends with `exit "$gh_rc"`, so **any** non-zero `gh` status—including a hypothetical or future **`gh` exit 2** unrelated to the in-progress string—is forwarded unchanged; `scripts/ship-pr.sh` at line 1197 exempts **all** `rc=2` from `record_failure`, not only the sentinel-driven branch, so a real `gh` failure that happens to use status 2 would be misclassified as the benign “still in progress” case and **silently skip** CI Issues logging. **Suggested fix:** reserve a wrapper-specific exit code for the in-progress case (for example 3) that `gh` never emits, return that only when the sentinel matches, map every other `gh` failure (including `gh_rc=2` without the sentinel) to exit 1, and narrow `ship-pr.sh` to exempt only that dedicated code.
- **Reviewer**: dyn-shell-capture-safety-output.txt
- **Concern**: - **correctness** `scripts/gh-run-logs.sh:44-50` — On non-matching failures the script ends with `exit "$gh_rc"`, so **any** non-zero `gh` status—including a hypothetical or future **`gh` exit 2** unrelated to the in-progress string—is forwarded unchanged; `scripts/ship-pr.sh` at line 1197 exempts **all** `rc=2` from `record_failure`, not only the sentinel-driven branch, so a real `gh` failure that happens to use status 2 would be misclassified as the benign “still in progress” case and **silently skip** CI Issues logging. **Suggested fix:** reserve a wrapper-specific exit code for the in-progress case (for example 3) that `gh` never emits, return that only when the sentinel matches, map every other `gh` failure (including `gh_rc=2` without the sentinel) to exit 1, and narrow `ship-pr.sh` to exempt only that dedicated code.
- **Suggested revision**: Address the concern above.

### FINDING_4: **risk-integration** `scripts/gh-run-logs.sh:49-50` — **Important**: the wrapper reserves exit `2` for the in-progress sentinel, but it also preserves unrelated raw `gh` exit code `2` via `exit "$gh_rc"`. `gh help exit-codes` says `2` is used when a running command is cancelled, so a cancelled/non-progress `gh run view` can return `2`; `scripts/ship-pr.sh:1197` will then treat it as non-failure and suppress the real `CI Issues` entry. **Suggested fix:** normalize every non-progress `gh` failure to `1` before returning, or have `ship-pr.sh` suppress only a verified in-progress sentinel rather than every rc `2`; add a regression test where the stub exits `2` with a non-matching message and assert it is recorded/returned as failure.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: - **risk-integration** `scripts/gh-run-logs.sh:49-50` — **Important**: the wrapper reserves exit `2` for the in-progress sentinel, but it also preserves unrelated raw `gh` exit code `2` via `exit "$gh_rc"`. `gh help exit-codes` says `2` is used when a running command is cancelled, so a cancelled/non-progress `gh run view` can return `2`; `scripts/ship-pr.sh:1197` will then treat it as non-failure and suppress the real `CI Issues` entry. **Suggested fix:** normalize every non-progress `gh` failure to `1` before returning, or have `ship-pr.sh` suppress only a verified in-progress sentinel rather than every rc `2`; add a regression test where the stub exits `2` with a non-matching message and assert it is recorded/returned as failure.
- **Suggested revision**: Address the concern above.

### FINDING_5: **risk-integration** `scripts/ship-pr.sh:1195-1197` and `scripts/gh-run-logs.sh:231-238` — `ship-pr.sh` skips `record_failure` for any `gh-run-logs.sh` exit code `2`, but `gh-run-logs.sh` ends with `exit "$gh_rc"` after the in-progress branch, so a non–in-progress failure where `gh` returns exit `2` (or a future CLI change) would still surface as `2` from the wrapper and would now be treated as a benign transient the same as the intentional in-progress sentinel, whereas previously any non-zero (including `2`) was recorded under “CI Issues.” **Suggested fix:** Use a dedicated sentinel exit code that `gh` will not reuse (for example `3` only from the in-progress branch and never from `exit "$gh_rc"`), or keep exit `2` only for that branch and map every other non-zero `gh_rc` to `1` before returning, and align `ship-pr.sh` with that contract.
- **Reviewer**: dyn-caller-integration-output.txt
- **Concern**: - **risk-integration** `scripts/ship-pr.sh:1195-1197` and `scripts/gh-run-logs.sh:231-238` — `ship-pr.sh` skips `record_failure` for any `gh-run-logs.sh` exit code `2`, but `gh-run-logs.sh` ends with `exit "$gh_rc"` after the in-progress branch, so a non–in-progress failure where `gh` returns exit `2` (or a future CLI change) would still surface as `2` from the wrapper and would now be treated as a benign transient the same as the intentional in-progress sentinel, whereas previously any non-zero (including `2`) was recorded under “CI Issues.” **Suggested fix:** Use a dedicated sentinel exit code that `gh` will not reuse (for example `3` only from the in-progress branch and never from `exit "$gh_rc"`), or keep exit `2` only for that branch and map every other non-zero `gh_rc` to `1` before returning, and align `ship-pr.sh` with that contract.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Harness and wiring changes in [`Makefile`](Makefile), [`agent-lint.toml`](agent-lint.toml), and [`scripts/test-gh-run-logs.sh`](scripts/test-gh-run-logs.sh) look consistent with repo conventions; Test 4 usefully guards against partial-string false positives for exit 2.
- **Reviewer**: dyn-shell-capture-safety-output.txt
- **Concern**: - Harness and wiring changes in [`Makefile`](Makefile), [`agent-lint.toml`](agent-lint.toml), and [`scripts/test-gh-run-logs.sh`](scripts/test-gh-run-logs.sh) look consistent with repo conventions; Test 4 usefully guards against partial-string false positives for exit 2.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Repository-wide search of `*.sh` shows no other production invocations of `gh-run-logs.sh` besides `scripts/ship-pr.sh:1195`; `scripts/test-ship-pr.sh:146` only includes the name in a helper-stub loop, so there are no additional call sites in this tree that need an `[ "$rc" -eq 2 ]`-style guard for this diff.
- **Reviewer**: dyn-caller-integration-output.txt
- **Concern**: - Repository-wide search of `*.sh` shows no other production invocations of `gh-run-logs.sh` besides `scripts/ship-pr.sh:1195`; `scripts/test-ship-pr.sh:146` only includes the name in a helper-stub loop, so there are no additional call sites in this tree that need an `[ "$rc" -eq 2 ]`-style guard for this diff.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] The new behavior depends on matching a fixed English substring from `gh`; that is an explicit design trade-off in the plan, not a missed caller, but operators should expect silent reversion of the ndjson noise fix if `gh` rephrases that message without updating the grep needle.
- **Reviewer**: dyn-caller-integration-output.txt
- **Concern**: - The new behavior depends on matching a fixed English substring from `gh`; that is an explicit design trade-off in the plan, not a missed caller, but operators should expect silent reversion of the ndjson noise fix if `gh` rephrases that message without updating the grep needle.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] The prior `gh | tail -100` arrangement still drove `gh` to EOF under normal `tail` behavior, so **SIGPIPE-driven early termination of `gh` was not the dominant behavioral difference** here; the main regression risk from this diff is **bash-side buffering**, not loss of backpressure that stopped `gh` mid-flight.
- **Reviewer**: dyn-shell-capture-safety-output.txt
- **Concern**: - The prior `gh | tail -100` arrangement still drove `gh` to EOF under normal `tail` behavior, so **SIGPIPE-driven early termination of `gh` was not the dominant behavioral difference** here; the main regression risk from this diff is **bash-side buffering**, not loss of backpressure that stopped `gh` mid-flight.
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] code-quality: scripts/gh-run-logs.sh:16-19
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Exit-code comment implies non-zero gh maps to exit 1 though script may exit with other preserved gh codes. Minor documentation imprecision for operators reading comments only. Clarify when touching that header for another reason.
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] risk-integration: scripts/ship-pr.sh:1194-1227
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Fix loop runs even when log fetch is degraded Pre-existing behavior for gh failures; not introduced by this branch None required for this review
- **Suggested revision**: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] risk-integration: scripts/ship-pr.sh:1194-1227
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] After rc 2 fix loop still runs with thin diagnostics in fail_file Operator may run vendor retries without real failure logs Pre-existing loop shape; only revisit if product wants early return or backoff on exit 2
- **Suggested revision**: Address the concern above.

### FINDING_13: architecture: scripts/gh-run-logs.sh:44
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Entire gh output captured into bash variable before tail Extremely large transcripts could increase memory vs a pipe Stream with tail cap or tempfile if operational limits matter
- **Suggested revision**: Address the concern above.

### FINDING_14: code-quality: scripts/gh-run-logs.sh:16-18
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Header exit-code summary omits that non-zero gh can yield exit 2. Readers relying on the file header get a misleading contract vs lines 23-24/45-47. Update the header lines to match the implemented exit-code table.
- **Suggested revision**: Address the concern above.

### FINDING_15: code-quality: scripts/test-gh-run-logs.sh:41-48
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] assert_not_contains is defined but unused. Dead code adds noise when reading the harness. Remove or use it in a meaningful assertion.
- **Suggested revision**: Address the concern above.

### FINDING_16: code-quality: scripts/test-gh-run-logs.sh:41-77
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Unused helper functions assert_not_contains and run_script in the new harness. Maintainers may assume run_script is exercised or copy the pattern forward; dead code slightly obscures what the contract tests actually cover. Remove unused helpers or use run_script in all cases and delete assert_not_contains if still unused.
- **Suggested revision**: Address the concern above.

### FINDING_17: code-quality: scripts/test-gh-run-logs.sh:71-77
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Unused run_script helper None beyond maintainability noise Remove helper or use it from all tests
- **Suggested revision**: Address the concern above.

### FINDING_18: code-quality: scripts/test-gh-run-logs.sh:71-77
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] run_script helper is defined but unused. Dead code and duplicated invocation pattern across tests. Remove or refactor tests to call run_script.
- **Suggested revision**: Address the concern above.

### FINDING_19: code-quality: scripts/test-gh-run-logs.sh:71-77
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Unused run_script helper uses eval on a variable name Dead code invites unsafe copy-paste patterns Remove helper or avoid eval entirely
- **Suggested revision**: Address the concern above.

### FINDING_20: code-quality: scripts/test-gh-run-logs.sh:71-77
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Unused run_script helper; tests duplicate invocation pattern. Dead code and duplicated control flow make future edits error-prone. Remove run_script or use it in all tests.
- **Suggested revision**: Address the concern above.

### FINDING_21: code-quality: scripts/test-gh-run-logs.sh:73-78
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Unused run_script helper Dead code adds noise for future editors. Remove run_script or use it in all four tests.
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: scripts/gh-run-logs.sh:233
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Substring match on gh English text only If GitHub changes the in-progress message, detection fails, gh_rc stays non-zero, exit code stays 1, and record_failure runs again. Widen or version the sentinels when gh output changes; document the coupling or add a small set of alternate phrases with tests.
- **Suggested revision**: Address the concern above.

### FINDING_23: correctness: scripts/gh-run-logs.sh:43-50
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Command substitution buffers full gh output before tail-100 Very large --log-failed streams can greatly increase peak memory and latency vs prior pipe-to-tail; possible OOM or long hangs on huge logs Stream to a temp file or bounded capture for classification; tail from file; avoid storing entire log in one variable
- **Suggested revision**: Address the concern above.

### FINDING_24: correctness: scripts/gh-run-logs.sh:45
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Substring grep classifies any gh error containing the in-progress phrase as exit 2 Real failure output that includes the same sentence fools the detector; record_failure skipped and CI issue suppressed Tighten match (line anchor, run id token, structured gh stderr) before mapping to exit 2
- **Suggested revision**: Address the concern above.

### FINDING_25: correctness: scripts/gh-run-logs.sh:45-47
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Substring match on full captured gh output can classify a genuine gh failure as exit 2. A non-zero gh run where stderr/stdout also contains the in-progress phrase (copied log line, wrapper output, or multi-error blob) skips record_failure in ship-pr and suppresses a CI Issues entry for a real failure. Tighten detection (anchored line / full canonical sentence) and extend the regression harness with a deliberate false-positive fixture.
- **Suggested revision**: Address the concern above.

### FINDING_26: risk-integration: scripts/gh-run-logs.sh:43-47
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Substring match maps any gh non-zero exit with that phrase to exit 2; ship-pr skips record_failure for rc 2 A future or rare gh error that includes the same substring would be misclassified as in-progress and would not be recorded as a CI Issue Tighten detection (line anchor documented by gh) or add secondary signals; extend tests if gh wording branches
- **Suggested revision**: Address the concern above.

### FINDING_27: risk-integration: scripts/gh-run-logs.sh:43-50
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Full-output capture into bash variable before tail can increase peak memory for huge gh transcripts. Very large failed-log responses could stress memory where the old pipeline fed tail directly. If observed, stream to tail while scanning only a bounded prefix/suffix for the sentinel.
- **Suggested revision**: Address the concern above.

### FINDING_28: risk-integration: scripts/gh-run-logs.sh:49-50 scripts/ship-pr.sh:1197
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] gh-run-logs.sh passes through gh exit code via exit "$gh_rc"; ship-pr treats any rc=2 as benign. If gh returns 2 without the in-progress substring, record_failure is skipped and CI Issues / execution-issues.ndjson miss a real failure. Use a dedicated exit code for in-progress, or only skip record_failure when output matches sentinel, or document gh never uses 2 for other errors.
- **Suggested revision**: Address the concern above.

### FINDING_29: risk-integration: scripts/test-ship-pr.sh:146
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No integration test for ship-pr when gh-run-logs exits 2 A mistaken revert of the rc=2 exception at scripts/ship-pr.sh:1197 would again append spurious CI Issues entries while scripts/test-gh-run-logs.sh still passes. Add a test-ship-pr section (or extend an existing section) that stubs gh-run-logs.sh to exit 2 and asserts record_failure is not invoked for that helper.
- **Suggested revision**: Address the concern above.

