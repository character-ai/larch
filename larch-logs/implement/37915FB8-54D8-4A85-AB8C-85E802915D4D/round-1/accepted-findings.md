### FINDING_1: Quiet wrapper harness is not wired into CI/Makefile
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-cli-wrapper-output.txt, dyn-ci-harness-output.txt
- **Severity**: important
- **Concern**: `skills/report-tokens/scripts/test-run-analysis-quiet.sh` exists as the quiet/FD-restore regression harness, but is not registered in Makefile, CI harness shards, or relevant-checks, so quiet-mode stream restoration can regress without automated signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-cli-wrapper-output.txt, dyn-ci-harness-output.txt: Address the concern above.


### FINDING_10: `NO_PLOT=0` disables plots inconsistently
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `report_tokens_plot.plot()` reads raw `LARCH_REPORT_TOKENS_NO_PLOT`, so `0` disables plotting even though CLI env parsing treats `0` as false.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_11: Bucket-mode token pricing can under-report spend
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-token-pricing-output.txt
- **Severity**: important
- **Concern**: Bucket pricing is selected for non-empty or malformed `BUCKETS_*` objects even when the actual priced lanes are zero, causing `token-cost.sh` to return zero cost despite positive aggregate vendor totals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-token-pricing-output.txt: Address the concern above.


### FINDING_13: Issue trimming measures a different body than `gh issue create` posts
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-issue-publish-output.txt
- **Severity**: important
- **Concern**: `post_issue()` / `_trim_sections()` trim after one redaction pass, but `gh.issue_create()` applies fail-closed redaction again, so a body can pass byte trimming yet fail posting at the edge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-issue-publish-output.txt: Address the concern above.


### FINDING_14: Scan follows symlinked run directories outside `larch-logs`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Symlinked run directories under `larch-logs` can point outside the repo and cause external JSON to be read into public aggregates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_15: Plot parent trusts child-returned paths
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-plot-isolation-output.txt
- **Severity**: latent
- **Concern**: `report_tokens_plot.py` trusts plot child JSON paths without confirming they are existing files confined to `plot_dir`, which can print bogus paths or invoke macOS `open` on unintended files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-plot-isolation-output.txt: Address the concern above.


### FINDING_19: `unknown/unknown` issue URLs are fabricated when repo slug resolution fails
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-cli-wrapper-output.txt, dyn-ship-parity-output.txt
- **Severity**: important
- **Concern**: When repo slug resolution fails, especially with `--no-issue` or before issue-post failure, rendered tables can contain plausible but false `https://github.com/unknown/unknown/issues/N` links.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-cli-wrapper-output.txt, dyn-ship-parity-output.txt: Address the concern above.


### FINDING_20: Git repo-root resolution failure falls back to cwd
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-ship-parity-output.txt
- **Severity**: important
- **Concern**: If `git rev-parse` fails, scanning falls back to `Path.cwd()` with only a warning, which can scan the wrong `larch-logs` tree or exit 0 with empty analysis.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-ship-parity-output.txt: Address the concern above.


### FINDING_21: Planned issue trim/oversize tests are missing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-issue-publish-output.txt
- **Severity**: important
- **Concern**: Tests do not cover body trimming, truncation banner/order, oversize-after-trim failure, or fail-closed `ShipError` propagation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-issue-publish-output.txt: Address the concern above.


### FINDING_22: Empty manifest objects are skipped without warning
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Runs with `{}` manifests disappear silently instead of emitting a clear skip warning for missing `issue_number`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_27: Scan fail-soft fixture coverage is incomplete
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Planned tests for bad manifest, timing, token-report, and slug-missing scan cases are absent, so fail-soft behavior may regress.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_38: Python ship path lacks authoritative phase state for routing/retries
- **Reviewer(s)**: dyn-ship-parity-output.txt
- **Severity**: important
- **Concern**: Phase 7 Python ship output does not provide or update phase state consistently with orchestrator instructions, so agents can read stale `PHASE` values, re-enter bash shipping, or mis-bucket Exit 6 retry counters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-parity-output.txt: Address the concern above.


### FINDING_40: `test-merge-parity` pytest entrypoint differs from `py-test`
- **Reviewer(s)**: dyn-ci-harness-output.txt
- **Severity**: latent
- **Concern**: `test-merge-parity` runs pytest from repo root while `py-test` runs from `python/`, so CI gates can diverge on import/config discovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-harness-output.txt: Address the concern above.


### FINDING_5: Invalid `LARCH_REPORT_TOKENS_REPO` values are not fail-closed
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-cli-wrapper-output.txt
- **Severity**: important
- **Concern**: Malformed or unsafe `LARCH_REPORT_TOKENS_REPO` overrides are silently ignored or loosely accepted, producing late generic failures or misleading rendered links instead of an explicit owner/repo validation error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-cli-wrapper-output.txt: Address the concern above.


### FINDING_8: Truncation notice uses internal section keys
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Trimmed issue bodies report omitted internal keys like `trends,rates` instead of reader-facing markdown section titles.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


