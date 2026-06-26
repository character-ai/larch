## Decision 1: Which grounding idea to implement
- **Question**: Force plan citation, self-consistency ensemble, or both?
- **Resolution**: Force plan citation — require the voter to quote the exact plan line before voting. Prompt-only change to rendering.py; no infrastructure changes.
- **Source**: user

## Decision 2: Necessity gate scope
- **Question**: Fix only the voter archetype, or also revise reviewer-templates.md Necessity gate?
- **Resolution**: Fix both — add a plan-mandated-deliverable carve-out to the Necessity gate in reviewer-templates.md, then regenerate the affected reviewer agents (reviewer-plan-fidelity.md, code-reviewer.md).
- **Source**: user

## Decision 3: Threshold carve-out
- **Question**: Should plan-mandated-deliverable findings pass on plan-fidelity YES alone?
- **Resolution**: OOS for this issue. Keep 2-of-3 threshold unchanged.
- **Source**: user
