# Review Round 3

- Mode: `diff`
- 15 accepted, 10 rejected (4 neutral)

## Accepted Findings

### FINDING_1: reviewer_signals omits dynamic/non-root reviewer outputs
- **Reviewer(s)**: cursor-specialist-security-output.txt, codex-specialist-security-output.txt, cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `reviewer_signals` scans only top-level/static output paths, so dynamic-archetypes, phase-shaped, or other non-root reviewer outputs can be excluded from committed logs and also absent from the concise audit carrier.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Walk dynamic-archetypes/ with the same output basename filters when building reviewer_signals; align _has_reviewer_outputs probe and add regression coverage.
  - From codex-specialist-security-output.txt: Scan dynamic-archetypes with the same safe file handling or emit explicit unavailable markers for omitted dynamic signals
  - From cursor-specialist-correctness-output.txt: Extend signal scan to include dynamic-archetypes/ and other output dirs per plan.
  - From codex-specialist-correctness-output.txt: Scan SOURCE_DIR plus dynamic dirs for *-output*.txt before exclusion and compose signals whenever any are present


### FINDING_10: migrated reviewer_signals audit scans lack pass/fail/skip coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-log-schema-migration-output.txt
- **Severity**: important
- **Concern**: Audit scan tests still exercise legacy/raw-file paths or partial coverage, leaving migrated `reviewer_signals` scans for NS-retry, codex-generalist waste, and trailing content under-tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add pass/fail/skip fixtures using round-meta reviewer_signals for all three migrated scans.
  - From cursor-specialist-testing-output.txt: Replace Test 24; add codex-generalist-waste and trailing-content reviewer_signals fixtures with skip paths.
  - From dyn-log-schema-migration-output.txt: Add hermetic `audit-scan-run.sh` fixtures for trailing-content and codex-generalist pass/fail/skip via `round-meta.json`, plus a legacy sidecar-only fixture asserting fallback or explicit skip behavior, and retire or repoint Test 24 to the real scan function.


### FINDING_11: implement log byte-budget regression guard is missing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Implement flushed logs lack a byte-budget regression fixture, so future artifact changes can re-bloat implement logs while design-only budget checks stay green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add synthetic implement multi-round flush fixture with byte ceiling per plan.
  - From cursor-specialist-testing-output.txt: Add implement multi-round flush fixture with pinned total-byte ceiling and reviewer-prune-ledger batch check.


### FINDING_15: reviewer_signals production failures can be swallowed or misreported clean
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-log-schema-migration-output.txt
- **Severity**: important
- **Concern**: Flush-time reviewer signal composition can fail or miss NS-retry data without making committed logs/audits fail, leaving concise logs with no transcripts and either skipped or zero-count audit results.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Remove || true or fail the flush; optionally write a minimal reviewer_signals stub on compose failure.
  - From dyn-log-schema-migration-output.txt: Treat “signals present, every `ns_retry_reason` empty, round had reviewer outputs” as `informational`/`fail` pending verification, or add a round-meta `signals_complete` flag set only when meta sidecars were successfully scanned at flush time.


### FINDING_18: legacy NS-retry sidecars are skipped before fallback scanning
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, dyn-log-schema-migration-output.txt
- **Severity**: important
- **Concern**: `scan_ns_retry_sidecars` skips immediately when `reviewer_signals` are unavailable, so legacy committed sidecars are not counted or failed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Check legacy sidecar globs before unavailable-signal skip, or use old file scan whenever reviewer_signals are absent
  - From dyn-log-schema-migration-output.txt: When signals are unavailable, fall back to the pre-migration file-glob path (count sidecars directly) and reserve `skip` for runs that lack both signals and sidecar files; keep the signal+orphan hybrid only as an enhancement on top of that fallback.


### FINDING_19: design waterfall dispatch rc can become successful all-slots-dropped state
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `dispatch-plan-review-panel.sh` can convert nonzero waterfall rc into `ALL_SLOTS_DROPPED=true` and rc 0, making crashes look like successful degraded-empty plan-review rounds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: After writing prune audit, return nonzero or emit a distinct failure state that plan-review-loop maps to panel-failed


### FINDING_2: ns_retry_reason can persist unsafe raw sidecar content
- **Reviewer(s)**: cursor-specialist-security-output.txt, codex-specialist-security-output.txt
- **Severity**: important
- **Concern**: `ns_retry_reason` extraction can follow unsafe sidecar inputs and persist arbitrary first-line/raw metadata into `round-meta.json`, creating a committed-log secret exposure path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Normalize to allowed NS_RETRY_REASON tokens only (UNKNOWN otherwise); never embed raw sidecar text; reuse meta-specific redaction before extraction.
  - From codex-specialist-security-output.txt: Skip symlinks with lstat or pass vetted find -type f paths, and restrict ns_retry_reason to explicit metadata keys/enums with no raw fallback


