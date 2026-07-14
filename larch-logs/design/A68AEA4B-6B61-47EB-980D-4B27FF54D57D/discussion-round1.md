## Decision 1: Reviser-tier implementation
- **Question**: New dedicated agent vs. adapting existing claude-implementer for plan editing?
- **Resolution**: Add `MODE=plan-revise` to existing `agents/claude-implementer.md` and `agents/_implementer-base.md`. No new agent file.
- **Source**: user

## Decision 2: Exception block enforcement point
- **Question**: Add `--allow-exception` to `_persist_design_assessment_main` (mirroring /implement), or enforce only at publish time?
- **Resolution**: Both: persist-time (add `--allow-exception` to `_persist_design_assessment_main` in `architectural_guidelines.py`) AND publish-time (`design_publish.py` checks exception block when state=deviation).
- **Source**: user
