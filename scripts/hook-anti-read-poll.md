# hook-anti-read-poll.sh

PostToolUse hygiene hook for generic repeated `Read` calls.

The hook warns on the third consecutive `Read` of the same file path and offset within a short window. It is advisory only and never blocks tool use. It does not inspect background task output or step completion state.

`scripts/hook-anti-read-poll.sh` is a thin stdin-forwarding wrapper around `scripts/larch.sh hook anti-read-poll`; it never requires Python or executes `bin/larch` directly. The Rust owner stores advisory state under `${TMPDIR:-/private/tmp}/larch-read-poll`, uses no-follow directory-file-descriptor operations and same-directory atomic replacement, and stores hashed path rows instead of raw file paths. Any event-decoding or local-state failure stays silent and exits successfully.
