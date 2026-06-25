# Review Round 1

- Mode: `diff`
- 1 accepted, 10 rejected (5 neutral)

## Accepted Findings

### FINDING_6: plan_scout CLI presence flags parsed but ignored
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: CLI wrappers in `python/plan_scout.py` parse session presence flags but recompute availability from binary-found/PATH before invoking scout helpers. A caller marking Cursor absent can still launch Cursor when the binary exists on PATH, violating caller availability gates and changing scout manifests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Thread the parsed presence flags into the helper calls or remove the dead flags and use one consistent availability source end to end
  - From codex-specialist-testing-output.txt: Thread the parsed presence booleans through to scout_dynamic_archetypes/scout_plan_archetypes instead of recomputing from binary-found/PATH


