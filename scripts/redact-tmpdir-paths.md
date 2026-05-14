# scripts/redact-tmpdir-paths.sh — contract

`scripts/redact-tmpdir-paths.sh` is the deterministic stdin-to-stdout scrubber for larch session temp directory literals before text crosses a remote publishing boundary. It rewrites `/tmp/`, `/private/tmp/`, and `/var/folders/` (macOS) session roots plus the cache-backed `${XDG_CACHE_HOME:-$HOME/.cache}/larch/sessions/` root to the literal `<TMPDIR>`.

The helper is intentionally markdown-unaware and idempotent. Non-matching input is passed through unchanged; running the helper twice produces the same output as running it once.

## Callers

Outbound publishers compose this helper before `scripts/redact-secrets.sh`, so tmpdir paths are removed before issue comments, PR bodies, and GitHub error envelopes are emitted. The primary runtime callers are `scripts/tracking-issue-write.sh` and `scripts/create-pr.sh`.

## Test Harness

`scripts/test-redact-tmpdir-paths.sh` covers legacy `/tmp`, macOS `/private/tmp`, clone-tagged names, cache-root paths, prose embedding, non-matching preservation, and idempotence. It is wired through `make test-redact-tmpdir-paths`.

## Boundary handling

All three expressions use `(^|[^[:alnum:]_./-])` as the left boundary anchor. This prevents the preceding non-whitespace prefix from consuming non-path content before a session path:

- Valid boundary characters include `=`, `"`, `'`, space, `:`, `(`, `)` — any character not in `[:alnum:]_./-`.
- The boundary character is captured in `\1` and re-inserted in the replacement so surrounding context (variable assignments like `VARNAME=<TMPDIR>`, JSON delimiters) is preserved.
- JSONL-encoded newlines (`\n` as two chars) do not serve as boundaries because `\` alone is a valid boundary but the following `n` is `[:alnum:]`, preventing a false match at that position.

## Edit-in-sync

When changing the accepted tempdir roots or session prefix list, update `scripts/session-setup.sh`, `scripts/cleanup-tmpdir.sh`, `scripts/implement-finalize.sh`, `scripts/token-tally.sh`, this contract, and `scripts/test-redact-tmpdir-paths.sh`.
