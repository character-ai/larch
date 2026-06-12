### OOS_2: [OUT_OF_SCOPE] admission fail-opens blocker helper failures
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Admission treats blocker helper subprocess failures as empty blockers. An import, source, dispatcher, or `blocker all-open` failure can let a DESIGNED issue pass without blocker enforcement. Return `ADMISSION_ERROR=blocker all-open failed` and exit 2 for blocker subprocess nonzero; keep fail-open only for degraded GitHub reads inside a successful blocker call.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


