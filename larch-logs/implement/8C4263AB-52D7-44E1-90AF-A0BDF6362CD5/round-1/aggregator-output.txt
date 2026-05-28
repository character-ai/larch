### FINDING_1: unresolved vars are suppressed in scoped pin checks
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: In `--changed-files` mode, unresolved `$VAR` targets can be skipped without `UNRESOLVED_VAR`, contradicting the documented contract and letting typoed or misconfigured pin assertions pass local `relevant-checks`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: double-quoted static pins are skipped
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Double-quoted `contains` literals containing backticks or `$` are classified as non-canonical and skipped, so edits to target docs can bypass the new verifier until broader harnesses run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_3: Bash 3.2 portability is only statically checked
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The portability harness greps for known forbidden syntax instead of executing the verifier under Bash 3.2 when available, so unrecognized Bash 4-only constructs could pass locally and fail on macOS Bash 3.2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_4: relevant-checks does not test pin verifier failure propagation
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The relevant-checks fixture covers pin verifier success but not verifier exit `1`, so a regression that drops `PINS_EXIT` propagation could allow pin defects to pass before `agent-lint`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: pin scanner parses all test harnesses on each relevant-checks run
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `relevant-checks` parses the full `test-*.sh` tree for pin assertions on every invocation, creating avoidable O(all harness lines) cost for small local commits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] branch bundles unrelated readability work
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The branch includes stacked #2828 readability changes alongside #3064 pin-verifier work, which can confuse review and CI triage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_7: scoped verifier ignores changed pin-bearing test scripts
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Scoped verification keys only on resolved target document paths, so commits that change only `scripts/test-*.sh` pin text can skip local pin checks until CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: relevant-checks does not assert pin phase accounting
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Fixture 3f does not assert that the pin verifier increments `PHASES_RUN`, so phase accounting could regress without the existing fixture failing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_9: read-only verifier assertion is missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The plan-required `git diff --quiet` before/after assertion is absent, so CI would not catch a verifier regression that writes to the repo.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_10: SCRIPT_DIR/../ variable resolution lacks fixture coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: There is no fixture covering `VAR="$SCRIPT_DIR/../target.md"` resolution, leaving `script_parent` relative composition vulnerable to regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] design structure routing remains incomplete for some pin edits
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Some non-design-file pin-bearing edits remain CI-only unless paths match the new routing rules.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] DEFECT output may be hidden by quiet contract
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `DEFECT` output uses `emit()` and may be suppressed under the quiet contract, leaving developers with exit `1` but no visible defect message.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: readability style file can exfiltrate arbitrary local files
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `READABILITY_STYLE_FILE` / `--readability-style-file` can load any readable local file into externally dispatched plan-review prompts, creating a local-file disclosure path if pointed at secrets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] generated Cursor implementer omits hard-guard rule
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `agents/cursor-implementer.md` omits hard-guard rule 9, so Cursor implementers may miss the interactive-subprocess prohibition present for Codex implementers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_15: forward-only variable assignment scan can miss later definitions
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The scanner only resolves variable assignments seen before a `contains` line, so a future harness that declares `contains` before `VAR="$REPO_ROOT/..."` can be skipped silently in scoped runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: scanner deviates from planned POSIX awk implementation
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The implementation uses Bash regex parsing instead of the planned POSIX `awk` scanner, making plan acceptance harder to evaluate if `awk` was intended as a portability requirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
