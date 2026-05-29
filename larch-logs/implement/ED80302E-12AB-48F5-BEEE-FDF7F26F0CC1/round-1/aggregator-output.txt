### FINDING_1: Breadcrumb tests still grep stdout after larch_err migration
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Postmerge and Phase 1-4 ship-pr harness assertions still inspect stdout for diagnostics now emitted through larch_err on stderr, so tests can fail or miss the migrated output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Implement bootstrap docs still describe removed breadcrumb env gating
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: implement-bootstrap documentation and behavior disagree about LARCH_QUIET_BREADCRUMBS gating: the helper now emits progress unconditionally via larch_err/stderr, while docs and expectations still describe env-gated stdout breadcrumbs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_3: test-ship-pr header still says breadcrumbs are grepped from stdout
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The test-ship-pr header comment still describes stdout-only breadcrumb assertions, which is misleading after the partial stderr retargeting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_4: lib-quiet docs still describe migration-era breadcrumb APIs
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: scripts/lib-quiet.md still implies emit_breadcrumb migration is ongoing and references legacy stdout assertions even though the APIs have been deleted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Breadcrumb publish source_dir contract no longer matches implementation
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: lib-larch-log no longer scans or validates source_dir as the docs/API imply; it effectively anchors publication around the session-root quiet logs, so docs and security expectations around breadcrumbs/ ndjson inputs and source_dir validation are stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_6: ci-wait retains vestigial breadcrumb stream branch
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: ci-wait still branches on LARCH_BREADCRUMB_STREAM for stderr newline formatting even though stream records are no longer emitted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] AGENTS still references removed emit_breadcrumb API
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: AGENTS.md still names emit_breadcrumb even though that API was removed, which can send contributors toward nonexistent helpers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] review-and-fix tests keep dead quiet breadcrumb env
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: review-and-fix tests still set LARCH_QUIET_BREADCRUMBS even though production ignores it, making the test contract harder to understand.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: ship-pr docs still describe removed breadcrumb stream categories
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: scripts/ship-pr.md still describes LARCH_BREADCRUMB_STREAM category vocabulary after Stage 2 removed stream emission from ship-pr.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_10: Negative CI-watch breadcrumb test only checks stdout absence
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The negative CI-watch test can pass while the forbidden diagnostic still appears on stderr, because it only asserts absence from stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: lib-quiet category helper lacks direct retained test coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: larch_quiet_bc_valid_category no longer has direct test coverage after emit API tests were removed, so accidental helper removal may only surface indirectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: collect-agent-results retry visibility lacks quiet-init test coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: There is no direct test that retry messages remain operator-visible via larch_err under quiet init, leaving a regression path to quiet-log-only output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Unrelated design structure tests expand branch scope
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: scripts/test-design-structure.sh changes appear unrelated to the Stage 2 breadcrumb migration and broaden the review/CI scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] ci-wait has orphan breadcrumb stream newline branch
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: ci-wait retains an orphan LARCH_BREADCRUMB_STREAM newline branch after the stderr migration, but reviewers identify it as a Piece 3 cleanup item.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: ci-wait larch_errf output bypasses prior stream redaction path
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: ci-wait now sends operator-visible CI strings through larch_errf/FD4 while LARCH_BREADCRUMB_STREAM remains, bypassing breadcrumb-monitor streaming redaction and sanitize_diagnostic_line hardening previously used for gh-derived output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_16: Retry breadcrumbs now reach operator stderr and need restrained content
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Retry breadcrumbs moved to operator stderr by design, so future retry text that includes paths or tool output could reach live transcripts without committed-log redaction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_17: ship-pr larch_err call leaks literal --category token
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: A migrated ship-pr larch_err call still passes --category=network-flake as a literal argument, causing operators to see the category token in stderr output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] create-pr forwards git stderr without sanitization
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: create-pr forwards git stderr to larch_err without sanitization or secret redaction, but the reviewer marks this as pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_19: Implement bootstrap B4-all test checks the wrong stream
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: skills/implement/scripts/test-implement-bootstrap.sh discards stderr and checks stdout for the coder breadcrumb, so it can pass or miss output after gating was removed and diagnostics moved to stderr.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_20: Family B monitors no longer receive breadcrumb stream records
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Migrated scripts no longer emit larch:bc records for Family B monitor pairs, so live monitor progress disappears until the Piece 3 monitor/env cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_21: run-log tree still shows ndjson breadcrumb files
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: docs/run-logs.md still shows breadcrumbs/*.ndjson in the committed run-log tree even though the migration now commits quiet logs instead.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
