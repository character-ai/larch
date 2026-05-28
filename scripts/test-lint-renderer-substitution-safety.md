# test-lint-renderer-substitution-safety.sh - contract

Harness for `scripts/lint-renderer-substitution-safety.sh`.

It builds hermetic fixture roots under `mktemp -d`, then verifies safe split substitutions, ANSI-C escape replacements, unsafe bare/braced/array variable replacements, same-line and preceding-line waivers, quoted heredoc fixture tolerance, and the PR #3051 readability-substitution regression shape.

Run with `bash scripts/test-lint-renderer-substitution-safety.sh` or `make test-lint-renderer-substitution-safety`.
