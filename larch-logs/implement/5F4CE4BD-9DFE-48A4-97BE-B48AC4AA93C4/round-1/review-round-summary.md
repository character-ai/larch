# Review Round 1

- Mode: `diff`
- 9 accepted, 10 rejected (8 neutral)

## Accepted Findings

### FINDING_1: `record()` suppresses `filed-as` rows on partial `/issue` success or missing verification flag
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-dyn-skill-orchestrator-output.txt
- **Severity**: important
- **Concern**: `record()` only writes `filed-as` ledger rows when `issue_verified is True` and `issues_failed == 0`. On partial `/issue` failure (one cluster succeeds, another fails), successfully created issue numbers are not ledgered, so the next run re-verifies and may re-file duplicates. A separate gate path leaves `issue_verified` as `None` when the orchestrator omits `--issue-verified true` after a successful Step 7; no `filed-as` rows are written but `record()` can still exit 0, orphaning real GitHub issues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Map resolved clusters when issue_verified=True even if issues_failed>0; withhold filed-as only for unmapped clusters; keep non-zero exit.
  - From codex-specialist-correctness-output.txt: Resolve and file each cluster independently against issue_map, and reserve the nonzero exit for unresolved clusters only.
  - From codex-specialist-edge-cases-output.txt: decouple mapping from global failure count and write `filed-as` rows for every cluster whose batch index resolved to a number or duplicate-of mapping, while withholding only unmapped clusters.
  - From codex-specialist-testing-output.txt: always walk `issue-cluster-map.json`, commit rows for clusters with resolved issue numbers, and set `UNMAPPED_CONFIRMED` only for confirmed clusters that truly lack a mapping.
  - From dyn-dyn-skill-orchestrator-output.txt: In SKILL Step 8, make `--issue-verified true` mandatory whenever Step 7 ran; in `record()`, fail closed (`rc=1`, `UNMAPPED_CONFIRMED=true`) when non-empty issue stdout shows created/deduped issues but `issue_verified` is not explicitly `True`.


### FINDING_8: Git log options placed after `--` so demotion probe never demotes touched files
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Git log options are placed after `--`, so the demotion probe never demotes touched files. A file modified after `started_at` still stays at full priority and can consume the verify cap instead of being demoted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Move the git log options before -- and fail closed on any nonzero probe result.


### FINDING_9: `_append_tsv` leaves stale `ledger-pending.tsv` when current row set is empty
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `_append_tsv` leaves an existing `ledger-pending.tsv` untouched when the current row set is empty. Reusing a workdir can replay stale pending rows from a previous run into the next `record()` call.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Truncate or recreate ledger-pending.tsv at the start of each run, or rewrite it atomically from the current row set even when empty.


### FINDING_10: `finalize()` silently skips candidates with no ingest-status row
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt, codex-generalist-output.txt
- **Severity**: important
- **Concern**: `finalize()` returns `continue` when `status is None`, so candidates with no durable ingest row are silently ignored instead of receiving a terminal disposition. A successful launch that crashes before `ingest-verdict` writes its row disappears from both `ledger-pending.tsv` and the committed ledger, breaking retry and idempotency; `record()` can still return success if no other failure is present.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Add a defensive terminal disposition for missing ingest-status rows, or persist a launch-attempt marker before launching so finalize can distinguish retryable launch-failed rows from lost ingests.
  - From codex-specialist-testing-output.txt: classify missing rows explicitly as `dismissed:verification-failed` unless a `launch-failed` row exists.
  - From codex-generalist-output.txt: Treat missing ingest status for any prepared candidate as an infra failure: emit/count it as retryable, make `LAUNCH_FAILURES` or an equivalent record flag nonzero, and prevent a successful exit until every candidate has a durable terminal or retryable status.


### FINDING_13: Dirty-tree rejection serialized as synthetic `stale` verdict in sidecar
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: A dirty-tree rejection is serialized as a synthetic `stale` verdict in `verdicts.jsonl`, and `_append_sidecar()` later commits it into the rejected-analysis verdict sidecar. That turns launcher or infra contamination into a false-negative label, so `/voter-calibration` treats a dirty-tree run as if the verifier actually said the finding was stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: keep dirty-tree results out of the verdict sidecar and sidecar reader, and record only the ingest-status disposition for that outcome.


### FINDING_15: `PATH_TOKEN_RE` treats any single backticked word as a repo path
- **Reviewer(s)**: codex-generalist-output.txt
- **Severity**: important
- **Concern**: `PATH_TOKEN_RE` treats any single backticked word as a repo path. A finding body that mentions a code symbol before the real file citation can pin verification to the symbol, causing a real finding to be dropped as `location-mismatch` or `no-file-path`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generalist-output.txt: Restrict arbitrary backtick parsing to path-shaped tokens with an extension, slash, line suffix, or known extensionless filenames. Keep broader single-token acceptance only for `File:` / `Location:` leaders or bare own-line path forms.


### FINDING_17: Reused work dir lets earlier `dismissed:verification-failed` shadow later `filed-as`
- **Reviewer(s)**: dyn-dyn-ledger-recovery-output.txt
- **Severity**: important
- **Concern**: `finalize()` appends verification dispositions to `ledger-pending.tsv`, but confirmed survivors are only written as `filed-as` in `record()`. `record()` merges pending + safe + filed rows and `_write_ledger_atomic()` keeps the first row per `finding_hash`. After a failed verification attempt in a reused `WORK_DIR`, an earlier `dismissed:verification-failed` row can permanently shadow a later `filed-as` row while `RECORD_EXIT_RC=0`, breaking idempotency.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-ledger-recovery-output.txt: Before merge, collapse `ledger-pending.tsv` to one row per `finding_hash` with explicit precedence (for example `filed-as` / `deduped-as` over dismissed rows), or rewrite `ledger-pending.tsv` on each `finalize()` instead of appending. Make `_write_ledger_atomic()` prefer higher-priority dispositions when duplicates exist, and add a regression test that re-finalizes and re-records after a failed-then-successful verification in the same work dir.


### FINDING_18: `_append_sidecar()` appends duplicate rows on `record()` retry
- **Reviewer(s)**: dyn-dyn-ledger-recovery-output.txt
- **Severity**: important
- **Concern**: `_append_sidecar()` always appends to `larch-logs/rejected-analysis-verdicts.tsv` on every `record()` call with no `finding_hash` deduplication. Retried `record()` after partial failure can double-count false-negative labels in `/voter-calibration`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-ledger-recovery-output.txt: Mirror the committed ledger pattern: read existing sidecar rows, merge by `finding_hash` (last wins or first wins, but pick one), then atomically replace the file. Skip append when the hash is already present unless the verdict changed.


### FINDING_19: `record()` trusts CLI `--launch-failures` instead of deriving from ingest status
- **Reviewer(s)**: dyn-dyn-ledger-recovery-output.txt
- **Severity**: important
- **Concern**: `record()` sets `rc=1` for launch failures only when the orchestrator passes `--launch-failures N`; it does not re-count `launch-failed` rows from `ingest-status.jsonl`. A missed or stale `--launch-failures 0` after `finalize` reported `LAUNCH_FAILURES>0` can yield `RECORD_EXIT_RC=0` while candidates remain unledgered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-ledger-recovery-output.txt: Derive `launch_failures` inside `record()` from `status_map` (count of `launch-failed` rows for candidates still in `candidates.json`) and treat `max(cli_value, derived_value)` as authoritative for exit-code gating.


