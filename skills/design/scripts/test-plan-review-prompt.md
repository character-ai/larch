# test-plan-review-prompt.sh

Regression harness for `skills/design/scripts/render-plan-review-prompt.sh`. It renders all 5 archetypes across the 2 supported external vendors and asserts: focus-area enum, `NO_ISSUES_FOUND` instruction, plan-file reference, `full_role` personality prose (`You are a`), TSV structured-record header, TSV record shape, and invalid-argument exit-2 behavior. Both Cursor and Codex are expected to produce equivalent TSV structured output.

Run with `make test-plan-review-prompt` or `bash skills/design/scripts/test-plan-review-prompt.sh`.
