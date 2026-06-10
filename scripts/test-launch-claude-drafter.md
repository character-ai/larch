# test-launch-claude-drafter.sh

Offline regression harness for `scripts/launch-claude-drafter.sh`.

The harness prepends PATH stubs for `claude` and `git` so no network or repository mutation is required. The `claude` stub records native argv and emits JSON envelopes for success, malformed JSON, `is_error`, empty result, delimiter failures, missing `diff_lines`, and no-summary success. The `git` stub emits caller-selected porcelain to exercise baseline-delta and no-baseline dirty-tree sidecars.

Coverage mirrors `launch-claude-drafter.md`:

- model, prompt, and output path validation;
- invalid output paths may exit before `.dirty-tree` exists;
- post-output-canonicalization failures write `.dirty-tree`;
- native argv contains `--add-dir`, `--allowedTools Read,Glob,Grep,LS`, and `--permission-mode plan`, and contains no `--read-tools*`, `Write`, `Edit`, or `Bash` grants;
- JSON `.result` promotion keeps the status KV file authoritative;
- invalid JSON, `is_error`, and empty result fail with `CLAUDE_JSON_RESULT_INVALID` / exit `99` and do not append token rows;
- whole-line delimiter extraction writes `plan.txt` and optional `plan-summary.md`;
- duplicate/malformed delimiters and missing `diff_lines:` fail closed;
- delimiter names inside plan prose are allowed when not exact sentinel lines;
- `.done`, `.meta`, `.stderr`, `.stderr-tail` or `.failure-diag`, and `.dirty-tree` sidecars are covered on success/failure paths;
- no persistent `.result` or `.json` sidecar remains;
- baseline clean, baseline dirty, and no-baseline unknown cases;
- token row `vendor=claude_sub raw=claude_draft`.

Makefile target: `make test-launch-claude-drafter`.
