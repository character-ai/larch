### FINDING_2: Go/no-go recommendation metric is undefined
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The aggregator emits both `saved_bytes` and `saved_tokens`, but the plan never specifies which aggregate drives `recommendation=go-design-validator-extension`. Mixed-sign rows or divergent byte/token estimates can therefore produce different go/no-go decisions from the same committed data.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin one rule in tokens.py and docs/run-logs.md, for example recommendation from sum(saved_tokens) with saved_bytes reported alongside, and add an aggregator test where byte and token totals disagree so the chosen metric is enforced.
  - From Cursor-Innovation: Pin one field (recommendation=go only when sum(saved_tokens)>0, else no-go), document it in docs/run-logs.md, and test the tie case explicitly
  - From Cursor-Pragmatic: Define one rule in measure_checks_digest_savings(), docs, and tests: e.g. go iff sum(saved_tokens) > 0 across valid rows; report byte totals for diagnostics only
  - From Cursor-Requirements: Pin the recommendation to sum(saved_tokens) > 0 (with sum(saved_tokens) <= 0 as no-go), document that rule in measure_checks_digest_savings() and docs/run-logs.md, and add an aggregator test that fails if bytes-positive/token-negative rows recommend go


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_3: Measurement scanner may read the wrong repo root
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: The new measurement command risks resolving `larch-logs` relative to the plugin checkout instead of the current consumer git repository, which would miss committed `checks-digest-sizes.tsv` rows and report insufficient data even when real data exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Specify that measure_checks_digest_savings resolves the current git repository root, matching report-tokens scan behavior, before scanning larch-logs; do not use the module __file__ root for this measurement.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: [OUT_OF_SCOPE] Second locked-TSV append implementation beside tokens._locked_tsv_append
- **Description**: [OUT_OF_SCOPE] Second locked-TSV append implementation beside tokens._locked_tsv_append. Scenario: Plan copies panel-prompt-sizes flock style inline instead of reusing tokens._locked_tsv_append, inviting divergent lock timeout and warning text
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: python/larch/implement/checks_run_relevant.py:1018-1037
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_2: [SCOPE-REDUCTION] Append-mode `checks-digest-sizes` batch registry is unused by the direct locked-TSV writer
- **Description**: [SCOPE-REDUCTION] Append-mode `checks-digest-sizes` batch registry is unused by the direct locked-TSV writer. Scenario: The writer appends `checks-digest-sizes.tsv` in-process and `run-log commit` copies the full run tree, so the batch registry, its tests, and `run-log-batches.md` edits add synchronized surface with no runtime consumer
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/report/run_log_batch.py:43-74
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_3: [SCOPE-REDUCTION] Append-mode `checks-digest-sizes` batch registry duplicates the direct locked-TSV writer
- **Description**: [SCOPE-REDUCTION] Append-mode `checks-digest-sizes` batch registry duplicates the direct locked-TSV writer. Scenario: Telemetry is written inside `_write_failure_digest_from_redacted` via locked append, not `run-log append`, so the batch slug plus `test_run_logs.py` registry coverage adds a second schema surface with no runtime consumer and extra sync work
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/larch/report/run_log_batch.py
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

