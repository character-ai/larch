### OOS_1: [OUT_OF_SCOPE] risk-integration: `docs/point-competition.md` still states old any-YES-high `+2` rule
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-dyn-rubric-sync-output.txt
- **Severity**: important
- **Concern**: Canonical operator doc `docs/point-competition.md` (line 11; nearby prose at line 16) still says `+2` when any YES-voter panel severity is `blocker` or `major`. The scoring commit updated `skills/shared/voting-protocol.md` and reviewer competition notices but not this doc. Operators reading `point-competition.md` will misunderstand live `+2` rules relative to updated runtime prose or a restored strict-majority contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-rubric-sync-output.txt: Update the `+2` row (and nearby prose at `docs/point-competition.md:16` if needed) to the same unanimous-all-high language now used in `skills/shared/voting-protocol.md:191`, or to strict-majority language if the plan semantics are restored.


