### OOS_1: [OUT_OF_SCOPE] Admission blocker helper failures fail open
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Admission treats non-zero blocker helper failures as no blockers in resume and non-resume paths. A blocked designed issue can pass when `python/cli.py blocker all-open` cannot import, run, or query blockers. The merged source includes one out-of-scope note that frames this as a historical fail-open trade-off.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


