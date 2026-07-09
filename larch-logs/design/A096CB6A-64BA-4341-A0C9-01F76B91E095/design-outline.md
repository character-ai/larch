## Proposed Design Outline

### Goals
- Close the TOCTOU windows around `chmod` and `mktemp` in `hook-anti-read-poll.sh` using fd-based atomic operations
- Replace path-based `chmod 700` with `O_NOFOLLOW + fchmod(fd)` via Python3 to prevent mode changes on swapped targets
- Replace bash `mktemp` with `O_NOFOLLOW + dir_fd`-relative temp-file creation so temp files can never land in attacker-controlled storage

### Non-goals
- Redesign the hook's JSON-parsing or session-key logic
- Move state storage out of `$TMPDIR` (trusted-root relocation is not required since fd-binding is the fix)
- Add cleanup logic for stale state files

### Approach sketch
- In `hook-anti-read-poll.sh`: replace `chmod 700 "$state_dir"` with a single-line `python3 -c` call using `O_NOFOLLOW + fchmod(fd)`
- In `hook-anti-read-poll.sh`: replace `mktemp "$state_dir/..."` with a `python3 -c` call that opens the dir via `O_NOFOLLOW`, creates the temp file using `os.open(..., dir_fd=fd)`, and prints the path
- Both Python3 calls use env-var argument passing to avoid nested quoting
- Keep existing bash guards as defense-in-depth; Python3 atomicity is the primary TOCTOU fix
- In `test-hook-anti-read-poll.sh`: update the Python3 variant-construction code to find the new Python3 lines, regenerate guardless variants, and add swap-after-mkdir tests verifying that the Python3 calls exit 0 when state_dir is a symlink

### Surfaces in scope
- `scripts/hook-anti-read-poll.sh`
- `scripts/test-hook-anti-read-poll.sh`

### Open questions
- None.
