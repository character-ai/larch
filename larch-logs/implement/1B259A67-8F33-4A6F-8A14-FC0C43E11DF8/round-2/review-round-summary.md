# Review Round 2

- Mode: `diff`
- 5 accepted, 2 rejected (2 neutral)

## Accepted Findings

### FINDING_1: Python sidecar append failure suppresses active-ledger ingestion
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `ingest_launcher_token_sidecar` returns after `append-record` fails. That can skip `record-vendor-sidecar`, so live cost ledgers miss usage even when active-ledger recording would succeed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Attempt record-vendor-sidecar after logging append failure; only fail when both paths fail
  - From codex-specialist-correctness-output.txt: Run append-record and record-vendor-sidecar independently and warn on each failure.


### FINDING_16: Relevant-checks misses changed sidecar and model launcher surfaces
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/relevant-checks.sh` maps only the Step 2b drafter harness. Changes to launcher and ingestion paths can pass without stale-sidecar, `MODEL`, direct-ledger, or exactly-once ingestion tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Add direct relevant-check mappings and the plan-required shell harness updates for the changed launcher and ingestion paths.


### FINDING_2: Design auto-fix can record active-ledger rows under implement tmpdir
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Codex plan-autofix writes `codex_plan_autofix` to design NDJSON, but `record-vendor-sidecar` can resolve to inherited `IMPLEMENT_TMPDIR`. Live design costs then omit the usage. Reviewers also noted missing harness coverage for this contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use env -u IMPLEMENT_TMPDIR DESIGN_TMPDIR=... when calling record-vendor-sidecar
  - From cursor-specialist-edge-cases-output.txt: Use env -u IMPLEMENT_TMPDIR DESIGN_TMPDIR=... like design-step2b-drafter.sh.
  - From codex-specialist-edge-cases-output.txt: Invoke record-vendor-sidecar with env -u IMPLEMENT_TMPDIR DESIGN_TMPDIR="$DESIGN_TMPDIR" like design-step2b-drafter.sh.
  - From cursor-specialist-testing-output.txt: Extend the harness to assert one NDJSON row and one active-ledger row for raw=codex_plan_autofix after the tmpdir guard.
  - From codex-specialist-testing-output.txt: Invoke record-vendor-sidecar with env -u IMPLEMENT_TMPDIR DESIGN_TMPDIR="$DESIGN_TMPDIR" and add the planned auto-fix harness assertion.


### FINDING_6: Cursor no-usage outputs create non-empty zero-token sidecars
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Cursor output JSON without `.usage` writes a non-empty zero-token sidecar. `-s` callers then attempt ingestion instead of treating no usage as an empty sidecar.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Only write the token-record when TOTAL > 0; otherwise leave the pre-cleared sidecar empty.


### FINDING_8: Python sidecar dedup marks paths seen before successful ingestion
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-dedup-robustness-output.txt
- **Severity**: important
- **Concern**: `ingest_launcher_token_sidecar` adds paths to `seen` before validating non-empty files and before both ingest steps succeed. Empty first sidecars or failed ingests can suppress later billable usage on stable output paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Only add to seen after both append-record and record-vendor-sidecar succeed, or key seen by path plus mtime/size.
  - From dyn-dedup-robustness-output.txt: Record in `seen` only after both CLI steps succeed (or use a two-phase mark), and roll back `seen` on any early return. Move the empty/missing-file guard above `seen.add`, or only add paths that were actually ingested.


