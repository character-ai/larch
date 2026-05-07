# scripts/test-agent-model-args.sh

Regression harness for `scripts/agent-model-args.sh`.

It pins the line-token stdout contract for Codex, Cursor, and Gemini: one argv token per physical line, no empty stdout lines on successful paths, ordinary punctuation preserved as a single token, and invalid Codex effort warnings sent to stderr while stdout remains machine-only.

It also covers the fail-closed input boundary: explicit blank / whitespace-only model env vars are rejected, and model values containing POSIX `[[:cntrl:]]` characters are rejected before any consumer launches an external CLI.

The static migration guard scans shell runtime under `scripts/` and `skills/` for unquoted scalar `MODEL_ARGS` expansions, plain `"${MODEL_ARGS[@]}"` array expansions that omit the Bash-3.2-safe `[@]+` guard, and non-comment `mapfile` / `readarray` use.

**Primary**: `scripts/agent-model-args.sh`

**Makefile wiring**: `make test-agent-model-args`, included in `test-harnesses-2`.
