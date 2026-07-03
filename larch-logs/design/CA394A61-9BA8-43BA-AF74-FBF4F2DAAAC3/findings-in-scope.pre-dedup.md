### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/SKILL.md:66-77
- **Concern**: Review checks failures never reach committed checks-digest-sizes.tsv. Scenario: Standalone /review runs checks at Step 3e with --tmpdir $REVIEW_TMPDIR before Step 4 creates larch-logs/review/<RUN_ID>/ via review log-phase and run-log commit. The plan writer only appends when exactly one run directory already exists and explicitly skips when none exists, so every review-step3e digest succeeds at runtime but produces zero committed rows. The issue wires digest in both implement and review skills and expects organic failure samples from committed logs; review-only failures cannot contribute to the five-sample threshold or bias the measurement toward implement.
- **Proposed resolution**: Add a minimum-change review path in checks_run_relevant.py: when canonical_tmp is a claude-review-* session and a valid RUN_ID is available from session env, call run-log init (or equivalent single-run-dir creation) for skill review before locked TSV append instead of requiring a pre-existing tree. Alternatively defer one count-only row to a pending file under relevant-checks and merge it during review Step 4 before run-log commit; document the chosen path in docs/run-logs.md.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/tokens.py
- **Concern**: Go/no-go recommendation metric is still undefined. Scenario: The plan requires aggregate saved_bytes and saved_tokens totals plus recommendation go-design-validator-extension when savings are positive and no-go when zero or negative, but never states whether positive means sum(saved_tokens) > 0, sum(saved_bytes) > 0, both, or a per-row majority. Two correct implementations from the same committed rows can disagree when byte and token estimates diverge or when negative per-row saved_tokens offset positive saved_bytes.
- **Proposed resolution**: Pin one rule in tokens.py and docs/run-logs.md, for example recommendation from sum(saved_tokens) with saved_bytes reported alongside, and add an aggregator test where byte and token totals disagree so the chosen metric is enforced.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/report/run_log_batch.py
- **Concern**: [SCOPE-REDUCTION] Append-mode batch registry has no producer. Scenario: Omit run_log_batch.py, docs/run-log-batches.md, and test_run_logs.py registry work unless the telemetry writer calls run-log append. The plan writes checks-digest-sizes.tsv via direct locked append in checks_run_relevant.py, so the batch entry is a second schema declaration with no runtime consumer and must stay synchronized manually.
- **Proposed resolution**: Drop the checks-digest-sizes batch registration and related docs/tests from this change, or switch the writer to run-log append --batch checks-digest-sizes and delete the direct locked-TSV path.



### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/report/tokens.py:1602
- **Concern**: measure_checks_digest_savings lacks a consumer-repo root contract. Scenario: The new CLI is registered under the plugin's python/cli.py, but tokens.py currently has _repo_root() bound to the plugin checkout. If the new scanner follows that local pattern, an installed plugin invoked from a consumer repo will scan the plugin checkout's larch-logs instead of the consumer run logs where checks-digest-sizes.tsv was committed, so it can report insufficient data forever despite real rows.
- **Proposed resolution**: Specify that measure_checks_digest_savings resolves the current git repository root, matching report-tokens scan behavior, before scanning larch-logs; do not use the module __file__ root for this measurement.



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/SKILL.md:66-79
- **Concern**: python/larch/implement/checks_run_relevant.py:1018-1037. Scenario: [SCOPE-REDUCTION] Standalone /review checks-digest telemetry cannot land under the unique-run-dir gate
- **Proposed resolution**: /review runs checks at Step 3e before Step 4 creates larch-logs/review/<RUN_ID>/; the writer skips when no unique run directory exists, so every standalone review failure omits rows while done criteria still claim /review accrual Drop review from telemetry targets, GC keep, docs, and done criteria; implement-only failures are enough for the 5-sample gate. If review must stay, add an explicit Step 4 flush after run-log init instead of writing at Step 3e



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/tokens.py
- **Concern**: Go/no-go rule still undefined on which signed aggregate drives recommendation. Scenario: Plan says positive savings vs zero or negative but does not pin saved_bytes sum, saved_tokens sum, or both; mixed-sign rows can yield positive bytes and negative tokens (or vice versa) and produce different go/no-go outcomes
- **Proposed resolution**: Pin one field (recommendation=go only when sum(saved_tokens)>0, else no-go), document it in docs/run-logs.md, and test the tie case explicitly



### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/report/run_log_batch.py:43-81
- **Concern**: [SCOPE-REDUCTION] checks-digest-sizes run-log batch registry has no runtime consumer. Scenario: Telemetry is written by direct locked TSV append in checks_run_relevant; run-log commit copies the whole run tree, so the append-mode batch entry plus registry/docs/tests add sync surface with no behavioral gain
- **Proposed resolution**: Omit run_log_batch.py, test_run_logs.py, and docs/run-log-batches.md changes unless a run-log append producer is added in the same PR



### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/SKILL.md:66-67
- **Concern**: Standalone `/review` checks failures skip digest-size telemetry because the run-log tree does not exist yet. Scenario: `/review` runs `checks run-relevant` at Step 3e, but `larch-logs/review/<RUN_ID>/` is only created at Step 4 `run-log commit`; the plan's "skip when no run directory" rule treats that as a permanent skip, so review failures never append `checks-digest-sizes.tsv` rows despite the done criteria requiring both implement and review samples
- **Proposed resolution**: In `checks_run_relevant.py`, when skill is inferable from `site` (e.g. `review-step3e`) and `RUN_ID` is slug-valid, create `canonical_tmp/larch-logs/review/<RUN_ID>/` if absent and append there; keep skip-only for ambiguous multi-run-dir cases, not for "not yet initialized"



### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/tokens.py
- **Concern**: Go/no-go recommendation metric is undefined beyond "positive" vs "zero or negative" aggregate totals. Scenario: The issue scopes a token delta, but the plan does not say whether `recommendation=go-design-validator-extension` uses `sum(saved_tokens)`, `sum(saved_bytes)`, or both; byte and token estimates can disagree on small logs, producing inconsistent go/no-go decisions from the same rows
- **Proposed resolution**: Define one rule in `measure_checks_digest_savings()`, docs, and tests: e.g. `go` iff `sum(saved_tokens) > 0` across valid rows; report byte totals for diagnostics only



### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/SKILL.md:66 / python/larch/implement/checks_run_relevant.py
- **Concern**: Done criteria require `/review` checks failures to accrue rows, but the plan's skip-when-no-run-dir rule blocks every review failure path. Scenario: Standalone `/review` runs `checks run-relevant` at Step 3e (`skills/review/SKILL.md` line 66) before Step 4 creates `larch-logs/review/<RUN_ID>/`; nested `/review` uses `$REVIEW_TMPDIR` while committed logs live under `$IMPLEMENT_TMPDIR/larch-logs/implement/`. The plan edge case says skip when no run-log dir exists, so review digests never get a committed `checks-digest-sizes.tsv` row despite the done criterion
- **Proposed resolution**: Either narrow done criteria to implement-only (minimum change if five implement samples suffice) or add a minimal review path: e.g. slug-valid `run-log init` before Step 3e, or buffer counts under `$REVIEW_TMPDIR` and append once the review run tree exists at Step 4



### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/tokens.py
- **Concern**: Go/no-go rule does not name the token metric that drives the recommendation. Scenario: The issue acceptance criterion is a token delta between digest and redacted log. The plan emits both `saved_bytes` and `saved_tokens` aggregates but defines go only as "positive savings", so one implementation could gate on byte totals and another on token totals and reach different go/no-go outcomes on the same rows
- **Proposed resolution**: Pin the recommendation to `sum(saved_tokens) > 0` (with `sum(saved_tokens) <= 0` as no-go), document that rule in `measure_checks_digest_savings()` and `docs/run-logs.md`, and add an aggregator test that fails if bytes-positive/token-negative rows recommend go



