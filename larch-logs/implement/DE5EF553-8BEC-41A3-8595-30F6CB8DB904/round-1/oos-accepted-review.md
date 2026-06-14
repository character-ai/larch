### OOS_1: risk-integration: python/test_launch_review.py:1-183
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Only nine pytest cases replace the deleted multi-thousand-line shell harness while the plan and acceptance criteria require broad parity coverage. Regressions in preflight exit codes, retry semantics, dirty-tree baseline, or degraded/empty Cursor handling can ship without CI catching them. Implement the plan-listed pytest matrix (or a justified subset with explicit gaps) before calling the migration done.
- **Suggested revision**: Address the concern above.


### OOS_2: risk-integration: python/test_launch_review.py:1-183
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Deleting scripts/test-launch-review.sh left only nine pytest cases while the plan requires broad launcher parity coverage. Regressions in retry loops preflight exit codes dirty-tree baseline handling or Cursor post-processing can ship without failing make test-launch-review or py-test. Port the deleted shell harness section coverage into python/test_launch_review.py per the plan enumerated cases before treating acceptance as met.
- **Suggested revision**: Address the concern above.


### OOS_3: correctness: python/test_launch_review.py:1-183
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Pytest coverage is far smaller than the plan/acceptance matrix after deleting scripts/test-launch-review.sh. Retry loops, preflight exit codes, CURSOR_DEGRADED gating, and dirty-tree edge cases can regress without CI signal. Add plan-enumerated pytest cases for preflight bundles, retries, postprocess, logging, and dirty-tree semantics.
- **Suggested revision**: Address the concern above.


### OOS_4: **correctness** `python/test_launch_review.py:1-183` — Pytest coverage is far thinner than the plan’s parity matrix and the deleted `scripts/test-launch-review.sh` harness. Present tests cover parser basics, sentinel replay, env cap hit, session-id precedence, and two stub-launch happy paths. They do not exercise auth/model preflight bundles, transient/auth retry locking, empty-result retry, terminal ordering, launch-failure logging to design vs implement logs, or the Cursor empty-result diag/redaction paths above. Regressions in those areas can ship despite green `py-test`. **Suggested fix:** Add focused tests for the missing matrix items from the plan, especially Cursor empty-result diag content/redaction, Cursor success sidecar marker presence, and collector retry argv shape.
- **Reviewer**: dyn-launcher-parity-output.txt
- **Concern**: - **correctness** `python/test_launch_review.py:1-183` — Pytest coverage is far thinner than the plan’s parity matrix and the deleted `scripts/test-launch-review.sh` harness. Present tests cover parser basics, sentinel replay, env cap hit, session-id precedence, and two stub-launch happy paths. They do not exercise auth/model preflight bundles, transient/auth retry locking, empty-result retry, terminal ordering, launch-failure logging to design vs implement logs, or the Cursor empty-result diag/redaction paths above. Regressions in those areas can ship despite green `py-test`. **Suggested fix:** Add focused tests for the missing matrix items from the plan, especially Cursor empty-result diag content/redaction, Cursor success sidecar marker presence, and collector retry argv shape.
- **Suggested revision**: Address the concern above.


### OOS_5: [OUT_OF_SCOPE] Collector review retries still omit `--timing-task-kind` (`scripts/collect-agent-results.sh:760-766`), so retries record timing under the generic `{tool}-review` default. The pre-cutover shell path had the same omission, so this is a pre-existing gap rather than a regression introduced by the Python port.
- **Reviewer**: dyn-launcher-parity-output.txt
- **Concern**: - Collector review retries still omit `--timing-task-kind` (`scripts/collect-agent-results.sh:760-766`), so retries record timing under the generic `{tool}-review` default. The pre-cutover shell path had the same omission, so this is a pre-existing gap rather than a regression introduced by the Python port.
- **Suggested revision**: Address the concern above.


### OOS_6: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-retry-cutover-output.txt
- **Concern**: - **risk-integration** `scripts/collect-agent-results.sh:551-560` — `validate_retry_stderr_sink_or_mark` only rejects `..` in `STDERR_SINK`; it does not apply the safe meta-path predicate used by `python/cli.py agent launch-review`. Tampered retry metadata could point stderr capture outside the session tmpdir. This predates the Python port but still affects replay security.
- **Suggested revision**: Address the concern above.


