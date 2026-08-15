# Review token propagation coverage (pytest)

Offline coverage for token telemetry propagation across `/implement` Step 5's
`review-and-fix` boundary lives in
`python/tests/implement/test_implement_shell_scripts.py` (token-propagation
node group).

## Coverage

- Builds a parent `/implement`-style session-env containing `LARCH_TOKEN_SESSION_ID` and `LARCH_CLAUDE_SOURCE_FILE`.
- The native `session setup` integration matrix runs `scripts/larch.sh session setup --caller-env ... --write-session-env ...` and asserts both keys survive the bounded caller-env allow-list.
- Asserts `LARCH_TIMING_LEDGER` survives the same caller-env to writer round-trip only when it is under an accepted root.
- Asserts `LARCH_TIMING_LEDGER` does not appear on `session-setup.sh` stdout.
- Rehydrates the written keys, runs `scripts/larch.sh review-and-fix step5 --mode single --implement-tmpdir` with a stubbed `review core`, and asserts the review-core subprocess sees the parent token session id, Claude source file, timing ledger, and implement session-env path.
- Asserts each starting difficulty keeps the expected panel shape and fixed round cap of 2.

## Edit-in-sync

Update with `crates/larch-cli/src/session_setup_commands.rs`, `scripts/larch.sh session write-env`, `scripts/larch.sh review-and-fix step5`, `scripts/larch.sh review core`, `crates/larch-cli/tests/session_setup.rs`, `crates/larch-cli/tests/review_and_fix_commands.rs`, and `skills/shared/subskill-invocation.md` when changing nested review session-env propagation.