### FINDING_20: OOS annotation treats missing issue stdout as success
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `file-design-oos.sh` annotation can treat missing or empty `/issue` stdout as success, leaving OOS items unannotated and unreported.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Make missing/empty stdout nonzero except for an explicit sentinel-backed recovery path, and log/append the failure


### FINDING_21: dispatch/prune integration test plan items are missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Planned dispatch/prune integration tests were not added, leaving prune audit and fail-open status regressions without CI coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend the three harnesses per plan B3/B6/B7 and FINDING_3/6/10.


### FINDING_22: full five-round design integration coverage is missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Concise multi-round design coverage is only partial, so publish/continuation bugs outside the publish script path may not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add full 5-round integration test with ledger all rounds four-file contract and byte budget.


### FINDING_25: skipped NS-retry scans aggregate as zero delta
- **Reviewer(s)**: dyn-log-schema-migration-output.txt
- **Severity**: important
- **Concern**: Counter aggregation treats skipped `ns-retry-sidecars` scan rows as count zero, making unavailable data look metrically clean in cumulative reports.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-log-schema-migration-output.txt: Only add to `delta_ns_retries` when `result=="fail"` (or emit an explicit `partial_data`/`skipped_runs` counter for `result=="skip"` and teach report writers to surface it).


### FINDING_28: audit/run-log docs still describe pre-concise raw-file semantics
- **Reviewer(s)**: dyn-log-schema-migration-output.txt, dyn-artifact-gate-regression-output.txt
- **Severity**: latent
- **Concern**: Operator-facing docs still point audit and run-log consumers at raw files, sidecars, capped vote outputs, or legacy fields instead of `reviewer_signals[]` and concise committed-log semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-log-schema-migration-output.txt: Update `audit-scan-run.md`, `SKILL.md`, and `larch-log.md` in the same change to document `reviewer_signals[]` as the primary carrier, file fallback rules (if any), and the `skip` semantics for legacy logs.
  - From dyn-artifact-gate-regression-output.txt: Update both docs to the concise default contract, `reviewer_signals` schema, debug-gated families, and note that `collector` (not `collect_log`) remains when `collector-results.env` exists.
  - From dyn-artifact-gate-regression-output.txt: Update the SKILL table and `audit-scan-run.md` to match the new scan types/locations; call out that `skip` means “concise carrier missing,” not “clean run.”


### FINDING_7: corpus smoke thresholds are looser than acceptance criteria
- **Reviewer(s)**: codex-specialist-security-output.txt, cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-fluff-analysis-corpus.sh` permits accepted-low-value and latent acceptance rates above the stated KPI, allowing post-v49 regressions to pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt: Enforce the documented <1% accepted-low-value and <=2% latent acceptance thresholds, or update the acceptance contract and tests together
  - From cursor-specialist-correctness-output.txt: Tighten to latent acc <=2.0% and accepted-low-value <1.0% with existing skip-when-no-corpus behavior.
  - From codex-specialist-correctness-output.txt: Tighten assertions to latent <=2.0% and accepted-low-value <1.0% or update the stated acceptance criteria
  - From cursor-specialist-edge-cases-output.txt: Tighten checks to <1.0% accepted-low-value and 0.0%-2.0% latent acc.
  - From cursor-specialist-testing-output.txt: Tighten to accepted-low-value <1.0% and latent <=2.0% per plan.
  - From codex-specialist-testing-output.txt: Restore the planned bounds or update the acceptance criteria and corpus selection intentionally.


### FINDING_8: category extraction happens after prose truncation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `compose-review-findings.sh` extracts category from truncated prose, so long rejected/OOS findings with category markers after the cap emit blank or wrong category metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Extract category from the full redacted body before truncation, mirroring body_severity/focus_area.
  - From codex-specialist-correctness-output.txt: Extract category from the full redacted body before truncating, then cap only prose_body
  - From cursor-specialist-edge-cases-output.txt: Extract category from full redacted body before prose truncation.


### FINDING_9: missing truncation regression for severity/focus extraction
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Tests do not cover severity/focus extraction from full bodies beyond the 2000-character prose cap, so future regressions could silently lose classification metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add the planned harness case asserting body_severity/focus_area from full body and capped prose_body.
  - From cursor-specialist-testing-output.txt: Add fixture with Severity marker past 2000 chars; assert body_severity from full body and capped prose_body.
  - From codex-specialist-testing-output.txt: Add a fixture with severity/focus markers beyond 2000 chars and assert the new fields plus capped prose_body.


