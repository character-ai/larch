### OOS_1: [OUT_OF_SCOPE] Per-item baseline warnings flood stderr/CI logs
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Check mode warns once per baselined violation (~1125 lines every run). Pre-commit and `py-lint` stderr become very noisy and can obscure real hook failures; unlike complexity-baseline silent grandfathering. Emit one summary line (N baselined warnings) unless `--verbose`, or otherwise match complexity-baseline summary-only silence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


