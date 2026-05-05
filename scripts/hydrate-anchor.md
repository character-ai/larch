# scripts/hydrate-anchor.sh — contract

`scripts/hydrate-anchor.sh` is the single-call wrapper around the recurring inline `gh api … --jq '.body'` + awk section-extraction loop that `/implement` Step 0.5 uses on resume paths (Branches 1, 2, and 3) to repopulate `$IMPLEMENT_TMPDIR/anchor-sections/` from a previously-planted anchor comment. It exists so SKILL.md no longer carries inline `gh api` and awk-section-extraction code, and so the hydration semantics live in one tested place.

## Inputs

- `--anchor-id ID` (required) — the GitHub comment id of the anchor to fetch. Empty / unset short-circuits to `HYDRATED=false ERROR=anchor-id-empty`.
- `--tmpdir DIR` (required) — session tmpdir; the script creates `DIR/anchor-hydrate/` (for the raw body) and `DIR/anchor-sections/` (for fragment files).
- `--repo OWNER/REPO` (optional) — when omitted, the script resolves the repo via `gh repo view --json nameWithOwner`. Failure to resolve emits `HYDRATED=false ERROR=could not resolve repo …` and exits 0.

## Behavior

1. Create `anchor-hydrate/` and `anchor-sections/` (idempotent).
2. Fetch the anchor body via `gh api /repos/<repo>/issues/comments/<id> --jq '.body'` to `anchor-hydrate/anchor-body.md`.
3. Run an awk pass over the body matching `<!-- section:<slug> -->` / `<!-- section-end:<slug> -->` open/close markers, writing the interior of each matched range to `anchor-sections/<slug>.md`. Empty sections produce empty files. Slug extraction uses portable `sub`-based parsing (no gawk-only `match($0, /…/, m)` 3-arg form), so the script runs unchanged on macOS BSD awk.
   Both open and close slugs are accepted only when they are present in the canonical `SECTION_MARKERS` allowlist from `scripts/anchor-section-markers.sh` and contain no `/`, `\`, or `..` bytes. Rejected slugs do not enter section state and never participate in output-path construction.
4. Emit `HYDRATED=true` and `SECTIONS=<count>` on success.

## Best-effort contract

`/implement` SKILL.md treats hydration failure as non-fatal — the next progressive upsert overwrites whatever local state exists, and any failure is logged to the `Warnings` section of `execution-issues.md`. Accordingly, `hydrate-anchor.sh` **always exits 0** so callers branch on the `HYDRATED=` envelope key rather than `$?`. The failure cases are:

- empty `--anchor-id` (`anchor-id-empty`)
- unresolvable repo (`could not resolve repo …`)
- failed `mkdir -p` (`cannot create hydrate/sections directories …`)
- failed `gh api` (`gh api fetch failed for comment …`)
- empty fetched body (`empty anchor body`)
- missing marker helper (`missing helper: …`)
- awk extraction crash (`awk section extraction failed`)

## When to update

Update this file when the marker format changes (currently `<!-- section:<slug> -->` / `<!-- section-end:<slug> -->`), when the awk extractor becomes more sophisticated, or when the `gh` fetch path changes (e.g., switching to `gh api graphql`). The marker format is shared with `scripts/assemble-anchor.sh` and `scripts/anchor-section-markers.sh` — any change to the marker syntax MUST land in all three files in the same PR. Edit-in-sync rule applies.

## Test harness

`scripts/test-hydrate-anchor.sh` is the sibling offline regression harness. It stubs `gh` on `PATH`, feeds a fixture containing canonical, unknown, and traversal-shaped markers, and asserts that hydration creates only allowlisted section fragments without clobbering traversal canaries. The harness is wired through `make test-hydrate-anchor` and the `make test-harnesses` shard set.
