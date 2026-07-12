# Review Round 2

- Mode: `diff`
- 11 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Historical ledger rows with `fix_time=0` excluded before git hydration
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-ledger-history
- **Severity**: major
- **Concern**: Corpus construction filters out ledger rows with `fix_time == 0` before canonicalization, git hydration, and marker backfill run. Legacy rows that have a valid `fix_sha` but no persisted timestamp never enter analytics `records`, so chronic-zone membership, file-intersection chains, churn, and risk routing miss fixes that `git show` would place inside the manifest-anchored window.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Canonicalize all repository-local rows per issue, hydrate missing metadata, then apply the manifest-anchored time window.
  - From codex-specialist-edge-cases: Retain fix-SHA rows as hydration candidates, hydrate metadata, then apply the analytics window.
  - From cursor-specialist-testing: Hydrate fix_time from fix_sha before applying the 14-day window filter; add a ledger-only hydration regression test.
  - From codex-specialist-testing: Retain fix_sha-backed rows through hydration, apply windows after hydration, and test an undated historical row that hydrates into the window.
  - From dyn-dyn-ledger-history: **Suggested fix:** Build a candidate set from in-window or `fix_sha`-bearing corpus rows without requiring pre-existing `fix_time`, run read-only git hydration first, then apply the trailing-window filter on hydrated timestamps (and keep undated, unhydratable rows out of aggregates).


### FINDING_2: Hydration skip treats partial metadata as complete (`added_lines=0`, empty `touched_files`)
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: Hydration is skipped when `metadata_version>=1` and `fix_time>0`, even when routing-critical fields remain incomplete. Partial or legacy rows keep `added_lines=0` or empty `touched_files`, so size cross-language promotion and chronic-zone risk promotion never fire on later runs; a separate path where `fix_time>0` with `added_lines=0` also skips hydration and leaves bundle merge at zero.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Re-probe or merge added_lines when zero despite valid fix_time; do not treat zero as complete metadata
  - From cursor-specialist-edge-cases: Skip hydration only when all routing fields are present; otherwise re-probe git metadata and persist repaired rows.


### FINDING_3: Marker evidence persistence replaces hydrated git metadata
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: Marker-evidence persistence replaces an earlier hydrated record from the original ledger row and drops successful git metadata. Historical rows missing git metadata but containing residual marker text after rendering persist marker data only, repeat git probes on later runs, and can yield transient analytics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Merge marker evidence onto hydrated.get(cache_key, record.ledger_record) so git and marker metadata persist in one appended row.


### FINDING_4: Deep-cap truncation leaves tier inconsistent with `NEEDS_DEEP` verdict
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: Deep-cap truncation sets verdict `NEEDS_DEEP` but leaves the prior tier unchanged. After `FIXED_CLEAR`/`DEEP` ingest, an issue deep-capped mid-run can show `Tier=DEEP` and `Verdict=NEEDS_DEEP` in the Issues table.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Clear or relabel tier when truncation applies (e.g. PENDING) so tier and verdict agree


### FINDING_5: External marker-reference nodes inflate chronic-zone components
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: External marker-reference nodes participate in connected-component chronic-zone detection. Two canonical issues in one zone that reference the same issue outside the corpus can falsely mark the zone chronic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Use only edges whose endpoints are canonical analytics records when computing chronic-zone components; retain external edges for report output.


### FINDING_6: Dual `build_analytics_view` calls; hydration not persisted before deep-queue routing
- **Reviewer(s)**: dyn-dyn-ledger-history
- **Severity**: major
- **Concern**: `ledger_compute` and `render_report` each call `build_analytics_view` independently, but only `render_report` appends `analytics.hydrated_records` to the durable ledger. Stage-2 deep-queue routing depends on in-memory hydration, git probes, and marker backfill that are neither persisted before queue construction nor reused in Stage 3; transient git or GitHub failures between the two calls can change chronic zones, chain edges, and risk-promotion inputs after `deep-queue.jsonl` is written.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-ledger-history: **Suggested fix:** After `build_analytics_view` in `ledger_compute`, append `analytics.hydrated_records` (and any coordinator metadata upserts) before `_priority_deep_candidates`, and have `render_report` consume the persisted ledger state instead of re-probing from scratch.


### FINDING_8: Missing canonicalization tie-break tests (`updated_at`, `append_ordinal`, manifest overlay)
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: No CI guard for multi-row ledgers with cache-key conflicts, `updated_at` ties, or manifest-overlay precedence on one issue. Stale `fix_sha` selection can drive chains and mis-route analytics for unselected issues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add table-driven corpus tests for updated_at, append_ordinal, and manifest-overlay precedence
  - From cursor-specialist-edge-cases: Add table-driven tests for cache-key conflicts updated_at ties and manifest overlay precedence.


### FINDING_9: Missing broad plan-required analytics test matrix
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: Required tests for canonicalization, all risk routing rules, sample defaults, snapshots, rerendering, verified-tier membership, metadata carry-forward, and complete report output remain largely unimplemented. Regressions in newly introduced analytics, routing, sampling, and delta paths can pass CI because coverage exercises only a subset of plan acceptance criteria.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Add focused table-driven coverage for the plan-listed canonicalization, routing, sampling, snapshot, and verified-predicate cases.
  - From cursor-specialist-testing: Add the missing tests listed in the plan Testing strategy and Acceptance sections.
  - From codex-specialist-testing: Add the plan-specified table-driven and golden tests, prioritizing canonical selection, all routing rules, sample defaults, snapshot rerendering, and metadata upserts.


### FINDING_10: Missing focused routing tests (chronic-zone cross-language promotion, default `sample=3`)
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: No isolated tests for chronic-zone cross-language size promotion or the default `sample=3` CLI behavior. Plan acceptance criterion 2 and routing priority rules can regress unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add focused routing tests plus a ledger_main default-args test for sample.


### FINDING_11: No test that analytics metadata survives triage or deep verdict upserts
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Verdict ingest could drop coordinator fields during `_upsert_record` and break treadmill analytics on the next run; there is no ingest test asserting metadata carry-forward.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add ingest test asserting metadata carry-forward through _upsert_record.


### FINDING_12: Golden report test omits calibration and deep-cap contract assertions
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The golden report fixture does not assert calibration output, `0.00%` false-pass-rate lines, or deep-cap truncation sidecars. Removal of sample-size / false-pass-rate lines or truncated-candidate logging could ship without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Extend the golden fixture to assert calibration text, 0.00% false-pass output, and deep-cap truncation sidecars.
