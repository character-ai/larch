# scripts/redact-tmpdir-paths.sh — contract

`scripts/redact-tmpdir-paths.sh` is the deterministic stdin-to-stdout scrubber for larch session temp directory literals and operator repo paths before text crosses a remote publishing boundary. It rewrites `/tmp/`, `/private/tmp/`, and `/var/folders/` (macOS) session roots plus the cache-backed `${XDG_CACHE_HOME:-$HOME/.cache}/larch/sessions/` root to `<TMPDIR>`. It also rewrites `/Users/<name>/<repo>/` and `/home/<name>/<repo>/` paths (operator sibling working-tree roots such as reviewer-local absolute paths leaked into committed log content) to `<OPERATOR_REPO_PATH>/`.

The helper is intentionally markdown-unaware and idempotent. Non-matching input is passed through unchanged; running the helper twice produces the same output as running it once.

## Callers

Outbound publishers compose this helper before `scripts/redact-secrets.sh`, so tmpdir paths are removed before issue comments, PR bodies, and GitHub error envelopes are emitted. The primary runtime callers are `scripts/tracking-issue-write.sh` and `scripts/create-pr.sh`.

## Test Harness

`scripts/test-redact-tmpdir-paths.sh` covers legacy `/tmp`, macOS `/private/tmp`, clone-tagged names, cache-root paths, operator repo paths (including dotted repo names and Linux `/home/...` clones), prose embedding, non-matching preservation, idempotence, multiple cache-root paths inside one JSON object, and JSONL `\n`-prefixed paths for operator repo paths plus all three session roots (expressions 4-7). It is wired through `make test-redact-tmpdir-paths`.

## Boundary handling

Expressions 1-3 use `(^|[^[:alnum:]_./-])` as the left boundary anchor. This prevents the preceding non-whitespace prefix from consuming non-path content before a session path:

- Valid boundary characters include `=`, `"`, `'`, space, `:`, `(`, `)` — any character not in `[:alnum:]_./-`.
- The boundary character is captured in `\1` and re-inserted in the replacement so surrounding context (variable assignments like `VARNAME=<TMPDIR>`, JSON delimiters) is preserved.
- JSONL-encoded newlines (`\n` as two chars) do not serve as boundaries for expressions 1-3 because `\` alone is a valid boundary but the following `n` is `[:alnum:]`, preventing a match when `\n` immediately precedes the path.
- The cache-root parent path in expression 3 is segment-aware: each segment stops at JSON string delimiters and path boundaries (`"`, `\`, `/`) so two quoted `/larch/sessions/` paths on the same line are redacted independently instead of collapsing into one match.

Expressions 4-7 handle the `\n`-prefix carve-out for operator repo paths and all three session roots: each matches the literal two-char sequence backslash+n immediately before `/Users/<name>/<repo>/`, `/home/<name>/<repo>/`, a `larch/sessions/` cache root, `/tmp`, or `/var/folders` session path, captures `\n` as `\1`, and re-emits it in the replacement. For example, `\n/Users/…/my.repo/scripts/foo.sh` is rewritten to `\n<OPERATOR_REPO_PATH>/scripts/foo.sh`, and `\n/Users/…/.cache/larch/sessions/claude-implement-XYZ` is rewritten to `\n<TMPDIR>` rather than passing through unchanged.

## Edit-in-sync

When changing the accepted tempdir roots or session prefix list, update `scripts/session-setup.sh`, `scripts/cleanup-tmpdir.sh`, `scripts/implement-finalize.sh`, `scripts/token-tally.sh`, this contract, and `scripts/test-redact-tmpdir-paths.sh`.
