### FINDING_1: SECURITY.md overstates timing-report inputs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: SECURITY.md says `timing-report*.json` files are consulted for SIMPLE/HARD classification, but the scanner only reads the exact skill-specific timing report basename (`timing-report.json` or `timing-report-final.json`) plus `run-params.json`. This can mislead maintainers or reviewers into expecting other `timing-report*.json` files to affect classification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: Merge parity coverage is py-test-only
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Merge parity no longer runs through `make lint` / `test-harnesses-5`; coverage now depends on `make py-test` / python-tests. Contributors running only harness shards or lint locally can miss merge parity drift until CI python-tests runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] Missing parity cases for version_already_published paths
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Python merge parity does not cover `version_already_published` paths exercised by `scripts/test-merge-pr.sh`, so Bash merge race behavior can drift without failing `py-test`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
