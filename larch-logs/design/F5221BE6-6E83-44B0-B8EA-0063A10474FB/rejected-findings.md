### [Plan Review] FINDING_4

### FINDING_4: Empty coder/expected-branch still shell-expand away
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-Requirements, Codex-Requirements
- **Severity**: blocking
- **Concern**: The launcher/tmpdir fix still leaves required non-tmpdir argv such as `--coder` and `--expected-branch` vulnerable to empty caller-shell expansion, so Step 2 can fail with a missing coder and the external-complete path can fail with an empty expected branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Teach run_dispatch_main to recover an empty --coder from the resolved tmpdir's bootstrap-routing.env or another durable Step 0 source, validate it against the safe coder set, and add the empty --coder execution case to the planned test.
  - From Codex-Innovation: Do not keep the rest of each command unchanged; either make affected entrypoints reconstruct all session-derived argv from the exported IMPLEMENT_TMPDIR and durable routing files, or change prompt fences so session-derived args are literal or resolved inside the called wrapper before execution
  - From Cursor-Requirements: After resolving tmpdir from env, fall back to `coder` from `session-env.sh` (bootstrap already persists it) when argv `--coder` is empty; add a focused test mirroring empty-argv plus env/session-env.
  - From Codex-Requirements: Extend the plan with targeted durable fallbacks for these required values. Have `run_dispatch_main` recover empty coder from `$IMPLEMENT_TMPDIR/bootstrap-routing.env`, and have `step2_post_dispatch_main` recover empty expected branch from the same durable `BRANCH_NAME`. Add empty-argv tests for both paths.


### [Plan Review] FINDING_5

### FINDING_5: Step 16-17 direct Python fence still bypasses launcher rehydration
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The Step 16-17 exception still invokes `python/cli.py` directly from a fresh shell with `--implement-tmpdir "$IMPLEMENT_TMPDIR"` and no launcher rehydration, so terminal report generation can still fail when the env var is absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Use the same `implement-run-$PPID.sh` prefix as other post-Step-0 fences for step-16-17, or add the same pointer-based tmpdir resolution used by the new runner.


