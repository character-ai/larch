# Review Round 2

- Mode: `diff`
- 15 accepted, 7 rejected (5 neutral)

## Accepted Findings

### FINDING_11: record-escalation can concatenate ledger rows
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `record-escalation` can strip a trailing newline before appending. Multiple escalation records can land on one physical ledger line, causing later parsing to miss or merge events.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_12: Python internal lint-fix handoffs use inconsistent site and trigger tokens
- **Reviewer(s)**: codex-specialist-correctness-output.txt, dyn-kv-contract-output.txt
- **Severity**: important
- **Concern**: The Python ship-pr internal lint-fix path can record generic or inconsistent site and trigger metadata compared with bash and the exit matrix. The same failure can produce different ledger rows and escalation titles by driver.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From dyn-kv-contract-output.txt: Address the concern above.


### FINDING_13: Tier B ledger rendering does not sanitize site and trigger
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Tier B rendering can print `site` and `trigger` directly from ledger rows. A malformed tmpdir ledger can expose a client path, branch, or other unsafe token in chat output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_15: Python CI handoff ledger omits the failure-detail log
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-ledger-chain-output.txt
- **Severity**: important
- **Concern**: Python CI handoffs can write a detail log but omit `ledger_failure_detail_log` from the JSON ledger envelope. Escalation rows then lack the evidence pointer needed for Tier A reports and root-cause analysis.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.
  - From dyn-ledger-chain-output.txt: Address the concern above.


### FINDING_16: Fallback ledger and marker writes lack containment checks
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Fallback escalation ledger writes and record-failure marker writes can skip symlink or tmpdir containment validation. A symlinked path under `IMPLEMENT_TMPDIR` could redirect writes outside the session tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_17: Step 5 record-escalation failures are swallowed
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-robustness-output.txt
- **Severity**: important
- **Concern**: `scripts/run-step5-review.sh` can suffix `record-escalation` with `|| true`. Validation or helper failure can drop escalation rows without fallback evidence, tagged Tool Failure output, or operator signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-robustness-output.txt: Address the concern above.


### FINDING_18: Bash ship-pr emits ledger-ready data for non-handoff bails
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Bash `ship-pr` can emit escalation ledger-ready KVs for operator or user-input bails that are not script-to-main-agent handoffs. Step 18a.5 can file false escalation-success reports.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_19: compose-report can mark issue input as filed too early
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `compose-report` can report Tier A issue-input composition as filed before an issue is actually filed or normalized. A filed sentinel can be written even if `/larch:issue` is skipped or fails later.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_2: Tier B projection omits version and run identifiers
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Tier B chat output can omit `larch_version` and `RUN_ID` even though they are allowlisted and required for traceability. Consumer reports become harder to correlate with runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_21: agent-lint misses the ci-decide markdown sibling
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/test-ci-decide.md` is not excluded beside the Makefile-only shell harness. CI can fail on the orphan sibling contract file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_22: compose-report custom attempts path lacks containment validation
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `compose-report` can write a missing custom attempts file without validating tmpdir containment. A caller can pass an absolute path outside `IMPLEMENT_TMPDIR` and create or overwrite it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_24: Bash exit-3 handoffs do not clear stall tracking
- **Reviewer(s)**: dyn-robustness-output.txt
- **Severity**: important
- **Concern**: Bash exit-3 ledger handoffs can update bail and ledger fields without setting `STALL_TRACKING=false` and `STALL_STEP=""`. Step 18a.5 can skip escalation-success reporting because a stall layer remains true.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-robustness-output.txt: Address the concern above.


### FINDING_3: Tier B validation does not derive the sensitive corpus from all evidence
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Tier B validation can scan only the prompt-state supplement instead of the full pinned evidence set. Bounded prose can echo client data from plan or execution artifacts and still be published.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_4: normalize-outcome ignores in-memory stall tracking
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `normalize-outcome` can ignore the in-memory `STALL_TRACKING` layer from `step-18a-gate`. Step 18a.5 can file an escalation during an active stall when disk layers are false.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_5: Tier B validator rejects allowlisted operational tokens
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Tier B sensitive-token validation can reject valid bounded prose when allowlisted operational values appear in corpus lines or `ALL_CAPS=value` patterns. Valid reports can fail composition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


