### FINDING_1: [OUT_OF_SCOPE] Double-quoted pin literals are skipped by verifier
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The pin verifier skips or cannot parse double-quoted `assert_contains` literals containing backticks, `$`, or embedded escaped quotes. Several `test-design-structure.sh` pins can therefore drift without being verified by `relevant-checks`, with failures deferred to the full design structure harness or CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: Pin-phase temp file lacks cleanup trap
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/relevant-checks.sh` creates a temporary changed-files list for the pin verifier without an `EXIT` trap, so interrupted runs can leave `_tmp_changed` files under `/tmp`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Bash 3.2 portability coverage is static only
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-check-contains-pins.sh` validates Bash 3.2 compatibility through source greps rather than running the verifier under an actual Bash 3.2 binary when available, so runtime-incompatible constructs could slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_4: Changed-files mode scans every harness file
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: In changed-files mode, the verifier still reads every harness file and only later filters by target scope, adding avoidable work for narrow edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Unrelated lint-readability-preamble Makefile target
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `lint-readability-preamble` was added from a different branch and is unrelated to the pin verifier acceptance criteria.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] SCRIPT_DIR/../ resolver has no current consumer or coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The `SCRIPT_DIR/../` resolution branch in `scripts/check-contains-pins.sh` appears unused and lacks direct harness coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_7: Missing positive target-changed changed-files regression case
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The verifier harness tests the inverse skip path but not the positive case where only a target file is listed in `--changed-files`. A regression in target matching could miss the original #3064 scenario.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: Harness does not assert verifier read-only behavior
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-check-contains-pins.sh` does not verify that running the pin verifier leaves the worktree unchanged, so future write side effects may not be caught by the dedicated harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: Path normalization can resolve outside repository
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `normalize_rel` collapses `..` segments but does not enforce that resolved targets stay under `REPO_ROOT`; a malicious in-repo harness assignment could make fixed-string checks read outside the repository.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_10: Deletion-only commits skip direct targets and pin verification
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/relevant-checks.sh` exits early for deletion-only commits before running direct relevant targets or the pin verifier, so pin-relevant deletions may avoid local mechanical checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_11: Missing resolved targets warn instead of failing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: When a resolved target file is missing, the verifier reports an unresolved warning and exits successfully rather than treating a changed missing target as a defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_12: Missing pin verifier script fails open
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: If `scripts/check-contains-pins.sh` is absent, `relevant-checks.sh` prints a warning and continues without incrementing the pin phase, allowing local checks to succeed without mechanical pin verification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: Test-script-only design edits do not run full design structure harness
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Edits only to `scripts/test-design-structure.sh` rely on `check-contains-pins.sh`; `test-design-structure` is not routed as a direct relevant target, which may surprise developers expecting the full harness to run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: Orchestrator-inline readability lint is file-scoped, not section-scoped
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/lint-readability-preamble.sh` checks for required text at file level, so removing a mandatory directive from one `/design` step could still pass if another copy remains elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Non-v1 pin shapes remain outside verifier coverage
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Backlog pins using assignment or assertion shapes outside the v1 grammar remain unverified and may produce unrelated unresolved or skipped reports.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Sketch readability variant counts tokens instead of exact lines
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The sketch readability lint counts `READABILITY_STYLE` tokens rather than exact required lines, so extra token mentions could satisfy the count without the intended prompt text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: Parser implementation diverges from plan’s POSIX awk requirement
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The plan requires POSIX awk per-file parsing, but `scripts/check-contains-pins.sh` implements parsing with Bash regexes, leaving docs and acceptance text inaccurate relative to the shipped implementation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_18: Changed-files scoping is broader than plan wording
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `--changed-files` verifies pins when the test script path changed as well as when the resolved target changed, which is stricter than the plan’s target-only wording and should be documented or narrowed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_19: Pin phase traceability drift from plan helper name
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The plan names a `run_contains_pins_check()` helper, but the implementation inlines the phase in `scripts/relevant-checks.sh`, creating minor traceability drift without functional impact.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
