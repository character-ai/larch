### FINDING_1: Empty compose-findings needs conditional scratch-dir handling
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: The compose-findings path appears to require a scratch directory too early, which could break the empty-input contract. If no design or implement inputs are present, the command should still be able to emit an empty JSONL output without needing a tempfile or ambient scratch state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Resolve scratch_dir as optional and fail only before branches that actually call _is_security_text or create the Gate B filtered tempfile; keep the no-input path writing an empty output


### FINDING_4: Published design log worktree can be copied into itself
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: The disposable publish worktree is placed under the directory that is later iterated and copied into the final design log tree. That makes it possible for the publish step to accidentally include the worktree or repo contents inside the committed output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Do not place the publish worktree directly under the published `design_tmpdir`, or add an explicit exclusion before the copy loop. Use an excluded scratch directory or a run-owned sibling outside the tree being copied.


### FINDING_5: Run-log scratch path can pollute the repo root
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Concern**: The run-log scratch directory is routed to `log_root.parent`, which can be the repository root for direct callers. That can create transient files in the working tree and trip clean-tree guards or interrupted-write cleanup paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Use `log_root.parent` only when it is an existing session/run tmpdir; otherwise use a larch-owned cache scratch directory such as ~/.cache/larch/sessions after mkdir, and keep the no-ambient-TMPDIR rule

