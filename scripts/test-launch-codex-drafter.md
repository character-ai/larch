# test-launch-codex-drafter.sh

Offline regression harness for `scripts/launch-codex-drafter.sh`.

The harness prepends PATH stubs for `codex` and `git` so no network or repository mutation is required. The `codex` stub records argv, copies `CODEX_HOME/config.toml` when requested, and emits `--output-last-message` transcripts for success, exec failure, empty output, delimiter failures, missing `diff_lines`, and no-summary success.

Coverage mirrors `launch-codex-drafter.md`:

- prompt and output path validation;
- invalid output paths may exit before `.dirty-tree` exists;
- post-output-canonicalization failures write `.dirty-tree`;
- read-only sandbox argv and trusted-instructions override in temp `CODEX_HOME/config.toml`;
- sentinel promotion writes `plan.txt` and optional `plan-summary.md`;
- exec failure writes redacted `.stderr-tail` without raw secrets;
- empty output fails with `CODEX_EMPTY_OUTPUT`;
- duplicate/malformed delimiters and missing `diff_lines:` fail closed with exit `99`;
- delimiter names inside plan prose are allowed when not exact sentinel lines;
- `.done`, `.failure-diag`, and `.dirty-tree` sidecars on failure paths;
- baseline clean, baseline dirty, and no-baseline unknown cases;
- timing ledger rows for `codex-plan-draft`.

Makefile target: `make test-launch-codex-drafter`.
