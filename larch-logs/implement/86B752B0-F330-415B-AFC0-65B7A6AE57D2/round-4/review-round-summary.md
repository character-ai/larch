# Review Round 4

- Mode: `diff`
- 6 accepted, 3 rejected (2 neutral)

## Accepted Findings

### FINDING_1: ship-pr lint-fix main-agent-required lacks ledger handoff
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `scripts/ship-pr.sh` can continue CI or recovery edits after a lint-fix loop returns `main-agent-required`, without emitting ledger-ready handoff data, clearing stall tracking, or exiting through the escalation path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_12: Tier B sensitive corpus omits raw evidence text
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Tier B sensitive-corpus construction extracts only shaped tokens from several evidence artifacts, so client-specific prose from those files can be repeated in bounded root-cause text without validation failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_13: ci-local-unfixable ledger trigger suffix can be empty
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: A malformed CI job token can produce an empty aggregate suffix, yielding `SHIP_PR_LEDGER_TRIGGER=ci-local-unfixable:` and causing escalation recording to reject the handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_5: forked dry-run success can skip Step 18a.5
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `forked-dry-run` is normalized but not treated as succeeded unless `CI_PASSED=true`, so a successful fork dry-run with escalation evidence can skip the required Step 18a.5 report.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_7: compose-report omits tagged Tool Failure evidence
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `compose-report` can omit tagged `record-escalation Tool Failure` evidence even though Step 18a.5 counts it as escalation evidence, leaving reports incomplete when other evidence writes fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_8: compose-report can emit escalation success without evidence
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `compose-report escalation-success` does not fail closed when ledger, fallback, marker, and tagged Tool Failure evidence are all absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


