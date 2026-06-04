### FINDING_1: [OUT_OF_SCOPE] Issue body redaction and trim measure a different body than gh posts
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-issue-body-output.txt
- **Severity**: important
- **Concern**: Issue body assembly applies redundant redaction passes before trimming, and `gh.issue_create` may redact again before posting. This violates the single-pass contract and can make byte-limit trimming or PEM fail-closed behavior diverge from the exact body sent to GitHub.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-issue-body-output.txt: Address the concern above.

### FINDING_2: Skill/workflow aggregation logic is duplicated between render and plot
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Render-table grouping and plot-series grouping implement the same skill/workflow aggregation rules separately, making future rule changes prone to drift between markdown and graph output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Phase rows are collected but not rendered
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `phase_rows` are parsed during scan but not consumed downstream, leaving extra complexity and removing the HARD phase-breakdown output expected from the prior/report plan shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_4: Branch combines unrelated change areas
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The branch mixes ship-pr Phase 7 work, report-tokens migration, and larch-logs chore changes, increasing review, regression, and revert risk for otherwise separable work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Truncation banner is not modeled as a BANNER section
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The truncation notice is handled as a raw string prefix while `SectionPriority.BANNER` remains unused, so the implementation does not match the intended section-priority trim contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_6: Small helper functions are duplicated across report_tokens modules
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Helpers such as `_date`, env flag parsing, and mapping conversion are repeated across modules, making small behavior fixes easier to miss.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: render() has parallel stdout and issue-section assembly paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `render()` builds stdout and issue sections through parallel paths, creating drift risk for fields such as actual spend and Cache JSON handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Non-object manifest.json reports the wrong skip reason
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: A malformed `manifest.json` with a non-dict JSON value is reported as lacking a numeric `issue_number` instead of as an invalid manifest shape, making corrupt manifests harder to diagnose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: SectionPriority.CACHE name is misleading for rates
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `SectionPriority.CACHE` names the rates section, which can be confused with cache NDJSON artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Plot child accepts malformed series/schema and can succeed with partial or empty plots
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-plot-isolation-output.txt
- **Severity**: latent
- **Concern**: `plot-cost-over-time.py` does not fully validate the documented payload contract and skips malformed series entries, allowing wrong labels, missing version/skill, extra series, or zero PNG output to appear successful.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-plot-isolation-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] LARCH_REPORT_TOKENS_LIMIT counts raw directories instead of valid/unique runs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-scan-pipeline-output.txt
- **Severity**: latent
- **Concern**: The scan limit is applied to immediate child directories before eligibility filtering and without unique issue semantics, so placeholder or invalid directories can consume the limit and hide valid runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-scan-pipeline-output.txt: Address the concern above.

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

### FINDING_15: [OUT_OF_SCOPE] Report-tokens operator failures reuse the stalled/bail exit code
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Report-tokens errors use an exit code that overlaps with stalled/bail constants, so wrappers cannot reliably distinguish operator or gh failures from stalled runs.
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

### FINDING_23: token-cost.sh subprocess has no timeout
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: If `token-cost.sh` hangs, `/report-tokens` can hang indefinitely instead of falling back with a warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

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

### FINDING_26: [OUT_OF_SCOPE] Cache JSON stdout path can leak temp/session paths
- **Reviewer(s)**: dyn-issue-body-output.txt
- **Severity**: latent
- **Concern**: Stdout still appends an unredacted `Cache JSON: {temp_path}` line, which can expose session temp paths in terminal transcripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-issue-body-output.txt: Address the concern above.

### FINDING_27: Issue-post ShipError handling can return nonzero without printing the exception
- **Reviewer(s)**: dyn-quiet-streams-output.txt
- **Severity**: important
- **Concern**: The CLI issue-post failure handler returns `EXIT_BAIL` without printing the caught `ShipError`, relying on every lower path to have already emitted stderr and risking silent failures after future refactors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-quiet-streams-output.txt: Address the concern above.

### FINDING_28: Missing skill-specific token report is skipped without warning
- **Reviewer(s)**: dyn-scan-pipeline-output.txt
- **Severity**: important
- **Concern**: A run with a valid manifest but no skill-specific token report file is silently dropped, so operators see under-reported analysis with no explanation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scan-pipeline-output.txt: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] Missing timing/run-params warnings are a plan/parity drift
- **Reviewer(s)**: dyn-scan-pipeline-output.txt
- **Severity**: latent
- **Concern**: Missing timing or run-params JSON still defaults workflow to unknown without warning; this matches prior bash behavior but conflicts with stricter plan wording.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scan-pipeline-output.txt: Address the concern above.

### FINDING_30: Plot parent does not verify expected PNG count per skill
- **Reviewer(s)**: dyn-plot-isolation-output.txt
- **Severity**: latent
- **Concern**: After the plot child returns, the parent validates path containment but not skill-specific output cardinality, so a design run with only one PNG could still be advertised as successful.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plot-isolation-output.txt: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] Plot subprocess contract is not exercised by tests
- **Reviewer(s)**: dyn-plot-isolation-output.txt
- **Severity**: latent
- **Concern**: Plot tests rely on fake Runner paths or optional smoke coverage, so the real child contract, especially design dual-series behavior and `MPLCONFIGDIR`, can drift without mandatory CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plot-isolation-output.txt: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] LARCH_REPORT_TOKENS_NO_OPEN flag parsing is inconsistent
- **Reviewer(s)**: dyn-plot-isolation-output.txt
- **Severity**: nit
- **Concern**: `LARCH_REPORT_TOKENS_NO_OPEN` treats any nonempty value as truthy/falsey via raw env lookup semantics, unlike the more explicit flag parsing used for `NO_PLOT`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plot-isolation-output.txt: Address the concern above.
