# scripts/test-lint-no-raw-stderr-after-quiet-init.sh

Regression harness for `python3 python/cli.py lint no-raw-stderr-after-quiet-init`.

The harness builds a temp root and exercises clean post-init diagnostics, raw `echo`/`printf`/`cat` writes to FD 2, script/hook/skill scopes, function-definition false positives, quoted text, and heredoc handling.

It is invoked by `make test-lint-no-raw-stderr-after-quiet-init` through the harness shard wiring. The primary contract is `python/lint_no_raw_stderr_after_quiet_init.md`.
