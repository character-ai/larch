### FINDING_1: Stale quiet breadcrumb env routing docs remain in Stage 2 surfaces
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Several docs still describe `LARCH_QUIET_BREADCRUMB_FD` or `LARCH_QUIET_BREADCRUMBS` routing even though `lib-quiet` no longer consumes those env vars. This can mislead operators and test authors into relying on dead breadcrumb routing instead of `larch_err` stderr/FD4 behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Dead `ensure_breadcrumb_fd` plumbing remains in review scripts
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `skills/review/scripts/review-core.sh` and `review-and-fix.sh` still allocate/export `LARCH_QUIET_BREADCRUMB_FD` even though no current emit API consumes it, creating misleading no-op routing setup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Retry docs still describe removed `emit_breadcrumb` behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Retry-related documentation still points readers at `emit_breadcrumb` or old quiet-log/stdout routing, while migrated code uses `larch_err` on operator-visible stderr/FD4. This affects bump-version retry docs and collect-agent-results retry visibility docs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_4: Redundant quiet-log publish branch obscures behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/lib-larch-log.sh` has a redundant `quiet_source_ok` wrapper around the quiet-log loop, making the quiet-only publish path harder to read without changing behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Tests still set no-op breadcrumb env vars
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-ship-pr.sh` still sets `LARCH_QUIET_BREADCRUMBS=1` even though `lib-quiet` ignores it, so tests may appear to cover routing behavior for the wrong reason.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Review breadcrumb tests still capture stdout only
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `skills/review/scripts/test-review-core.sh` and `test-dispatch-panel.sh` grep stdout for breadcrumb text after the scripts migrated breadcrumb output to `larch_err` on stderr/FD4, causing CI failures or missed assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_7: Migrated `larch_err` diagnostics no longer enter quiet-log breadcrumb artifacts
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Breadcrumb/progress diagnostics now emitted through `larch_err` go to FD4/stderr rather than quiet logs, so committed breadcrumb artifacts can lose ship-pr, ci-wait, or review-and-fix progress lines formerly available for forensic review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: Compressed shell branch reduces maintainability
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `scripts/lib-voter-parse-rate.sh` has a merged `} else` line after migration, making future edits more likely to damage branch structure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Stale `emit_breadcrumb` references remain in later-scope docs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Later-scope docs such as `AGENTS.md` still mention `emit_breadcrumb`, which may confuse contributors until the planned Piece 3 doc sweep.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_10: CI wait inline newline semantics are under-tested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-ci-wait.sh` only substring-matches stderr for the inline wait banner, so adding an accidental newline before dot progress would not fail tests even though it would break real inline output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: Collector retry diagnostics lack operator-stderr coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/collect-agent-results.sh` migrated retry diagnostics to `larch_err`, but no harness pins that `ns-retry:` remains visible on operator stderr/FD4 under quiet init.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: Larch-log ndjson regression test no longer targets publish behavior
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-larch-log.sh` has a stale ndjson-named test that would not catch reintroducing removed ndjson publish behavior because it only checks quiet-log absence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: Review token propagation assertion is comment-only
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `skills/implement/scripts/test-implement-review-token-propagation.sh` only documents the expected assertion in a comment, so drift in the actual `review-and-fix` early-failure path could go unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Unrelated #2667 tests are bundled with Stage 2
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-design-structure.sh` includes unrelated #2667 structural tests on the Stage 2 branch, increasing harness time and review confusion for breadcrumb-focused changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: Breadcrumb source-dir security docs disagree with implementation
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `SECURITY.md` and `docs/run-logs.md` still claim invalid `LARCH_BREADCRUMB_SOURCE_DIR` values fail closed, while Stage 2 code silently skips breadcrumb publishing and returns success. Operators or auditors may expect abort behavior that no longer exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: Ship-pr phase 14 breadcrumb assertions grep the wrong stream
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `scripts/test-ship-pr.sh` phase 14 still greps stdout for aggregator-dispatch breadcrumb text even though `ship-pr.sh` now emits it through `larch_err` to stderr, making the assertions unreliable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: Vestigial breadcrumb stream newline guard remains in ci-wait
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/ci-wait.sh` still has a `LARCH_BREADCRUMB_STREAM` newline guard after stream migration, leaving dead coordination and an extra stderr newline when the stream is unset.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Source-dir session-root derivation can silently skip quiet logs
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/lib-larch-log.sh` derives session root from `dirname(source_dir)`, so a nested or unexpected `LARCH_BREADCRUMB_SOURCE_DIR` hint can skip quiet logs with silent success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] CI wait poll-budget test label is misleading
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-ci-wait.sh` has a poll-budget assertion label that implies stderr migration coverage while the test reads stdout KV, confusing future timeout-test maintenance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_20: Breadcrumb monitor docs still name removed stream writer
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/breadcrumb-monitor.md` still describes `emit_breadcrumb` as the stream writer after Stage 2 removed that API, causing readers to expect removed callsites or stream records from migrated scripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_21: Unrelated #2667 work is bundled into the Stage 2 branch
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: An unrelated #2667 commit and associated docs/test/plugin changes are included with Stage 2 Piece 2, obscuring the focused breadcrumb partition and making independent landing or revert harder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_22: Lib-quiet test docs still describe pre-Stage-2 breadcrumb quieting
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-lib-quiet.md` still summarizes old breadcrumb quieting behavior, misleading contributors about the current API surface after removal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
