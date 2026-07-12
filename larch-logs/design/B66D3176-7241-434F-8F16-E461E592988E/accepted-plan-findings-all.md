### FINDING_1: Analytics corpus must include historical ledger records
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Temporal Analytics Integrity
- **Severity**: major
- **Concern**: Chronic-zone counts, churn, file-intersection chains, and risk routing can under-report historical activity if analytics iterate only over the current manifest selection. The analytics view needs a defined union of deduplicated ledger records within manifest-anchored trailing windows plus current manifest overlays.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: State explicitly that the analytics view unions all in-window deduped `LedgerRecord` rows (plus current manifest overlays) and that zone/chain/churn math is not limited to `manifest.issues`.
  - From Cursor-Innovation: State explicitly that the aggregate view is built from all ledger records (canonicalized per issue/fix), with manifest bundles overlaying the active run; chronic, churn, and file-intersection helpers must consume that union.
  - From Cursor-Pragmatic: State explicitly that aggregations iterate deduped last-valid ledger records repo-wide within manifest-anchored trailing windows, union current bundles, and treat absent legacy metadata as unavailable rather than shrinking to manifest-only rows
  - From Cursor-Requirements: In Approach step 3, state that chronic-zone, churn, and file-intersection analytics iterate all ledger records inside the trailing window (deduped by issue/fix), then overlay the active manifest; risk routing reads that full view
  - From Cursor-dyn-Temporal Analytics Integrity: In Approach §3, require one `build_analytics_view(manifest, ledger, runner)` that unions deduped ledger issues with manifest bundles, anchors windows to `manifest.generated_at`, and read-only hydrates missing fix_time, touched_files, and added_lines from fix_sha during view build (same git helpers as prefetch). Persist hydrated fields to ledger after a successful report, not only on triage/deep ingest.


### FINDING_2: Cache-skipped metadata must be persisted
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Cache-complete issues that skip triage and deep ingest may never persist coordinator-derived analytics such as touched files, fix timestamps, zones, or added lines. Without an explicit metadata-only ledger upsert, later runs lose the historical evidence required for chains, chronic zones, and risk routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit coordinator-only upsert step (prefetch tail or `ledger_compute` prologue) that append-updates metadata for every manifest issue via existing cache-key matching, without changing agent bundle/JSONL contracts.
  - From Cursor-Innovation: Add an append-only coordinator metadata pass after prefetch (or before report) for every selected bundle: merge analytics fields into the latest row per `cache_key` without requiring a new verdict ingest.
  - From Cursor-Pragmatic: After prefetch (or at ledger_compute/report), append additive ledger rows for every manifest-selected issue with coordinator-derived metadata, even when triage/deep ingest is skipped; keep last-valid cache_key merge semantics
  - From Cursor-Requirements: Add an explicit step: after prefetch derives metadata for every selected issue, append or upsert analytics fields to ledger.jsonl before routing/reporting, including rows that skip triage/deep ingest because stages are already complete


### FINDING_4: Analytics records require explicit per-issue deduplication
- **Reviewer(s)**: Cursor-dyn-Temporal Analytics Integrity
- **Severity**: major
- **Concern**: Multiple cache keys can exist for one issue after re-verification or fix changes. Without a deterministic winner, stale and current rows may double-count zones, churn, and chains or pair chains against obsolete SHAs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Temporal Analytics Integrity: Specify dedup in the analytics builder: one fix record per issue, prefer manifest bundle when cache_key matches, else highest `updated_at`, else last append order. Use that record for zones, chains, churn, and promotions. Add a test with two cache_keys for one issue.


### FINDING_5: Chronic zones require connected in-zone members
- **Reviewer(s)**: Codex-Arch, Cursor-Pragmatic, Codex-Requirements
- **Severity**: minor
- **Concern**: Marking a zone chronic when two of its members merely touch unrelated external edges produces false chronic zones and unnecessary deep routing. The threshold must require two zone members in the same connected chain component, while still allowing paths through issues in other zones if intended by the specification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Build connected components from chain edges and mark the zone chronic only when at least two bugs in the same component belong to that zone. Preserve the specified cross-zone edge behavior without treating unrelated endpoint memberships as connected
  - From Cursor-Pragmatic: Align chronic chain rule with spec (in-zone connected pair/component) or document intentional broadening in Approach and tests
  - From Codex-Requirements: Require at least two zone members in the same connected chain component. Allow paths through issues in other zones, and add a disconnected-edge test.


