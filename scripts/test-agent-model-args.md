# scripts/test-agent-model-args.sh

Regression harness for `scripts/agent-model-args.sh`.

It also covers the fail-closed input boundary: explicit blank / whitespace-only model env vars are rejected, and model values containing POSIX `[[:cntrl:]]` characters are rejected before any consumer launches an external CLI.

The static migration guard scans shell runtime under `scripts/` and `skills/` for unquoted scalar `MODEL_ARGS` expansions, plain `"${MODEL_ARGS[@]}"` array expansions that omit the Bash-3.2-safe `[@]+` guard, and non-comment `mapfile` / `readarray` use.

**Primary**: `scripts/agent-model-args.sh`

**Prerequisites**: `ripgrep` (`rg`) must be on `PATH`. The harness fails fast with exit 2 if `rg` is missing — the static migration guards above scan the repo for unsafe `MODEL_ARGS` expansion patterns and would otherwise silently PASS via empty `rg ... || true` substitutions.

**Makefile wiring**: `make test-agent-model-args`, included in `test-harnesses-2`.
