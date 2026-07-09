# hook-anti-read-poll.sh

PostToolUse hygiene hook for generic repeated `Read` calls.

The hook warns on the third consecutive `Read` of the same file path and offset within a short window. It is advisory only and never blocks tool use. It does not inspect background task output or step completion state.
