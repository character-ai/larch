# Review Round 1

- Mode: `diff`
- 2 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_2: Block-list parser silently skips malformed indented lines under `paths:`
- **Reviewer(s)**: codex-specialist-correctness-output.txt, dyn-topology-parser-output.txt
- **Severity**: important
- **Concern**: In block-list mode under `paths:`, indented lines that are not `-` list items are skipped via `continue` instead of failing. Shapes such as `paths:\n  skills/foo.md` (block-scalar), `paths:` followed by `include: docs/topology.md` mixed with valid `-` entries, or bare `paths:` with no list items can return `[]` or pass subset checks where legacy `yaml.safe_load` rejected non-list `paths` values. Failures surface as misleading “missing from paths” / “TSV runtime authorities missing” rather than `paths must be a list`. Harness case `j` covers inline scalar `paths: skills/foo.md` only; block-scalar and mixed-key gaps are untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Reject any indented non-comment line under paths: that does not start with - in block-list mode.
  - From dyn-topology-parser-output.txt: In the block-list loop, fail with `{RULE_PATH} frontmatter paths must be a list` when `leading > 0` and the stripped line is not a `-` entry (and is not only a comment). When block parsing finishes with `paths == []` and there was no inline flow value, also fail with the same message unless the inline form was explicitly `paths: []`.


### FINDING_3: Block-list topology paths accept YAML non-string tokens as strings
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Block-list topology parsing accepts YAML non-string tokens as path strings. A rule with `paths` containing a covered real authority plus an extra `- {foo: bar}` now passes, where the legacy PyYAML implementation failed with `paths[N] must be a string`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Tighten bare block tokens to a path-token grammar or reject YAML-like mapping sequence float anchor and alias tokens before accepting them


