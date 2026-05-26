# test-tracking-issue-summary.sh contract

Regression harness for `scripts/tracking-issue-summary.sh`.

It runs against a stub `gh` executable and covers create, update, redaction,
stable `larch:diagrams` marker handling, and multiple-comment fail-closed
behavior for marker-keyed summary comments.
