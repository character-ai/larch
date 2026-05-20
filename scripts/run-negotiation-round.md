# scripts/run-negotiation-round.sh — contract

`scripts/run-negotiation-round.sh` is the per-round driver for the Negotiation Protocol described in `skills/shared/external-reviewers.md`. It wraps the Codex stdin-pipe and Cursor `--agent-prompt` invocation styles behind a uniform interface so callers don't repeat the per-tool argv shape. Removes the previous output file before invoking the tool (fresh-result invariant). Inputs: `--tool codex|cursor`, `--prompt-file`, `--output`, `--workspace`. Stdout emits `RESPONSE_FILE=<path>`. Exit 0 on success, 1 on usage error, 2 on reviewer command failure, and 3 on `cursor_auth_preflight` failure. Model-arg resolution failures from `scripts/agent-model-args.sh` propagate that helper's exit code (typically 1); its stderr diagnostic is the authoritative anchor. Used by `/design` Steps 1d / 3.5 (interactive design discussion rounds) when an external reviewer is the negotiator.

## KeyChain serial lock

Sources `scripts/lib-external-launcher-common.sh` to access `external_serial_lock_acquire` / `external_serial_lock_release_after`. Both the Codex and Cursor branches acquire the per-tool serial lock immediately before spawning the agent and release it asynchronously after `${LARCH_EXTERNAL_SERIAL_LOCK_DELAY:-0.5}` seconds, matching the pattern used by the 5 existing correctly-guarded launchers.

## Cursor auth handling

Sources `scripts/lib-cursor-auth.sh` in the Cursor branch and runs `cursor_auth_preflight || exit 3` before launching `cursor agent`. Model args from `scripts/agent-model-args.sh` are read as one argv token per line into Bash arrays and expanded with the Bash-3.2-safe `${MODEL_ARGS[@]+"${MODEL_ARGS[@]}"}` pattern. When `CURSOR_API_KEY` is non-empty, passes `--api-key "$CURSOR_API_KEY"` between the Cursor model-args array and `--workspace`. When empty, `cursor agent` runs without `--api-key` and falls back to its default auth resolution (e.g., the `cursor login` keychain entry on Darwin) — preserving backward compatibility with operators who haven't set the env var.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Response written |
| 1 | Usage / argument error, or the typical `scripts/agent-model-args.sh` validation failure propagated from that helper |
| 2 | Reviewer command failed |
| 3 | `cursor_auth_preflight` failed before `cursor agent` launched |
| other | Propagated from `scripts/agent-model-args.sh`; inspect that helper's stderr diagnostic |

The negotiation flow is foreground-synchronous and has no sentinel collector, so a synthesized `.done`/`.diag` (as in `launch-review.sh --tool cursor`) is unnecessary here.

## Stdout envelope symmetry

Every terminal exit path (success, exit 2, exit 3) emits `RESPONSE_FILE=<path>` on stdout before exiting, so callers can parse the response-file path with one rule regardless of failure class. The `RESPONSE_FILE` value still points at the configured `--output` path even on the exit-3 (preflight) path — the file may be empty (the script `rm -f`s it before invocation), but the key is always present. The exit-1 usage-error and `agent-model-args.sh`-propagated paths do NOT emit `RESPONSE_FILE` (they fail before the response-file slot is meaningful).

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.
