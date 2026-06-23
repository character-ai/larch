# Review Round 2

- Mode: `diff`
- 2 accepted, 3 rejected (0 neutral)

## Accepted Findings

### FINDING_11: Bare `*` without following kw-only params still flagged
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_has_bare_star_separator` only returns `True` when `kwonlyargs` is non-empty, so `def f(a, b, *)` with no following kw-only parameters is still flagged. Parts 1–10 convert definitions to bare-`*`-only signatures expecting baseline rows to drop on regen; those rows stay forever and the ratchet never tightens for the common minimal fix. Detect bare `*` via `ast.get_source_segment` or def-line source parsing; add a unit test for `def f(a, b, *): pass`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_14: Trailing bare `*` falsely satisfies rule while positional params remain
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: The lint accepts any bare `*` anywhere in the signature, not a leading `*`. A new function like `def new_helper(a, b, *, dry_run=False): ...` returns no violation even though it still has two non-`self`/`cls` positional parameters. Existing examples such as `python/git.py:54-58` are also omitted from the baseline for this reason.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Treat the signature as compliant only when the bare `*` appears before the second non-`self`/`cls` parameter, or before the first non-`self`/`cls` parameter if the intended rule requires all counted args to be keyword-only, then regenerate the baseline.


