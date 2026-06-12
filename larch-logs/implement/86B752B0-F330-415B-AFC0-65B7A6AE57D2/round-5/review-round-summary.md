# Review Round 5

- Mode: `diff`
- 11 accepted, 3 rejected (3 neutral)

## Accepted Findings

### FINDING_10: Fallback-only escalation evidence is not fully rendered or tested
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Fallback escalation rows and record-failure-marker-only evidence may satisfy evidence checks but fail to render useful site or trigger details, or may skip successful Tier B reporting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Parse fallback rows like canonical ledger rows and use fallback site/trigger for title and body when canonical ledger is empty.
  - From cursor-specialist-testing-output.txt: Add compose-report fixtures with only fallback TSV or only record-failure marker; assert successful Tier B print.


### FINDING_11: Generic Tool Failures are not tested as invalid escalation-success evidence
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Untagged generic Tool Failure entries could be misread as escalation evidence without a negative test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add execution-issues.md with generic Tool Failure only; assert compose-report escalation-success fails closed.


### FINDING_12: Tier A raw bail handling lacks redaction and verbatim-bail coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Tier A `BAIL_REASON_RAW` compose behavior is not tested for verbatim bail intent and secret redaction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add Tier A issue-input compose test with BAIL_REASON_RAW and a secret token; assert verbatim bail intent and redacted output.


### FINDING_13: terminal-failure compose lacks missing-classification fail-closed coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Missing `classification.env` on terminal-failure compose is untested, so the fail-closed requirement could regress.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add terminal-failure compose without classification file; assert exit 1 with validation error.


### FINDING_14: Step 5 CMAR success path lacks canonical ledger ownership tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-architecture-output.txt
- **Severity**: important
- **Concern**: The coder-main-agent-required success path lacks tests that prove exactly one canonical ledger row is created and no duplicate prompt-side KVs are emitted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add CMAR success spy; assert one ledger line with correct site/trigger tokens.
  - From codex-specialist-testing-output.txt: Add a success-path test asserting exactly one canonical ledger row.
  - From dyn-architecture-output.txt: Add a success-path test asserting **no** `STEP5_REVIEW_LEDGER_*` lines and exactly one ledger row after successful `record-escalation`, so a future refactor cannot reintroduce duplicate prompt-side recording.


### FINDING_19: Python and Bash ship-pr handoff token normalization diverge
- **Reviewer(s)**: dyn-architecture-output.txt
- **Severity**: important
- **Concern**: Bash normalizes RCC and Step 6 main-agent-required lint-fix handoffs to `ship-pr-internal` / `ship-pr-internal-lint-fix`, while Python can emit phase-specific site and trigger tokens.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-architecture-output.txt: Centralize handoff normalization in one helper used by `checks.py`, `lint-fix-loop.sh`, and bash ship-pr (or map merge/per-job `main-agent-required` to the same `ship-pr-internal` / `ship-pr-internal-lint-fix` pair bash uses), and add parity tests for merge-phase handoffs.


### FINDING_2: record-escalation can fail without durable fallback evidence
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `record-escalation` validation or canonical ledger write failures can leave no durable fallback marker or ledger evidence for Step 18a.5.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Write marker file whenever ESCALATION_RECORD_FAILURE_MARKER is emitted, or fail closed when persistence is impossible
  - From codex-specialist-edge-cases-output.txt: Route non-writable regular canonical ledger files through the fallback/marker path; keep hard rejection for outside, symlink, non-regular, or malformed paths.
  - From cursor-specialist-testing-output.txt: Add fixture forcing canonical ledger append failure; assert fallback file or marker plus tagged Tool Failure.


### FINDING_22: run-step5-review parses status weaker than the documented Step 5 KV parser
- **Reviewer(s)**: dyn-code-robustness-output.txt
- **Severity**: important
- **Concern**: `scripts/run-step5-review.sh` reads the first whole-line `STEP5_REVIEW_STATUS`, so multi-KV lines, later terminal envelopes, or whitespace can skip ledger handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-code-robustness-output.txt: Reuse the same helper as `review-implement-step5-loop.sh` (`step5_parse_kv_tokens`) or port `step5_get_kv` / last-match semantics from `test-review-and-fix.sh`; trim whitespace; add a harness case that asserts ledger KVs are emitted when `STEP5_REVIEW_STATUS` appears only on the final envelope line amid other stdout noise.


### FINDING_7: record-escalation stdout can pollute the Step 5 review KV stream
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `record-escalation` can emit extra stdout lines into the preserved review stream, causing callers that expect only child KVs to misparse output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Capture or redirect record-escalation stdout; emit only fallback STEP5_REVIEW_LEDGER_* KVs when prompt-side recording is needed


### FINDING_8: Legacy report subcommands remain callable
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Legacy `bug-body`, `bug-comment`, and `issue-input-file` subcommands can still generate the old report surface without mandatory root-cause or Tier B validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Remove the subcommands from dispatch or gate them behind explicit test-only compatibility
  - From codex-specialist-edge-cases-output.txt: Remove these from the runtime dispatcher or gate them behind an explicit test-only environment variable.


### FINDING_9: Tier A compose-report emits a status outside the documented enum
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Tier A compose-report emits `STALL_RECOVERY_REPORT_STATUS=composed`, but downstream contracts expect documented statuses such as `filed`, `printed`, `skipped_operator_action`, or `failed`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Emit a documented post-filing status or update the contract and callers to handle composed explicitly
  - From codex-specialist-testing-output.txt: Align the status contract and tests, or add a documented post-filing normalization step.


