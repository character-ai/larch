## Proposed Design Outline

### Goals
- Close two TOCTOU windows in `hook-anti-read-poll.sh`: between `mkdir -p` and `chmod`, and between the last state-dir guard and `mktemp`.
- Add a negative-control regression test showing the new pre-mktemp guard is load-bearing.

### Non-goals
- Ancestor-symlink path-component checks (requires per-hop traversal; attack surface requires same-UID compromise of a `/tmp` parent, which is out of scope).
- Changes to any other hook or script beyond the two targeted files.

### Approach sketch
- Add one guard line (`[ -d "$state_dir" ] && [ ! -L "$state_dir" ] || exit 0`) immediately after `mkdir -p`, before `chmod 700`.
- Add one guard line with the same text immediately before `mktemp`.
- In the test, create two hook variants via inline Python heredocs: a fully-guardless hook (all state-dir guards removed) and a deep-guardless hook (same but the new pre-mktemp guard is kept).
- Run each variant with `state_dir` pointing at a symlink to a redirect dir; verify the negative control writes a state file to the redirect and the positive test does not.

### Surfaces in scope
- `scripts/hook-anti-read-poll.sh`
- `scripts/test-hook-anti-read-poll.sh`

### Open questions
- None.
