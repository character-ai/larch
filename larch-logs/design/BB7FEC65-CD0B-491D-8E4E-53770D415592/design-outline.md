## Proposed Design Outline

### Goals
- Scope the generic-read poll counter by session, matching the task-output counter's existing session+cwd keying
- Add a regression test for generic-read session isolation (mirroring the existing task-output isolation test)
- Update the sibling doc to document consistent session+cwd keying for both counters

### Non-goals
- Changing task-output counter key (already correct)
- Changing window durations, thresholds, or fire logic
- Cleaning up unrelated code in the hook or tests

### Approach sketch
- One-line fix in `handle_generic_read_poll`: add `${session_hash}` to the state file key
- Update three existing test assertions that directly construct the old `state-${cwd_hash}.tsv` path to use the new `state-${session_hash}-${cwd_hash}.tsv` pattern
- Add one new test section: generic-read session isolation (two sessions share cwd; verify they don't share the counter)
- Update `hook-anti-read-poll.md` State section: rename `state-<cwd_hash>.tsv` to `state-<session_hash>-<cwd_hash>.tsv`

### Surfaces in scope
- `scripts/hook-anti-read-poll.sh` (line 356, state file key)
- `scripts/test-hook-anti-read-poll.sh` (3 path updates + 1 new section)
- `scripts/hook-anti-read-poll.md` (State doc entry)

### Open questions
- None.
