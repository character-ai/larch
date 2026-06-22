# Review Round 2

- Mode: `diff`
- 3 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: --run-id swallows trailing flag tokens
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `--run-id` consumes the next argv token unconditionally, so a trailing flag can be swallowed as the run-id value instead of being parsed or rejected. `/design 123 --run-id --bogus` exits 0 with `RUN_ID=--bogus` (and `123 --run-id --hard` bypasses the `--hard` forbidden error; `123 --run-id --brainstorm` binds `RUN_ID=--brainstorm` without enabling brainstorm).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Reject --run-id values that start with - or match a known public flag token; add tests for 123 --run-id --bogus, --hard, and --brainstorm.


### FINDING_3: _delete unlinks sidecars without containment checks
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_delete` unlinks `.meta`/`.json` sidecars without containment checks even though callers only gate the primary path. A run dir with a legitimate `dyn-*-prompt.md` inside and a `dyn-*-prompt.md.meta` symlink to `/tmp/victim` causes `--execute` cleanup to unlink the external target.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Resolve each delete target and require _within_run_dir before unlink; add a sidecar-escape regression test


### FINDING_9: _within_run_dir does not catch RuntimeError on symlink loops
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `_within_run_dir` catches `OSError` from `Path.resolve()`, but Python 3.11 can raise `RuntimeError` for symlink loops. A run dir containing a self-referential symlink like `dyn-loop-prompt.md -> dyn-loop-prompt.md` will crash cleanup during `_contained(...)` instead of skipping the unsafe path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Catch `RuntimeError` alongside `OSError` and return `False`; add a regression test with a symlink loop inside a run dir.
