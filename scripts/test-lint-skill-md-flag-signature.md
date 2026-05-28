# test-lint-skill-md-flag-signature.sh - contract

Harness for `scripts/lint-skill-md-flag-signature.sh`.

It builds hermetic `skills/<fixture>/SKILL.md` and `scripts/*.sh` fixture pairs under `mktemp -d`, then verifies matching flags, missing flags, multiple mismatches, waivers, multiline backslash-continuation invocations, and the issue #3077 `write-run-params.sh` drift/fixed shapes.

Run with `bash scripts/test-lint-skill-md-flag-signature.sh` or `make test-lint-skill-md-flag-signature`.
