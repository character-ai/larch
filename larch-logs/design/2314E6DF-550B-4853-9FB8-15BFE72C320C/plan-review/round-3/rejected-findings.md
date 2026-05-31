### [Plan Review] FINDING_5

### FINDING_5: Fixer waterfall launch argv contract underspecified
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: `build_launch_argv` / `launch_tier` require `--output`, `--run-id`, `--repo`; bash also passes optional `--plan-file` via `plan_args`. The plan only lists `--role` and `--conflict-files`, so injected `launch_fn` closure behavior is unclear.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Document the closure around injected `launch_fn`: temp output path, `plan_file` when available, then `run_waterfall`; tests should assert argv includes `--output` and optional `--plan-file`


### [Plan Review] FINDING_8

### FINDING_8: Duplicate conflict prompt assembly vs launch scripts
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `_resolve_conflicts` is described as building a fixer prompt from `conflict-resolution.md` while also calling `launch_*-ci`. Launch scripts already inject `CONFLICT_CONTEXT` and optional `PLAN_CONTEXT`; duplicating prompt assembly in `rebase.py` adds surface area and can drift from `launch-cursor-ci.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Have _resolve_conflicts only call agents.launch_tier / run_waterfall with role=resolve-conflict and conflict_files; delete prompt-building prose from the plan


