# Review Round 5

- Mode: `diff`
- 4 accepted, 3 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Bash lint-fix omits token-report NDJSON append
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-risk-integration-output.txt
- **Severity**: important
- **Concern**: Codex lint-fix sidecars are recorded into the active ledger but not appended to `$IMPLEMENT_TMPDIR/token-report.ndjson`, so committed run-log token batches can omit `codex_lint_fix` spend.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: After the sidecar check, call token append-record --tmpdir "$IMPLEMENT_TMPDIR" then record-vendor-sidecar; warn-not-fail on either failure.
  - From dyn-risk-integration-output.txt: Mirror `skills/design/scripts/design-step2b-drafter.sh:219-227` or `scripts/ship-pr.sh:1469-1477`: after a non-empty `${run_dir}/codex.log.token-record`, call `token append-record --tmpdir "$IMPLEMENT_TMPDIR"` first, then `IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR" python3 … token record-vendor-sidecar`, warn-not-fail on either leg, and keep ingestion independent of `parsed_exit`.


### FINDING_2: Golden fixtures duplicate shipped-default rate legend
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Report-token golden fixtures still pin full default rate legends, duplicating the single intended default-rate snapshot authority and making unrelated render tests fail on future rate corrections.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Inject explicit rates_display in golden tests or scrub the Rates used for display/fallback section from fixtures.
  - From cursor-specialist-testing-output.txt: Scrub or remove per-bucket rate numbers from report_tokens_*_golden.md legends


### FINDING_3: Rebase conflict sidecar ingestion lacks seen-set dedup
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-architecture-output.txt, dyn-code-quality-output.txt
- **Severity**: important
- **Concern**: `make_conflict_launch_fn` calls `ingest_launcher_token_sidecar` without a closure-scoped `seen` set, so repeated ingestion of the same `.token-record` path can double-append NDJSON and active-ledger rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Pass a per-waterfall seen set from make_conflict_launch_fn, matching ci_monitor.py.
  - From dyn-architecture-output.txt: Mirror the CI-monitor pattern: keep a `seen_token_records: set[str]` in the `make_conflict_launch_fn` closure (or per `rebase_and_push` session) and pass it as `seen=`. Extend `test_make_conflict_launch_fn_ingests_external_token_sidecar` to assert `seen` is a `set`, and add a partial-failure retry case like `test_agents.py` already has for CI monitor.
  - From dyn-code-quality-output.txt: Add `seen_token_records: set[str] = set()` inside `make_conflict_launch_fn` and pass `seen=seen_token_records`, mirroring `ci_monitor._make_default_launch_fn`.


### FINDING_5: Lint-fix ingestion harness misses planned assertions
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-risk-integration-output.txt
- **Severity**: important
- **Concern**: `test-lint-fix-loop.sh` does not assert failed Codex sidecar ingestion reaches both active ledger and NDJSON, preserves `MODEL=`, or exports `IMPLEMENT_TMPDIR`, so lint-fix ledger regressions may ship unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add the planned cases to scripts/test-lint-fix-loop.sh and wire append-record in run_codex.
  - From cursor-specialist-testing-output.txt: Extend test-lint-fix-loop.sh case 0b to jq-assert one codex_lint_fix active-ledger row and add MODEL= plus IMPLEMENT_TMPDIR export assertions per plan
  - From dyn-risk-integration-output.txt: Extend the Codex fixture sidecar to include `MODEL=gpt-5.5`, add cases for failed Codex attempts with parseable usage, and assert both one NDJSON row in `$IMPLEMENT_TMPDIR/token-report.ndjson` and one active-ledger row with preserved `model`, matching the Step 2b drafter harness pattern.


