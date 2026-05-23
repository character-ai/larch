# Review Round 3

- Mode: `diff`
- 3 accepted, 11 rejected (9 exonerated)

## Accepted Findings

### FINDING_12: Missing positive harness for `VAR=$( ... denylisted.sh ... )`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: No positive fixture for command-substitution assignment to a variable with a denylisted `.sh` path, though the plan listed that shape and production uses it (e.g. `dispatch-with-waterfall.sh`)—a bad refactor of the `=$(` ERE branch could ship if only the harness is run without full-repo lint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_14: `CLAUDE_PLUGIN_ROOT` anchor regex matches dangerous suffix substrings
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: The `CLAUDE_PLUGIN_ROOT` anchor ERE can match any suffix equal to a denylisted basename (e.g. a path ending in `.../test-review-and-fix.sh` treated like `review-and-fix.sh`), causing false violations or misleading marker placement unless matching is tightened to the final path segment or explicit `/basename` boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_8: Unbraced `$CLAUDE_PLUGIN_ROOT/.../denylisted.sh` not matched by ERE branches
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Unbraced `$CLAUDE_PLUGIN_ROOT/.../denylisted.sh` invocations are not matched by existing ERE branches, so omitted markers around valid unbraced expansion calls can pass lint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


