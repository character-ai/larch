### OOS_1: [OUT_OF_SCOPE] Missing resume@* router-flag OR-merge coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Existing router-flag merge coverage exercises already-planned paths but not `resume@*`, so a regression in pause/resume OR-merging newly supplied flags such as `--per-round-approval` could slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] design-publish handoff docs still describe old parsing contract
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/design-publish.md` still documents the old `_publish_out` / file-first / manual stdout merge handoff rather than the new stdout-file capture, `read-result-env.sh` fallback, rc=3 stdout-authority, and WARN replay contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


