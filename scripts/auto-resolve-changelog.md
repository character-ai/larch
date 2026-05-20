# auto-resolve-changelog.sh

**Purpose**: Deterministic merge of a conflicted Keep-a-Changelog-style file during an in-progress `git rebase`, using index stages `:2:` (upstream / rebased-onto side) and `:3:` (the replayed commit side). Invoked by `scripts/ship-pr.sh` in `run_rebase_rebump` before launching external resolve-conflict vendors.

## Preconditions

- A rebase is in progress and the given path is in conflict (both `:2:` and `:3:` blobs exist).
- Both sides share the same first Markdown level-2 heading: a line starting with two `#` characters followed by a space and the title (for example an `Unreleased` section). If the first heading is missing on either side or the two first headings differ, the script exits `1` so the vendor can resolve.

## Merge rule

1. Emit the upstream preamble (all lines before the first level-2 heading) unchanged.
2. Emit the shared first heading line once.
3. Under that heading, print every line from the upstream first section (lines after the first level-2 heading through the line before the next level-2 heading, or end of file), then append lines from the replayed side’s first section that are not already present (exact-line dedupe, upstream order first).
4. Append the remainder of the **upstream** file from its second level-2 heading through EOF (including that heading). If upstream has only one such section, there is no tail.

## Output

Writes the merged result to the working-tree path given as the sole argument (repo-relative as passed by the caller).

## Exit codes

- `0` — wrote merged changelog
- `1` — headings mismatch / missing, or `git show` failed

## Test harness

`scripts/test-auto-resolve-changelog.sh` — offline regression harness. Wired as `make test-auto-resolve-changelog`.

## Edit-in-sync

`scripts/ship-pr.sh` (rebase conflict pre-pass), `scripts/test-ship-pr.sh` (fixtures that rely on the merge contract).
