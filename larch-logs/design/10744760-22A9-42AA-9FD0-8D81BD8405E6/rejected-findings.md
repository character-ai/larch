### [Plan Review] FINDING_3

### FINDING_3: Symlinked `source-env.sh` drops `claude_pid` and skips capture
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: If `$DESIGN_TMPDIR/source-env.sh` is symlinked, `_load_source_env` returns `{}` without `claude_pid`, so design publish skips transcript capture and the new run remains unmeasured even when other capture wiring is correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Thread the parsed `--claude-pid` into `_load_source_env` and add a regression test with a trusted symlinked `source-env.sh`.


