# Review Round 1

- Mode: `diff`
- 12 accepted, 7 rejected (3 neutral)

## Accepted Findings

### FINDING_1: Audit scans still depend on raw reviewer files removed from concise logs
- **Reviewer(s)**: cursor-specialist-security-output.txt, codex-specialist-security-output.txt, cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-risk-integration-output.txt, dyn-architecture-output.txt
- **Severity**: important
- **Concern**: `audit-scan-run.sh` still scans raw NS-retry, first-pass, and Codex generalist output files that concise logging now excludes by default. This can produce false `pass`/`count=0` or unconditional skips instead of checking `round-meta.json` `reviewer_signals[]`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, codex-specialist-security-output.txt, cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt: Address the concern above.
  - From dyn-risk-integration-output.txt: Land the planned D15 migration in the same change set: teach all three scans to read `reviewer_signals[]` from each round’s `round-meta.json`, emit `skip` with an explicit “signal unavailable” detail when the array or required keys are absent, and update `scripts/test-audit-runs.sh` / `scans-implement.tsv` accordingly before relying on concise flush.
  - From dyn-architecture-output.txt: Implement the planned `reviewer_signals` readers in `audit-scan-run.sh`, update `test-audit-runs.sh` fixtures to use concise `round-meta.json` only, and emit `result:"skip"` with `detail:"…signal unavailable"` when required keys are absent.


### FINDING_10: `larch-log` golden tests omit new concise-log contract assertions
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-architecture-output.txt
- **Severity**: important
- **Concern**: `test-larch-log-write-round.sh` does not assert `reviewer_signals` schema, prune audit env inclusion, or byte ceilings, allowing producer, allowlist, or size regressions to pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-architecture-output.txt: Extend the round-meta Python assertion block to require `reviewer_signals` entries with `output_basename`, `slot_label`, `result_kind`, `ns_retry_reason`, and `first_pass_trailing_content` when fixture reviewer outputs exist.


### FINDING_12: Design prune ledger is not initialized or recorded on MAV paths
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Design prune ledger initialization and MAV/non-normal round recording are missing, so multi-round runs can publish absent or empty ledger history and later rounds may fail open.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_13: Design severity consumers still use legacy `major`/`minor`
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Design severities are normalized to `important`/`latent`/`nit`, but downstream reporting still checks old `major`/`minor` values, dropping accepted latent/minor findings from metrics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_14: Fluff-analysis corpus smoke test is not wired into CI
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-fluff-analysis-corpus.sh` exists but is not invoked by the main Makefile/CI path, so post-v49 corpus thresholds are not enforced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_18: Compose metadata extraction lacks regression coverage beyond prose cap
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: There is no test ensuring `body_severity` and `focus_area` are extracted before the 2000-character prose cap, so future truncation changes could blind fluff-analysis.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_19: Prune-status matrix and early-flush tests are missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Planned prune-status tests for advisory warn, fail-open, out-of-window skipped, pruned-empty, and review-core early-flush audit cases are absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_20: Design publish tests do not assert prune audit artifact staging
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test-design-log-publish.sh` does not assert that `prune-decision.env`, `prune-nit.env`, or root `reviewer-prune-ledger.tsv` are staged, so publish can omit prune audit files unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_26: `round-meta.json` and `reviewer_signals` are gated on unrelated sidecars
- **Reviewer(s)**: dyn-architecture-output.txt
- **Severity**: important
- **Concern**: `reviewer_signals[]` is only composed when `sidecar_paths` is non-empty, so early or minimal flushes with reviewer outputs but no tally/collector sidecars can omit `round-meta.json` and the new audit carrier.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-architecture-output.txt: Split round-meta composition: always run the `reviewer_signals` scan against `SOURCE_DIR` when any reviewer output exists; keep sidecar-driven keys (`tally`, `collector`, etc.) gated on their own inputs.


### FINDING_5: `reviewer_signals` uses the wrong NS-retry sidecar filename
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, dyn-risk-integration-output.txt, dyn-architecture-output.txt
- **Severity**: important
- **Concern**: The `reviewer_signals` producer looks for NS-retry metadata using the wrong basename pattern, while the collector writes `<stem>-ns-retry.txt.meta`. As a result, `ns_retry_reason` is usually empty in committed `round-meta.json`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-risk-integration-output.txt: Resolve NS-retry meta via the same basename rule as the collector (`os.path.join(src, name[:-4] + "-ns-retry.txt.meta")`), parse `NS_RETRY_REASON=` from that file, and add a harness fixture with a real `-ns-retry.txt.meta` sidecar asserting the populated `ns_retry_reason` lands in `round-meta.json`.
  - From dyn-architecture-output.txt: Resolve NS-retry meta via `os.path.splitext(name)[0] + '-ns-retry.txt.meta'` (and `.json` siblings), or join against the paired `-ns-retry.txt` basename; add a fixture with a real NS-retry sidecar layout in `test-larch-log-write-round.sh`.


### FINDING_7: Five-round design publish and byte-budget coverage is missing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The planned multi-round concise design publish integration test and byte-budget guard are absent, so dropped rounds or log re-bloat can ship unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_9: Non-HARD design round number binding lacks regression coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The C11 `STEP3_REVIEW_ROUND_NUM` / `ROUND_NUM` behavior lacks SIMPLE and HARD regression tests, so round artifacts could again land under the wrong directories.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


