## Proposed Design Outline

### Goals
- Add a two-tier fix ladder for adverse Gate C outcomes (`violation`/`deviation`) in `/design`, mirroring the #7193 ladder for `/implement`.
- Implement the reviser tier as `MODE=plan-revise` in `larch:claude-implementer` (second operator-approved Gate C carve-out).
- Add guideline exception block machinery: `--allow-exception` flag on `persist-design-assessment` (persist-time) and publish-gate check in `design_publish.py`.

### Non-goals
- Changing what Gate C assesses (invariant/guideline scope and criteria unchanged).
- Changing plan-review, drafters, voting, or any step other than Gate C and its direct callers.
- `/implement` architectural assessments (covered by #7193/#7216).

### Approach sketch
- Extend `approval-gates-gate-c.md`: after assessor authoring, on adverse outcome run tier-1 subagent (plan-revise mode) → re-assess → if still adverse, run tier-2 main agent → re-assess → hard-stop (invariant) or exception-block persist (guideline).
- Add `MODE=plan-revise` to `agents/claude-implementer.md` and `agents/_implementer-base.md`; register in `AGENTS.md` as second operator-approved Gate C carve-out.
- Add `--allow-exception` flag to `_persist_design_assessment_main` in `architectural_guidelines.py` + tests; parser must track fenced-code-block state when scanning for `Exception:` lines (G-Md-3).
- Check `deviation + no exception block` in `design_publish.py` and add tests in `test_design_publish.py`.
- Update pause snapshot allowlist in `test_design_pause.py` to include new tier-counter and exception-block session files (I-Pause-1).
- Update `skills/design/SKILL.md` step 4b with new ladder reference prose.

### Surfaces in scope
- `skills/design/SKILL.md` (firm)
- `skills/design/references/approval-gates-gate-c.md`
- `agents/claude-implementer.md`
- `agents/_implementer-base.md`
- `AGENTS.md`
- `python/larch/core/architectural_guidelines.py`
- `python/tests/core/test_architectural_guidelines.py`
- `python/larch/design/design_publish.py`
- `python/tests/design/test_design_publish.py`
- `python/tests/design/test_design_pause.py` (pause snapshot allowlist for new session artifacts)

### Open questions
- None.
