# token-ledger.sh

**Purpose**: Session-scoped JSONL ledger for `/implement` token accounting. It records step boundary marks and external-vendor token totals. The ledger is observability-only; failures warn on stderr, exit 0, and never block `/implement`.

## Relationship to scripts/token-tally.md

`scripts/token-tally.sh` is the older `/research` helper for lane-level Claude token sidecars. `scripts/token-ledger.sh` is a distinct `/implement` PoC mechanism: JSONL, step marks, vendor records, and session-id based file naming. Do not merge the two contracts in this PR.

## Session-id resolution

Resolution order (used to derive the hash suffix in the ledger filename):

1. `LARCH_TOKEN_SESSION_ID` env var if set and non-empty.
2. `$IMPLEMENT_TMPDIR/session-id` file if present and non-empty.
3. `$DESIGN_TMPDIR/session-id` file if present and non-empty (standalone `/design` parity with `timing-ledger.sh`).
4. `sha256(cwd)` deterministic fallback.

The cwd-hash fallback is a last resort and can collide across multiple concurrent `/implement` windows in the same checkout. Step 0 exports `LARCH_TOKEN_SESSION_ID` after `write-session-id.sh` so normal runs avoid that collision.

The resolved id is never used directly in the filename. It is hashed and used as the `<sha256>` suffix in `larch-tokens-<sha256>.jsonl`, preventing path traversal, whitespace, and control bytes from escaping.

## Ledger path resolution

Resolution order for the ledger file location:

1. `--ledger PATH` override, validated under `${TMPDIR:-/tmp}`.
2. `$LARCH_TOKEN_LEDGER`, validated under `${TMPDIR:-/tmp}`.
3. `$IMPLEMENT_TMPDIR/larch-tokens-<sha256(session-id)>.jsonl` when `IMPLEMENT_TMPDIR` is set and is an existing directory.
4. `$DESIGN_TMPDIR/larch-tokens-<sha256(session-id)>.jsonl` when `DESIGN_TMPDIR` is set and is an existing directory (standalone `/design` sessions).
5. `dirname("$SESSION_ENV_PATH")/larch-tokens-<sha256(session-id)>.jsonl` when `SESSION_ENV_PATH` is set and its parent directory exists.
6. Fails closed with a stderr warning when none of the above are set. Callers MUST set at least one root or pass `--ledger`.

## Subcommands

- `mark <step-name>` appends a JSON object with `type=mark`, `step`, and UTC `ts`.
- `record-vendor <vendor> [key=value ...]` appends a JSON object with `type=vendor`, `vendor`, `input`, `output`, `cache_read`, `cache_create`, `total`, `raw`, and UTC `ts`.
- `dump` prints the ledger path on stdout's first line, then the JSONL contents when present.

`--ledger PATH` overrides session-id resolution for tests. The override resolves under `${TMPDIR:-/tmp}` after canonicalizing its parent. Paths with `..` are rejected.

`record-vendor raw=` is enum-like and bounded. Use short provenance labels such as `codex_implement`, `codex_review`, `cursor_implement`, or `cursor_review`; never paste unstructured stderr, stdout, sidecar logs, prompts, or user content into `raw=`.

## Failure Mode

All subcommands are best-effort. On malformed input, missing `jq`, or path failures, the script writes a warning to stderr and exits 0. It should not mutate stdout except for `dump`. When ledger path resolution fails (no per-run root configured), `dump` writes the warning to stderr and produces no stdout output; callers that assume the first line is always a valid path must handle the empty case.

## Test Harness

`scripts/test-token-ledger.sh` covers mark / vendor / dump round trips, session-id precedence, safe hashed filenames, `--ledger` containment, JSON safety, and mode `600`.
