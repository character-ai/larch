### FINDING_3: Missing round_artifact_included unit exclusions
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Unit-level `round_artifact_included` tests do not directly pin exclusion of `codex.events.jsonl` and `foo.events.jsonl`; only `coder-codex.events.jsonl` is covered directly. A targeted allowlist or glob regression could fail less clearly or slip past fast unit coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.



