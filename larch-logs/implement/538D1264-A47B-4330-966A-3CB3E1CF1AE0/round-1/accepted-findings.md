### FINDING_1: **Important** `risk-integration` [skills/review/scripts/test-dispatch-panel.sh:192](<OPERATOR_REPO_PATH>/skills/review/scripts/test-dispatch-panel.sh:192): The new harness-path guard suppresses `append_scout_parse_issue` for any `REVIEW_TMPDIR` under `test-dispatch-panel.*`, but the existing core parse-failed test still expects the explicit `$issues_log` to be written. Concrete failing scenario: `make test-dispatch-panel-core` creates `TMP=$(mktemp -d .../test-dispatch-panel.XXXXXX)`, runs the parse-failed case with `--review-tmpdir "$TMP/dynamic-parse-failed"`, `dispatch-panel.sh:298` returns before appending, then `grep -Fq ... "$issues_log"` fails because the log was intentionally not written. Update this case to assert the new suppressed-harness behavior and local diag sidecar, or move any production append assertion to a temp root outside `test-dispatch-panel.*`; do the same for the append-failure/WARN assertion at `skills/review/scripts/test-dispatch-panel.sh:199-209`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` [skills/review/scripts/test-dispatch-panel.sh:192](<OPERATOR_REPO_PATH>/skills/review/scripts/test-dispatch-panel.sh:192): The new harness-path guard suppresses `append_scout_parse_issue` for any `REVIEW_TMPDIR` under `test-dispatch-panel.*`, but the existing core parse-failed test still expects the explicit `$issues_log` to be written. Concrete failing scenario: `make test-dispatch-panel-core` creates `TMP=$(mktemp -d .../test-dispatch-panel.XXXXXX)`, runs the parse-failed case with `--review-tmpdir "$TMP/dynamic-parse-failed"`, `dispatch-panel.sh:298` returns before appending, then `grep -Fq ... "$issues_log"` fails because the log was intentionally not written. Update this case to assert the new suppressed-harness behavior and local diag sidecar, or move any production append assertion to a temp root outside `test-dispatch-panel.*`; do the same for the append-failure/WARN assertion at `skills/review/scripts/test-dispatch-panel.sh:199-209`.
- **Suggested revision**: Address the concern above.


### FINDING_13: correctness: skills/review/scripts/dispatch-panel.sh:279-282
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Suppression OR-tests SCOUT_MANIFEST path against harness globs; SCOUT_MANIFEST can be set from scout SCOUT_OUTPUT stdout, not only the round file under REVIEW_TMPDIR. A parse-failed round with production REVIEW_TMPDIR but SCOUT_MANIFEST path containing /test-scout-... (or other matched segment) never appends the Warnings entry to the real execution-issues log. Suppress only when REVIEW_TMPDIR matches harness (or require manifest path prefix REVIEW_TMPDIR before applying harness glob).
- **Suggested revision**: Address the concern above.


### FINDING_20: risk-integration: skills/review/scripts/test-dispatch-panel.sh:486-566;Makefile:490-497
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] New scout-parse regressions are unconditional so each sharded harness target runs them once. Redundant CI time (same three tests on core, reuse, limits shards) without additional branch coverage. Shard into one Makefile target/section or accept and document intentional triple smoke.
- **Suggested revision**: Address the concern above.


### FINDING_21: security: skills/review/scripts/dispatch-panel.sh:279-300
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] OR-ing is_harness_scout_path(REVIEW_TMPDIR) with is_harness_scout_path(SCOUT_MANIFEST) lets a manifest path alone suppress append_scout_parse_issue. SCOUT_MANIFEST can be stale or attacker-influenced via round status sidecar; a path containing /test-scout-* (or other globs) triggers parse-failed append suppression even when REVIEW_TMPDIR is a normal prod-shape dir, so LARCH_EXECUTION_ISSUES_LOG may miss scout parse-failed warnings. Suppress only on REVIEW_TMPDIR and/or explicit harness env; do not treat SCOUT_MANIFEST as a harness signal.
- **Suggested revision**: Address the concern above.


