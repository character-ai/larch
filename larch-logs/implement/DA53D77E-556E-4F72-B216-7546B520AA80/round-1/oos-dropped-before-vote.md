### OOS_1: [OUT_OF_SCOPE] Execution issue artifact precedence
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: When both execution-issues artifacts exist, the run-dir NDJSON can override the tmpdir markdown path and drop newer or richer tmpdir entries from the final summary counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Matrix heading assertion can miss the H2 line
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, codex-specialist-testing
- **Severity**: important
- **Concern**: The matrix check only matches `: <expected>`, so the Outcome bullet can satisfy it even if the `## /implement run ...` heading regresses. The run-summary title contract should be verified directly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Assert a line-anchored H2 pattern such as ^## /implement run .+: <expected> when expect_outcome=present
  - From codex-specialist-testing: assert the full heading string or anchor the match to the H2 line in both stdout and file assertions

### OOS_3: [OUT_OF_SCOPE] SECURITY.md marker example mismatch
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: SECURITY.md still documents the em-dash PEM truncation marker while the redaction helper emits the colon form, so the documented example no longer matches the emitted marker text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Step 0 timing labels still use em dashes
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The live Step 0 timing labels still pass through the em-dash form as wire labels. The reviewer treats that as intentional passthrough and deferred work rather than a missed production fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] PR-body redaction tests still use em-dash markers
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The PR-body redaction test mocks still encode the em-dash truncation marker, so the test suite continues to model the older punctuation even though the production helpers were out of scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] Write-final-report harness is not in CI
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: The bash write-final-report harness is not exercised by the reported make target, so this check remains implement-local while CI only covers pytest.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Wire bash skills/implement/scripts/test-write-final-report.sh into a Makefile/CI harness target or document it as manual-only

### OOS_7: [OUT_OF_SCOPE] PR-body truncation markers still use em dashes
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The PR-body truncation markers remain on the em-dash form in the redaction helper, leaving a rare redaction path with non-compliant punctuation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Track as separate readability sweep if desired

