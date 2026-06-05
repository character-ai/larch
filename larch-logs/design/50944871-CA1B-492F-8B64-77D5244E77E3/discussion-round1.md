## Decision 1: Exclude vs include raw plan-review reviewer transcripts
- **Question**: Should design-log publish exclude or include raw plan-review reviewer transcripts in the committed log (`larch-logs/design/<run-id>/`)?
- **Resolution**: EXCLUDE — drop raw plan-review reviewer transcripts and their `.meta`/`.json`/`.cap-hit` sidecars from the top-level commit. Consistent with the round-N staging gate and the implement-log policy (#3504); `findings.md` / `voting-tally.md` remain the canonical aggregate.
- **Source**: user

## Decision 2: Scope/breadth of the exclusion
- **Question**: Should the exclusion cover only plan-review reviewer outputs, or all raw reviewer transcripts (sketches, dialectic, assessor)?
- **Resolution**: Plan-review outputs only — exclude `codex-primary-plan-*-output.txt`, `cursor-plan-*-output.txt`, and `claude-plan-*-output.txt` (static + dynamic), each with `.meta`/`.json`/`.cap-hit` sidecars. HARD-only sketch / dialectic / plan-quality-assessor transcripts are explicitly OUT of scope for this issue (a reviewer may file them as OOS).
- **Source**: user

## Decision 3: Secondary defect (dead lib pattern + fictional test fixtures)
- **Question**: How to handle the dead `codex-plan-*-output.txt` pattern and fictional test fixtures?
- **Resolution**: Fix the dead pattern in `lib-design-round-artifacts.sh` (`codex-plan-*` → `codex-primary-plan-*`); replace fictional fixtures (`codex-plan-edge-output.txt`, `dyn-cursor-plan-foo-output.txt`) with real producer names in both `test-lib-design-round-artifacts.sh` and `test-design-log-publish.sh`.
- **Source**: codebase + issue

## Hard constraints (must not break)
- `findings.md`, `findings-classification.tsv`, `voting-tally.md`, accepted/rejected/oos artifacts, `ballot.txt`, `plan.txt` stay committed (canonical aggregate).
- Vote outputs (`*-vote-output.txt`) stay committed — the round-N policy (`lib-design-round-artifacts.sh`) includes them; do not exclude.
- The round-N allowlist gate's observable behavior for real producers is unchanged: `codex-primary-plan-*` is already excluded via the catch-all today; the lib edit only removes dead code and makes the explicit exclusion match reality.
- Pattern additions must not collide with canonical filenames (verified: no canonical artifact begins with `cursor-plan-`, `codex-primary-plan-`, or `claude-plan-`).
