# test-revise-plan-with-waterfall.sh

Cross-tree harness for `skills/design/scripts/revise-plan-with-waterfall.sh`.
The primary behavior contract lives in
`skills/design/scripts/revise-plan-with-waterfall.md`.

Cases cover Codex win, Cursor promotion, Claude fallback, no-patch failure,
apply failure, emit-plan failure, Codex absence, argv defects, canonical-plan
invariant, heading-loss revert, and prompt-source assertions.

Makefile target: `test-revise-plan-with-waterfall`.
