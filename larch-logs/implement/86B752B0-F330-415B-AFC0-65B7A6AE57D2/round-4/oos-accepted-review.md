### OOS_5: [OUT_OF_SCOPE] operator-action env writes literal newline escapes
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `stall-recovery-report.sh` writes literal `\n` sequences into operator-action and record-failure env artifacts, so durable KV readers can fail while sentinel-only tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### OOS_6: [OUT_OF_SCOPE] Step 18a.5 evidence gate is prompt-only
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Step 18a.5 evidence and skip logic lacks a mechanical wrapper, so orchestration can skip ledger reads, sentinel writes, or tagged Tool Failure checks without test coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


