# macOS keychain interaction

When `CURSOR_API_KEY` is set in your environment, larch's launchers (`python/cli.py agent launch-review --tool cursor`, `python/cli.py agent launch-cursor-implement`, `python/cli.py agent run-negotiation-round`, plus the runtime markdown templates that emit `cursor agent` invocations) export the normalized `CURSOR_API_KEY` into the environment the `cursor agent` child inherits and pass **no** `--api-key` argv element (issue #3375 — keeping the secret off the command line, `.meta` logs, and `ps`). `cursor agent` reads the key from the `CURSOR_API_KEY` environment variable, bypassing the macOS keychain entirely for that auth path. This is the recommended setup for larch.

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

On Darwin only, larch's launchers run a read-only pre-launch check: if `CURSOR_API_KEY` is empty AND no `cursor-user` / `cursor-access-token` keychain entry exists, the launcher exits early with an actionable message rather than letting `cursor agent` emit the cryptic `Security process exited with code: 45`. The check and pre-read are strictly read-only — they do NOT delete keychain entries or invoke `cursor` as a subprocess. On Linux/CI, the check and pre-read are no-ops (`CURSOR_API_KEY` is the only auth path).

For the at-rest secret-persistence tradeoff (the API key appears in `.meta` `CMD_JSON` sidecars under the session tmpdir, because the collector's empty-output retry path relies on faithful argv reconstruction), see `SECURITY.md`.

```bash
# or
```
- Authenticate with OAuth:
```bash
```
```JSON
{
  "auth": {
    "type": "oauth"
  },
  "model": {
  }
}
```
```JSON
{
  "trustedFolders": [
    "/Users/<your-user-name>/path/to/repo"
  ]
}
```
```bash
```
