### OOS_11: [OUT_OF_SCOPE] retired-script lint misses basename-only stale prose
- **Reviewer(s)**: dyn-cutover-completeness-output.txt
- **Severity**: nit
- **Concern**: `make lint-retired-scripts` matches full repo-relative paths only, so basename-only stale script names in prose can pass lint while still breaking operator workflows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cutover-completeness-output.txt: Address the concern above.


### OOS_12: [OUT_OF_SCOPE] audit-runs skill still names deleted helpers and docs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-testing-output.txt, dyn-cutover-completeness-output.txt
- **Severity**: important
- **Concern**: `.claude/skills/audit-runs/SKILL.md` still references retired shell helpers, jq scan filters, harnesses, and contract docs. Agents following the documented flow can invoke missing files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-testing-output.txt, dyn-cutover-completeness-output.txt: Address the concern above.


### OOS_13: [OUT_OF_SCOPE] classify-bump rules doc names retired bash surfaces
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-cutover-completeness-output.txt
- **Severity**: latent
- **Concern**: `.claude/skills/release/scripts/classify-bump.md` still describes `classify-bump.sh` and `release-prepare.sh` as the implementation or consumers instead of the Python release commands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-cutover-completeness-output.txt: Address the concern above.


