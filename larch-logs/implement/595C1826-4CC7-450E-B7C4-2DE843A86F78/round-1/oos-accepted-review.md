### OOS_1: [OUT_OF_SCOPE] code-quality
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 1. **code-quality** — `python/research_eval.py:201` — `_diag` reject lines help debugging but only go to the diagnostic stream; they do not surface in `execution-issues.md` or collector `NOT_SUBSTANTIVE` breadcrumbs. The plan’s open question about louder drop visibility was not implemented. Out of scope for the pinned defects but worth a follow-up.
- **Suggested revision**: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] **Open question 3 from the issue** (louder `NOT_SUBSTANTIVE` aggregation during runs) is not addressed in this branch; drops still surface only via collector / `execution-issues.md`.
- **Reviewer**: dyn-migration-parity-output.txt
- **Concern**: - **Open question 3 from the issue** (louder `NOT_SUBSTANTIVE` aggregation during runs) is not addressed in this branch; drops still surface only via collector / `execution-issues.md`.
- **Suggested revision**: Address the concern above.


