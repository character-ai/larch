### FINDING_1: Breadcrumb tests still grep stdout after larch_err migration
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Postmerge and Phase 1-4 ship-pr harness assertions still inspect stdout for diagnostics now emitted through larch_err on stderr, so tests can fail or miss the migrated output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_10: Negative CI-watch breadcrumb test only checks stdout absence
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The negative CI-watch test can pass while the forbidden diagnostic still appears on stderr, because it only asserts absence from stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_17: ship-pr larch_err call leaks literal --category token
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: A migrated ship-pr larch_err call still passes --category=network-flake as a literal argument, causing operators to see the category token in stderr output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_19: Implement bootstrap B4-all test checks the wrong stream
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: skills/implement/scripts/test-implement-bootstrap.sh discards stderr and checks stdout for the coder breadcrumb, so it can pass or miss output after gating was removed and diagnostics moved to stderr.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_2: Implement bootstrap docs still describe removed breadcrumb env gating
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: implement-bootstrap documentation and behavior disagree about LARCH_QUIET_BREADCRUMBS gating: the helper now emits progress unconditionally via larch_err/stderr, while docs and expectations still describe env-gated stdout breadcrumbs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_21: run-log tree still shows ndjson breadcrumb files
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: docs/run-logs.md still shows breadcrumbs/*.ndjson in the committed run-log tree even though the migration now commits quiet logs instead.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

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


### FINDING_9: ship-pr docs still describe removed breadcrumb stream categories
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: scripts/ship-pr.md still describes LARCH_BREADCRUMB_STREAM category vocabulary after Stage 2 removed stream emission from ship-pr.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


