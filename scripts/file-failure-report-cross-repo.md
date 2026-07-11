# file-failure-report-cross-repo.sh

`file-failure-report-cross-repo.sh` files `/implement` stall recovery reports across repositories and deduplicates them by exact public signature marker.

## Inputs

Required inputs are `--repo OWNER/REPO` and `--body-file PATH`. Create paths also require `--title TITLE`. `--dedup-only` runs the Tier A pre-pass without creating an issue.

Non-dry-run calls require `--mutation-context PATH`, `--run-id ID`, and `--trusted-root PATH`. Trusted callers pass the authoritative implement or design session tmpdir as `--trusted-root`, its matching live run ID, and the session env file as an immediate child of that root. The shared Python checker requires a canonical session root, a regular non-symlink context file, `LARCH_LIVE_MUTATION_OK=true`, and matching run identity. The helper does not protect against a caller that controls every argument and the filesystem state. Dry-run paths are authorization-free and make no `gh` calls.

Refusal emits `FILE_FAILURE_REPORT_STATUS=mutation-refused` and `FILE_FAILURE_REPORT_FALLBACK_REASON=unauthorized-mutation:<reason>`.

Optional structured comment payloads are `--attempts-file`, `--escalation-ledger-file`, and `--root-cause-file`. The helper validates supplied files as regular, readable, non-symlink paths.

## Signature dedup contract

The body must contain the exact marker:

```text
<!-- larch-stall:signature=<64-hex> -->
```

The helper fetches all open issues with bodies from `--repo` using `gh api --paginate`, ignores pull requests, and exact-matches the marker client-side.

## Create and comment behavior

- On a match, the helper posts one `+1 occurrence` comment instead of creating a duplicate.
- The comment is assembled only from structured payload files. It does not repost the full report body.
- On no match, non-dedup paths create with `gh issue create -R "$repo" --title "$title" --body-file "$body_file"`.
- `FILE_FAILURE_REPORT_STATUS=filed` is the create-success token.
- `FILE_FAILURE_REPORT_URL` may be an issue URL or comment URL depending on status.
- Issue URL aliases are caller-owned. Callers must not populate issue aliases from comment URLs.

## Tier B public comment boundary

Tier B callers must pass only bounded public slices:

- bounded attempts table
- allowlisted escalation summary with sanitized site and trigger rows only
- `stall-recovery-bounded-root-cause.md` or an equivalent bounded root-cause slice

Tier B callers must not pass raw ledger TSV, raw root-cause files, full report bodies, raw logs, paths, branches, or run IDs as comment payloads. The helper rejects Tier B comments that look like raw report bodies and reuses the existing stall-recovery sensitive-token rejection path before posting.

## Fallback and dry-run status

- `--dedup-only` no match emits `FILE_FAILURE_REPORT_STATUS=no-match`.
- Tier A `--dedup-only` lookup failure or marker-missing emits `FILE_FAILURE_REPORT_STATUS=lookup-failed-open` and exits 0.
- Non-dedup missing marker, lookup failure, auth failure, network failure, comment failure, or create failure emits `FILE_FAILURE_REPORT_STATUS=fallback-print-required` with `FILE_FAILURE_REPORT_FALLBACK_REASON=<token>` and exits 0.
- Authorization refusal (missing, invalid, outside-root, run-mismatched, or denied authorization input) emits `FILE_FAILURE_REPORT_STATUS=mutation-refused` and `FILE_FAILURE_REPORT_FALLBACK_REASON=unauthorized-mutation:<reason>` with exits 0.
- `--dry-run` validates inputs and marker rules, emits `FILE_FAILURE_REPORT_STATUS=dry-run`, and makes no `gh` calls. Dry-run requires no mutation authorization arguments.

## Prefix-aware Tier B sensitive corpus

`--sensitive-corpus-file PATH` overrides the default `stall-recovery-sensitive-corpus.env` beside `--body-file`. `/implement` callers keep the default path. `/design` callers pass `design-failure-sensitive-corpus.env` so duplicate Tier B reports validate occurrence comments against the design-prefixed sensitive corpus.

Tier B comments fail closed to `fallback-print-required` when the sensitive corpus is missing, invalid, unreadable, or flags a sensitive token. Raw full-report body rejection recognizes both `/implement` and `/design` headings, so duplicate occurrence comments contain only bounded slices. Duplicate `/design` reports still exact-match the public signature marker and post `+1 occurrence` comments when validation passes.
