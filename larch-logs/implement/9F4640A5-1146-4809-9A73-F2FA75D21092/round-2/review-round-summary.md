# Review Round 2

- Mode: `diff`
- 1 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_4: Restore byte-identical chooser copy
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: important
- **Concern**: `design_gate_render.py` is surfacing command-oriented copy in user-visible chooser text instead of the accepted byte-identical wording.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Copy the old AskUserQuestion-visible option descriptions into the renderer constants, changing only the required cap-authority wording where the stale literal `5` must be removed, and keep the golden tests pinned to those legacy strings.
  - From codex-specialist-edge-cases: Keep renderer/orchestrator commands only in markdown instructions. Restore the prior visible option descriptions in `design_gate_render.py`, with only the cap-authority wording adjusted as needed, and update `python/tests/design/test_design_gate_render.py:72-75` and `python/tests/design/test_design_gate_render.py:138-142` to pin the restored user-facing text.


