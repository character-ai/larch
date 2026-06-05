### FINDING_25: architecture: python/ship.py
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] python/ship.py and python/test_ship.py were modified in round-1 review but are not in the plan file list for pause/resume WI1-WI3. The branch bundles unrelated ship-pr resume/OOS-gate logic with the pause/resume fix, breaking plan-to-diff traceability and review scope. Split ship.py changes to a separate PR or extend the plan and acceptance criteria to cover them explicitly.
- **Suggested revision**: Address the concern above.



