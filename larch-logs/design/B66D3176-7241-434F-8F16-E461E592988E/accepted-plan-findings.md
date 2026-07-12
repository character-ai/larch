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


