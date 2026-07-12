### FINDING_4: [OUT_OF_SCOPE] Added-line metadata is not rehydrated when partial
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: Hydration skips re-probing `added_lines` when `fix_time` and `touched_files` are populated, so partial metadata with `added_lines=0` can miss size-based deep promotion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_8: [OUT_OF_SCOPE] Serialized truncated-candidate data is ambiguous
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: `_emit_kvs` stringifies `DEEP_TRUNCATED_CANDIDATES` dictionaries on stdout, so parsers consuming ledger-summary KVs may misread the truncation reasons.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=2 NO=0 JUDGE_ERROR=1 Result=accepted Fileable=false

### FINDING_13: [OUT_OF_SCOPE] Manifest and ingest timestamps may drift
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Ingest upserts use wall-clock `updated_at`, while metadata upserts use `manifest.generated_at`, creating potential canonical-order drift across reruns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_14: [OUT_OF_SCOPE] Marker phrase coverage is incomplete
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Tests cover only one marker phrase, leaving alternate required phrase families vulnerable to unnoticed regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_15: [OUT_OF_SCOPE] Golden output assertions omit edge-case fields
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Golden report coverage does not assert zero-sample false-pass output or truncated-candidate reasons, allowing report-contract drift on edge outputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_19: [OUT_OF_SCOPE] Ledger canonicalization differs between loaders
- **Reviewer(s)**: dyn-dyn-ledger-history
- **Severity**: minor
- **Concern**: `load_ledger` still collapses append-only ledger rows by `cache_key` using last-row-wins, while `load_analytics_corpus` uses append ordinal. Upsert and analytics paths can therefore disagree when multiple valid rows share a cache key.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-ledger-history: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_20: [OUT_OF_SCOPE] Verified-issue classification may be too broad
- **Reviewer(s)**: dyn-dyn-ledger-history
- **Severity**: minor
- **Concern**: `_verified_issue` treats any non-empty tier with a verdict other than `NEEDS_DEEP` as verified, including `UNVERIFIABLE`, `NOT_FIXED`, and `INCOMPLETE`, which may inflate “Newly verified” deltas.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-ledger-history: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_21: [OUT_OF_SCOPE] Routing cannot see metadata appended in the same computation
- **Reviewer(s)**: dyn-dyn-ledger-history
- **Severity**: minor
- **Concern**: `ledger_compute` builds analytics before appending metadata upserts, so routing cannot see coordinator metadata that exists only in newly appended ledger rows. Manifest overlay currently masks the issue, but the ordering is fragile.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-ledger-history: Address the concern above.
Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false
