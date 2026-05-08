# test-compose-review-findings.sh — sibling stub

Regression harness for `scripts/compose-review-findings.sh`. Self-contained:
creates fixtures under a fresh tmpdir, exercises the helper, asserts the
output shape, checks jq-only JSONL parsing, verifies inline/archive redaction,
and cleans up.

The full contract for the helper under test lives at
`scripts/compose-review-findings.md`. This stub points there for the
behavioral contract; the harness file itself documents the assertion list
in its own header comment.

Wired into `make lint` via the `test-compose-review-findings` target —
runs in CI on every PR alongside the other anchor / tracking-issue
regression harnesses.
