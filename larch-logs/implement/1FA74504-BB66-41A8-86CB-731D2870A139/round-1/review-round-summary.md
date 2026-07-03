# Review Round 1

- Mode: `diff`
- 8 accepted, 6 rejected (0 neutral)

## Accepted Findings

### FINDING_1: JSONL identities must be round-scoped
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-calibration-data
- **Severity**: important
- **Concern**: JSONL identity handling can collapse implement/review findings across rounds when `finding_hash` is absent, so restarted `FINDING_N` labels are merged and accepted findings are undercounted on gc-slimmed runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-calibration-data: Pass skill into `_parse_jsonl_source` / `_json_identity` and, for `implement` and `review`, default to `{round_num}:{finding_id}` unless a non-empty `finding_hash` is present. Reserve `id:` / `hash:` collapse for design or for rows with a genuinely stable cross-round identifier. Add a regression test mirroring `test_implement_identity_restarts_each_round` but through `review-findings-full.jsonl`.


### FINDING_3: Explicitly reject out-of-scope spellings in row scope checks
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: important
- **Concern**: `_row_in_scope()` accepts `out_of_scope` / `out-of-scope` rows as in-scope, which can let rejected design or review rows inflate the realized tier.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_4: Malformed-only JSONL should be unparseable
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: important
- **Concern**: JSONL fallback parsing can treat files with only malformed lines as parseable, so broken inputs enter the matrices instead of being classified as unknown.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_5: Missing verdict sidecar should render n/a
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: important
- **Concern**: When the rejected-analysis sidecar is missing, the run-level confirmed count is rendered as zero instead of unknown, which misstates under-rating burden.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_7: Join sidecar burden by finding identity
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-calibration-data
- **Severity**: important
- **Concern**: Under-rating burden is aggregated at the run level instead of being joined on the specific round/finding identity, so confirmed false negatives can be attributed to the wrong miss.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-calibration-data: Build a per-run sidecar lookup keyed by `(round_num, finding_id)` (and `finding_hash` when present), join against `classification.accepted_identities` when rendering under-rating misses, and count only `verdict=confirmed` rows that match an accepted identity for that miss row’s burden column.


### FINDING_8: Count sidecar rows without finding_hash
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: Confirmed verdict rows lacking `finding_hash` are silently dropped, so some sidecar evidence never contributes to burden annotations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


### FINDING_11: Validate JSONL phases explicitly and count unsupported rows as degraded
- **Reviewer(s)**: codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: important
- **Concern**: JSONL fallback can default missing phases to `code-review` and silently ignore unsupported phases, so broken fallback rows look valid and degraded-input counts stay clean.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Require an explicit allowed phase, bump a degraded counter for missing/unsupported values, and skip those rows before acceptance logic
  - From codex-specialist-testing: Address the concern above.


### FINDING_14: Skip drift rows without parseable timestamps
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: important
- **Concern**: The drift table folds missing or unparsable `started_at` values into an unknown month bucket instead of excluding them or rendering `n/a`, which distorts month distribution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.


