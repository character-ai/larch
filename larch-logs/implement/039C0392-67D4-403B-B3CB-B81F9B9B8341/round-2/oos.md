### FINDING_13: [OUT_OF_SCOPE] Analytics built before metadata upsert in `ledger_compute`
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: `ledger_compute` builds analytics before same-turn metadata upserts append coordinator rows. Same-call routing cannot see metadata written only in that upsert pass and currently relies on bundle overlay; future overlay changes could desync queue construction from persisted metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Build analytics after metadata upsert or reload ledger before routing
  - From cursor-specialist-edge-cases: Rebuild analytics after metadata append or fold upserted rows into the view.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_14: [OUT_OF_SCOPE] `_verified_issue` counts negative mechanical finals as verified
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-ledger-history
- **Severity**: minor
- **Concern**: `_verified_issue` treats any non-empty tier with a verdict other than `NEEDS_DEEP` as verified, so mechanical `NOT_FIXED`, `UNVERIFIABLE`, or `WONTFIX` finals inflate “Newly verified” in `Since last run` even when verification did not confirm a fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Tighten predicate to positive fix verdicts if operator semantics require it
  - From cursor-specialist-edge-cases: Narrow the predicate if product intent is success-only verification.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_15: [OUT_OF_SCOPE] `DEEP_TRUNCATED_CANDIDATES` stdout is not structured for KV parsers
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: `_emit_kvs` uses `str()` on a dict list for `DEEP_TRUNCATED_CANDIDATES`, breaking KV parsers that read `ledger_compute` stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Emit JSON for complex KV values or document JSON-only sidecar


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_16: [OUT_OF_SCOPE] Unbounded GitHub issue body fetch during marker backfill
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Historical marker backfill reads unbounded issue bodies from GitHub; pathological issue bodies can waste coordinator CPU during backfill regex scanning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Cap fetched body size before marker regex scanning.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_17: [OUT_OF_SCOPE] Marker phrase coverage tests only one regex family
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Marker phrase coverage tests exercise only one required phrase family; alternate marker regex families could regress unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: expand only if regressions appear.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_18: [OUT_OF_SCOPE] Missing focused canonicalization, routing, and CLI default tests (architecture)
- **Reviewer(s)**: dyn-dyn-ledger-history
- **Severity**: minor
- **Concern**: Accepted round-1 coverage for canonical per-issue selection (`updated_at`/append-ordinal ties, manifest overlay, multi-cache-key ledgers), metadata carry-forward through verdict ingest, and CLI default `--sample 3` still has no focused tests; regressions there would not be caught before bad risk routing ships.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_19: [OUT_OF_SCOPE] `load_ledger` collapses rows by `cache_key` while analytics corpus preserves append order
- **Reviewer(s)**: dyn-dyn-ledger-history
- **Severity**: minor
- **Concern**: `load_ledger` collapses append-only rows by `cache_key` (last row wins) while `load_analytics_corpus` preserves append order, so upsert/routing consumers and analytics consumers can disagree when multiple valid rows share a cache key.
- **Suggested revisions (informational for voters; coder decides)**:
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false
