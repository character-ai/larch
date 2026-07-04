### OOS_1: [OUT_OF_SCOPE] ci_monitor pointer still emits em dash
- **Reviewer(s)**: cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-report-format
- **Severity**: important
- **Concern**: The live /implement CI log pointer still uses the old em-dash form in collect_failed_logs(), so operators can see two different pointer formats for the same diagnostic and the live CI path still violates the readability rule this change is meant to enforce.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Mirror the gh.py colon separator in collect_failed_logs or deduplicate through one shared pointer helper
  - From codex-specialist-edge-cases: Update the banner separator to colon/comma punctuation; this file was untouched by the diff.
  - From cursor-specialist-testing: Track as follow-up or extend sweep to implement/ci_monitor.py in a separate change.
  - From codex-specialist-testing: If the broader scrub should include implement/ci_monitor.py, update it in a separate follow-up
  - From dyn-dyn-report-format: Change the `ci_monitor.py` pointer to the same colon wording as `gh.py`, or route `collect_failed_logs()` through the shared `gh` helper so the string has a single source of truth.

### OOS_2: [OUT_OF_SCOPE] live progress passthrough still uses em dashes
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The live progress passthrough still emits timing-ledger em-dashes, so user-visible run output can violate readability style during runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Accept as wire-label passthrough per plan, or extend scrub to timing mark emission in a follow-up

### OOS_3: [OUT_OF_SCOPE] PR-body redaction truncation markers still use em dashes
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The PR-body redaction truncation markers still contain em dashes, so rare redaction paths can still show non-compliant punctuation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Fix in a separate readability sweep of pr_body redaction helpers.

### OOS_4: [OUT_OF_SCOPE] bootstrap append-failure fallback still uses em dash
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: latent
- **Concern**: The append-failure fallback bullet still emits an em dash, so bootstrap-generated execution-issues entries remain non-compliant.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Fix it separately if you want the em-dash ban enforced across bootstrap-generated execution-issues entries

### OOS_5: [OUT_OF_SCOPE] write-final-report harness is out of sync with the new heading contract
- **Reviewer(s)**: dyn-dyn-report-format
- **Severity**: important
- **Concern**: The offline write-final-report harness still asserts em-dash run-summary headings, matrix outcomes, and top-reviewer lines even though the renderer now emits colon separators, so direct bash-harness runs can false-fail against the new contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-report-format: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] run-summary heading docs still show the old em dash
- **Reviewer(s)**: dyn-dyn-report-format
- **Severity**: latent
- **Concern**: The documented run-summary heading contract still shows `## /<skill> run <run-id> — <outcome>`, which no longer matches the colon format emitted by the renderers and can mislead implement tooling and reviewers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-report-format: Address the concern above.

### OOS_7: [OUT_OF_SCOPE] final_report stalled-heading parser is fragile
- **Reviewer(s)**: dyn-dyn-report-format
- **Severity**: latent
- **Concern**: `_summary_stalled_heading_index()` and `summary_heading_is_stalled()` only inspect the first non-empty line of `final-summary.md`, so the parser is brittle if any writer ever prepends content above the H2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-report-format: Address the concern above.

