### OOS_1: [OUT_OF_SCOPE] tracking-issue pytest parity coverage is too thin
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-stream-contracts-output.txt, dyn-fail-closed-output.txt, dyn-api-stability-output.txt
- **Severity**: important
- **Concern**: The deleted shell harness coverage was not replaced with plan-equivalent pytest coverage, leaving stream placement, quiet routing, append delegation, marker filters, upsert behavior, and stderr sanitization weakly guarded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.
  - From dyn-stream-contracts-output.txt: Address the concern above.
  - From dyn-fail-closed-output.txt: Address the concern above.
  - From dyn-api-stability-output.txt: Address the concern above.


