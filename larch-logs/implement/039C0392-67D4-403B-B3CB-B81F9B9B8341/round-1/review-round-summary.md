# Review Round 1

- Mode: `diff`
- 11 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Undated ledger rows bypass the analytics window
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: Ledger records with missing or zero `fix_time` bypass the 14-day analytics window and can inflate chronic-zone counts, causing incorrect risk promotion. Exclude undated records from windowed aggregates unless valid metadata is hydrated first.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.


### FINDING_2: Git hydration is not persisted
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-ledger-history
- **Severity**: major
- **Concern**: Successful hydration of historical `fix_time`, `touched_files`, `added_lines`, and derived zones updates only the in-memory analytics view. Because those updates are not persisted with marker backfills, later runs repeat git probes and can produce different analytics or risk routing after transient failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-ledger-history: Collect git-hydration updates the same way marker backfill does (only when probes succeed), append them through the existing post-report `_append_private_jsonl` path in `render_report`, and skip re-hydration when persisted metadata already matches the `fix_sha`.


### FINDING_3: Failed marker backfills consume the retry budget
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-ledger-history
- **Severity**: minor
- **Concern**: The historical marker backfill counter increments before confirming that a non-empty fingerprint was returned. Repeated API or GitHub failures can exhaust the fixed budget without persisting evidence, preventing later candidates from being processed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-ledger-history: Increment the budget only after a successful fetch (non-empty fingerprint), or track separate attempt vs success caps and prefer retrying issues that have no persisted `marker_fingerprint`.


### FINDING_5: Deep verdicts lose to mechanical verdicts
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases, cursor-specialist-testing
- **Severity**: major
- **Concern**: Final-verdict selection evaluates mechanical evidence before deep-verification evidence. A valid deep result can therefore be ignored, producing an incorrect verdict tier and corrupting snapshots, verified-issue membership, and deltas.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


### FINDING_6: Invalid predecessor snapshots can abort report rendering
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-ledger-history
- **Severity**: major
- **Concern**: `_previous_snapshot` fails the report when any historical `run-state.json` is corrupt, schema-invalid, or missing newer fields such as `verified_predicate`. A single bad predecessor can block unrelated reports and delta rendering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-ledger-history: Treat missing `verified_predicate` as a legacy schema with a documented default, or ignore malformed/legacy predecessor snapshots when computing deltas while still validating snapshots written by the current code.


### FINDING_9: Canonical corpus and tie-break coverage is missing
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: Required tests for per-issue canonicalization and tie-breaking are absent. Regressions involving multi-row ledgers, cache-key conflicts, `updated_at` or append-order ties, and manifest-overlay precedence could double-count analytics or select stale fixes without CI detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_10: Risk-promotion and sampling behavior lack isolated tests
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: The chronic-zone, cross-language, size, queue-cap, ordering, sampling, and default/zero-sample routing rules are not covered independently. Regressions can cause under-routing, incorrect queue order, unintended calibration work, or lost dropped-candidate persistence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_11: Tier, predicate, metadata, and agent-contract tests are missing
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: Required tests for verdict-tier precedence, the verified-issue predicate, metadata preservation through verdict upserts, and the agent bundle-field contract are absent. Upserts or snapshot calculations could silently lose analytics metadata or miscompute verified deltas.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_12: CLI sample defaults are untested
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The default `--sample 3` behavior and explicit `--sample 0` disable path are not tested, so a default calibration-load regression could go unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_16: Report golden, corpus, snapshot, and rerender tests are incomplete
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: major
- **Concern**: Required coverage for complete report output, cost-footer grammar, historical-ledger analytics, deferred persistence, snapshot validation, canonicalization, and deterministic rerender deltas is missing, so broad report-contract regressions may pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.


### FINDING_17: Marker backfill can persist false completion
- **Reviewer(s)**: dyn-dyn-ledger-history
- **Severity**: major
- **Concern**: `_marker_evidence` returns a non-empty SHA-256 fingerprint even when no marker phrase or issue reference exists. The backfill path treats that as success and can persist `marker_references: []`, permanently suppressing future backfill even if marker language is later added.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-ledger-history: Persist marker metadata only when `marker_references` is non-empty, or store fingerprint plus references together and re-backfill when the live issue-text fingerprint disagrees with the persisted provenance.
