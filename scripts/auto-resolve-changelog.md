# auto-resolve-changelog.sh

**Purpose**: Deterministic merge of a conflicted Keep-a-Changelog-style file during an in-progress `git rebase`, using index stages `:2:` (upstream / rebased-onto side) and `:3:` (the replayed commit side). Invoked by `scripts/ship-pr.sh` in `run_rebase_rebump` before launching external resolve-conflict vendors.

## Preconditions

- A rebase is in progress and the given path is in conflict (both `:2:` and `:3:` blobs exist).
- `git show ":2:PATH"` and `git show ":3:PATH"` must succeed; otherwise the script exits `1`.

## Format detection (basename of the conflict path)

| Basename ends with | Mode |
|--------------------|------|
| `.rst` | reStructuredText (first title + underline, then sections) |
| `.md` | Markdown (first line that starts with two `#` characters plus a space) |
| Anything else (e.g. `CHANGELOG` with no extension) | If **either** side contains at least one Markdown level-2 heading (a line matching the regex `^##` plus a single space after the hashes), Markdown mode is used **only** when both sides share the same first such heading; otherwise exit `1` (no silent fallback to RST). If **neither** side has any level-2 Markdown heading line, RST heuristics apply. |

This avoids mis-classifying Markdown logs without a shared first level-2 heading as RST when the path has no `.md` suffix.

## Markdown merge rule (level-2 headings)

1. Both sides must have the same first level-2 heading line (for example a shared `## Unreleased`). If the first heading is missing on either side or the two first headings differ, exit `1`.
2. Emit the upstream preamble (all lines before the first level-2 heading) unchanged.
3. Emit the shared first heading line once.
4. Under that heading, print every line from the upstream first section (lines after the first level-2 heading through the line before the next level-2 heading, or end of file if there is none), then append lines from the replayed side’s first section that are not already present (exact-line dedupe, upstream order first).
5. **Tail guard**: From the second level-2 heading through EOF, the `:2:` and `:3:` spans must be **identical** line-for-line (including when only one side has a second heading — then exit `1`). If they match, append that tail once from the upstream blob (the second heading through EOF).

## reStructuredText merge rule

1. Both sides must share the same detected first RST section title (title line plus adornment underline). Otherwise exit `1`.
2. Emit the upstream preamble through the first title and its underline.
3. Merge the first section body like Markdown (upstream lines first, then `:3:` lines not already seen, exact-line dedupe).
4. **Tail guard**: From the second RST section title onward, the `:2:` and `:3:` spans must be identical; otherwise exit `1`. If they match, append the upstream tail from the second title through EOF.

## Output

Writes the merged result to the working-tree path given as the sole argument (repo-relative as passed by the caller).

## Exit codes

- `0` — wrote merged changelog
- `1` — format/heading mismatch, tail mismatch between stages, unsupported extensionless mix, or `git show` failed (caller should defer to a human or vendor resolver)

## Test harness

`scripts/test-auto-resolve-changelog.sh` — offline regression harness. Wired as `make test-auto-resolve-changelog`.

## Edit-in-sync

`scripts/ship-pr.sh` (rebase conflict pre-pass), `scripts/test-ship-pr.sh` (fixtures that rely on the merge contract).
