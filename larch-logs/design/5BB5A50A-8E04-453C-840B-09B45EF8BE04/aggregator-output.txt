### FINDING_1: Case 14 does not seed omitted reviewer keys before testing preservation
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-dyn-test-gap-recovery, Codex-dyn-test-gap-recovery
- **Severity**: important
- **Concern**: Case 14 attempts to verify that omitted reviewer keys are preserved during a partial override, but its setup only seeds `CODEX_PRESENT`. Without prior values for `CURSOR_PRESENT`, `CODEX_AVAILABLE`, and `CURSOR_AVAILABLE`, the test cannot prove those omitted keys survive the rewrite.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch: Seed all four reviewer keys in the first Case 14 write, then rewrite with only --codex-present false and assert CODEX_PRESENT=false while the other three keep their initial values
  - From Cursor-dyn-test-gap-recovery, Codex-dyn-test-gap-recovery: Seed all four reviewer keys in Case 14's first write, then rewrite the same output with only --codex-present false and assert CODEX_PRESENT is false while CURSOR_PRESENT CODEX_AVAILABLE and CURSOR_AVAILABLE keep their seeded values

### FINDING_2: Partial explicit overrides can preserve stale alias values
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Concern**: A partial override such as `--codex-present false` can emit `CODEX_PRESENT=false` while recovering an old `CODEX_AVAILABLE=true`, causing alias consumers to see contradictory availability state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Either require paired overrides in the plan/test, or track flag presence and mirror an explicit present/available value to its omitted peer instead of recovering the stale peer
