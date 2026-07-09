# hook-anti-read-poll.sh

PostToolUse hygiene hook for generic repeated `Read` calls.

The hook warns on the third consecutive `Read` of the same file path and offset within a short window. It is advisory only and never blocks tool use. It does not inspect background task output or step completion state.

`scripts/hook-anti-read-poll.sh` is a thin stdin-forwarding wrapper around `python/cli.py hook anti-read-poll`. The Python helper owns state under `${TMPDIR:-/tmp}/larch-read-poll`, performs state writes relative to verified directory file descriptors, and stores hashed path rows instead of raw file paths.
