## Proposed Design Outline

### Goals
- Resolve the rubric contradiction in the plan-fidelity voter: plan-mandated deliverables explicitly override the default-test-to-OOS rule.
- Add a citation-first grounding step to the voter prompt: quote the plan line before voting.
- Add a matching plan-mandated-deliverable carve-out to the reviewer Necessity gate, then regenerate affected agent files.

### Non-goals
- Self-consistency ensemble (k=3 voter runs).
- Threshold carve-out (plan-fidelity-alone pass).
- Auto-OOS capture system changes.
- Model or routing changes.

### Approach sketch
- Edit `VOTER_ARCHETYPES["plan-fidelity-completeness"]` in `python/rendering.py`: add the explicit override and the citation step.
- Add a carve-out paragraph to the "Default a test finding" section of the Necessity gate in `skills/shared/reviewer-templates.md`.
- Regenerate all four generated agent files via `python/cli.py generate <verb>`.
- Add unit tests in `python/test_rendering.py` asserting the new override and citation text appear in the rendered voter prompt.

### Surfaces in scope
- `python/rendering.py`
- `skills/shared/reviewer-templates.md`
- `agents/reviewer-plan-fidelity.md` (generated)
- `agents/code-reviewer.md` (generated)
- `agents/reviewer-code-robustness.md` (generated)
- `agents/reviewer-security-structure-tests.md` (generated)
- `python/test_rendering.py`

### Open questions
- None.
