# Review Round 1

- Mode: `diff`
- 2 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_3: `_growth_violations()` never compares the `files` field
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: important
- **Concern**: `python/larch/lint/lint_skill_closure_growth.py:677-693` — `_growth_violations()` never compares the `files` field, despite the plan saying panel-tier ratchets `closure_*` and `files`. A concrete failure: adding an empty `agents/new-reviewer.md` grows panel-tier source coverage, but line/token metrics stay unchanged, so `lint skill-closure-growth` exits 0.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Add explicit file-list growth checks for ratcheted targets that require file ratcheting, at least `panel-tier`.


### FINDING_4: Review `step-name-registry.tsv` outside ratcheted `/review` closure
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: important
- **Concern**: The new registry `.tsv` matcher is not applied to `review`, so `skills/review/scripts/step-name-registry.tsv` remains outside the newly ratcheted `/review` closure even though `skills/review/SKILL.md:18` tells the agent to read `step-name-registry.tsv`. Changes to that prompt source can grow without `skill-closure report` or `lint skill-closure-growth --skill review` seeing them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Include `review` in the session-start registry matcher and resolve the `/review` basename form to `skills/review/scripts/step-name-registry.tsv`, or update the prompt to use the full plugin-root path and count it for review.


