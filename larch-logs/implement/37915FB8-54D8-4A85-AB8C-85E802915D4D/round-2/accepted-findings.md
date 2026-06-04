### FINDING_12: Invalid LARCH_REPORT_TOKENS_LIMIT is ignored instead of failing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: An invalid limit value is warned and ignored, so a typo like `100x` scans all run directories and may post an unexpectedly large issue instead of exiting clearly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_13: Successful GitHub issue creation prints no URL or confirmation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-issue-body-output.txt
- **Severity**: important
- **Concern**: When issue posting succeeds, stdout lacks the created issue URL or confirmation line, leaving operators and automation without the durable pointer emitted by the previous implementation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-issue-body-output.txt: Address the concern above.


### FINDING_14: Cache JSON trailer is emitted twice
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Successful runs can print duplicate `Cache JSON:` lines, which can confuse downstream parsers expecting a single trailer path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_16: CLI e2e coverage is missing for main orchestration and issue-post gates
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Tests do not execute the CLI `main()` success path or planned fake-Runner stdout/cache/env contracts, and they do not adequately guard the missing repo-slug fail-before-post behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_17: Real token-cost.sh integration coverage is missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-pricing-contract-output.txt
- **Severity**: important
- **Concern**: Tests named like token-cost integration use fake Runner output instead of executing `scripts/token-cost.sh`, so argv/env drift and rate override propagation to the pricing authority can ship undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-pricing-contract-output.txt: Address the concern above.


### FINDING_18: Design SIMPLE/HARD render and plot split coverage is incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Tests do not explicitly guard the required design SIMPLE/HARD split in rendered trend sections and plot payloads, or the implement path’s lack of workflow subheads.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_19: Quiet wrapper harness lacks failure-mode and design-path coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-quiet-streams-output.txt
- **Severity**: important
- **Concern**: The bash quiet harness mainly covers one implement success path and misses `--plot-from` rejection, invalid/missing skill paths, repo-resolution failures under inherited quiet, and design wrapper passthrough.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-quiet-streams-output.txt: Address the concern above.


### FINDING_20: Scan warning/skip fixture coverage is incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Plan-listed invalid timing, run-params, and token-report fixture cases are missing, so scan warn-and-skip behavior for auxiliary JSON can regress without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_21: token-cost fallback warning behavior lacks tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Missing tests for token-cost failure and fallback warning paths could allow silent wrong headline costs if fallback handling or stderr warnings regress.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_22: Plot series labels can escape the output directory
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The plot child uses series labels in output filenames without rejecting path components, so a crafted standalone payload could write PNGs outside the intended output directory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_24: /report-tokens docs still list no arguments
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The skill catalog still says `/report-tokens` has no arguments even though the wrapper requires `--skill`, so consumers following docs will hit validation failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_25: Claude blended pricing path may use the wrong token total
- **Reviewer(s)**: dyn-pricing-contract-output.txt
- **Severity**: important
- **Concern**: For Claude blended pricing, the Python argv builder uses `VendorTotals.total` where the removed bash/Python path used component sums; real reports can diverge, shifting headline Claude costs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pricing-contract-output.txt: Address the concern above.


### FINDING_28: Missing skill-specific token report is skipped without warning
- **Reviewer(s)**: dyn-scan-pipeline-output.txt
- **Severity**: important
- **Concern**: A run with a valid manifest but no skill-specific token report file is silently dropped, so operators see under-reported analysis with no explanation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scan-pipeline-output.txt: Address the concern above.


### FINDING_3: Phase rows are collected but not rendered
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `phase_rows` are parsed during scan but not consumed downstream, leaving extra complexity and removing the HARD phase-breakdown output expected from the prior/report plan shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.