### FINDING_6: Risk promotions must require verified triage evidence
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Risk-based promotion of `FIXED_CLEAR` or `FIXED_LIKELY` issues must use the same verified-triage gate as the calibration sample pool. Checking only the verdict could re-queue unverified legacy ledger rows and violate the evidence-token contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Require `_triage_complete(record, refresh=refresh)` (or equivalent) for all four risk rules; add a table test mirroring the existing unverified-legacy sample exclusion for risk `source` values.


### FINDING_9: Upserts must preserve coordinator analytics fields
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: Triage or deep ingestion can rebuild ledger records from verdict fields and silently discard metadata previously written by the coordinator in the same run. New analytics fields need explicit carry-forward behavior across mapping, upsert, and serialization paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Document and implement preservation of analytics fields in `_upsert_record`, `_ledger_record_from_mapping`, and `_record_json` so verdict updates never clear coordinator metadata.
  - From Cursor-Requirements: In the analyze_bugs.py plan section, require _upsert_record to copy all new analytics fields from base unchanged unless the ingest path intentionally refreshes them


### FINDING_12: Chain-edge identities must be canonical and directional
- **Reviewer(s)**: Cursor-dyn-Temporal Analytics Integrity
- **Severity**: minor
- **Concern**: Snapshotting file-intersection and marker edges as undirected or inconsistently ordered pairs can create false Since-last-run deltas when input ordering changes or a report is rerendered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Temporal Analytics Integrity: Define edge id as `(from_issue, to_issue, detector_kind)` with fixed detector direction rules. Store that tuple in snapshots and delta diff tests. Add a rerender idempotency test that permutes input edge order.


### FINDING_13: Predecessor snapshots must precede the active run
- **Reviewer(s)**: Codex-dyn-Temporal Analytics Integrity
- **Severity**: major
- **Concern**: Selecting the newest valid snapshot without constraining it to precede the active run can compare an older run against a later run. That makes Since-last-run deltas and report text dependent on which newer run directories happen to exist, violating rerender idempotency.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Temporal Analytics Integrity: Select the predecessor by the active manifest's deterministic run timestamp or run sequence, requiring its snapshot to precede the active run. For rerenders, use the same predecessor even when later run directories exist, and test rendering an older run after a newer snapshot is present.


### FINDING_1: In-window ledger rows cannot produce marker-chain edges
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Marker-chain detection lacks an evidence path for historical in-window ledger issues that are not selected by the current manifest. If marker references are persisted only for manifest-selected issues, those issues cannot participate in marker edges until they are selected again.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend coordinator metadata for the in-window corpus: persist derived marker_references (and any needed stripped-body hash) on ledger rows during the metadata upsert pass for all canonical in-window issues, not only manifest-selected ones; or document and test an explicit bounded issue-text backfill for ledger rows missing marker_references before marker-edge construction.


### FINDING_2: Canonical analytics selection must preserve ledger append order
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: major
- **Concern**: The planned ledger representation cannot deterministically select the canonical record required by the analytics rules. `load_ledger` collapses records by cache key and discards cross-key/file-order evidence, so equal `updated_at` values or legacy `updated_at=0` rows can select stale fix metadata or verdicts and miscompute chains, churn, chronic zones, and routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an analytics-corpus loader that scans ledger.jsonl in file order, keeps all valid rows grouped by issue, then applies the documented canonical winner; reserve load_ledger for cache-key upserts and ingest paths.
  - From Codex-Arch: Preserve valid append order in the loaded ledger corpus, or persist and load an explicit append sequence, then use it for the specified canonical-record tie-break.


### FINDING_5: Verified-issue membership for deltas is undefined
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: The plan stores and compares `verified_issues` but does not define the predicate used at snapshot time. Different implementations could include evidence-token triage, mechanical-only rows, partial triage, deep completions, or only final verdicts, producing unstable Since-last-run deltas across rerenders.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Define verified once: for example, manifest-selected issues whose current canonical ledger record has evidence-verified triage and/or a completed deep stage for the active cache key. Use that same predicate for run-state storage and Since-last-run rendering.
  - From Cursor-Requirements: Define verified_issues as manifest issue numbers whose canonical record has a final evidence tier of MECH, TRIAGE, or DEEP and is not pending NEEDS_DEEP or not-yet-triaged; pin the rule in run-state schema text and delta tests.


