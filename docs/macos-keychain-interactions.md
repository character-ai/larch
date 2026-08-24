# macOS keychain interaction

When `CURSOR_API_KEY` is set in your environment, larch's Rust launchers (`scripts/larch.sh agent launch-review --tool cursor`, `scripts/larch.sh agent launch-cursor-implement`, and `scripts/larch.sh agent run-negotiation-round`) pass the normalized credential as a typed child-environment override and no `--api-key` argv element. This keeps the secret out of argv, ordinary command-line listings, and `.meta` logs; same-UID or host-level process inspection can still expose a live child environment. `cursor agent` reads the key from its environment, bypassing the macOS keychain entirely for that auth path. This is the recommended setup for larch.

When `CURSOR_API_KEY` is unset or empty on macOS, larch's shared Cursor launchers first pre-read the service that Cursor itself uses (`cursor-user` / `cursor-access-token`) and export the result as `CURSOR_API_KEY` for the child invocation. If that read succeeds, the Cursor child inherits `CURSOR_API_KEY` from the environment and does not perform its own keychain read. If the pre-read fails or returns empty, larch falls back to Cursor's default auth resolution, which may consult the keychain entry created by `cursor login`.

A stale or transiently-unhealthy `cursor-user` keychain entry can produce intermittent failures during parallel reviewer launches with errors like:

```
Password not found for account 'cursor-user'
Security process exited with code: 45
```

If you hit this, the simplest workaround is:

```sh
security delete-generic-password -a cursor-user 2>/dev/null
# then either:
export CURSOR_API_KEY="<your-key>"   # recommended for larch (env-only, deterministic)
# or:
cursor login                          # recreates the keychain entry interactively
```

On Darwin only, larch's launchers run a read-only pre-launch check: if `CURSOR_API_KEY` is empty AND the `cursor-user` / `cursor-access-token` keychain entry is missing or denies its read, the launcher exits early with an actionable message rather than letting `cursor agent` emit the cryptic `Security process exited with code: 45`. The check and pre-read are strictly read-only. They do NOT delete keychain entries or invoke `cursor` as a subprocess. On Linux/CI, the check and pre-read are no-ops (`CURSOR_API_KEY` is the only auth path).

The standalone check is `"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" agent cursor-auth-preflight`. It exits `0` when Cursor can authenticate and `2` with the actionable message when it cannot. For the credential-handling boundary it enforces, see [Vendor credential preflight and the reviewer-probe cache](security/supply-chain-credentials-and-services.md#vendor-credential-preflight-and-the-reviewer-probe-cache).

The credential is excluded from `.meta` `CMD_JSON` sidecars; retry metadata
reconstructs approved argv separately from the typed environment overlay. For
the remaining at-rest session-artifact boundary, see
[Private Session State and Retention](security/artifacts-redaction-and-publication.md#private-session-state-and-retention).
