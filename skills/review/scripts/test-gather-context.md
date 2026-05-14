# test-gather-context.sh Contract

Regression harness for `skills/review/scripts/gather-context.sh`.

It exercises description mode, verifies that deterministic path resolution finds `skills/review/SKILL.md` for a review-skill description, and includes a stdout size cap assertion (≤2 KB).

Run with `bash skills/review/scripts/test-gather-context.sh` or `make test-gather-context`.
