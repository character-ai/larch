# promote-latest-release.sh contract

`.claude/skills/release/scripts/promote-latest-release.sh` promotes the newest non-draft release in `character-ai/larch` for consumption. It is invoked only by the private `.claude/skills/release/SKILL.md` workflow.

## Behavior

The script queries GitHub releases with `gh release list --exclude-drafts --limit 100`, sorts by `publishedAt` descending in jq, and selects the newest non-draft release. It then runs `gh release edit <tag> --prerelease=false --latest`. After editing, it verifies the result via `gh release list` scoped to non-draft releases and confirms `isPrerelease=false` and `isLatest=true`.

It prints machine-readable key-value lines on stdout:

- `RELEASE_REPO`
- `RELEASE_TAG`
- `RELEASE_PUBLISHED_AT`
- `RELEASE_WAS_PRERELEASE`
- `RELEASE_WAS_LATEST`
- `RELEASE_IS_PRERELEASE`
- `RELEASE_IS_LATEST`

Failure diagnostics are `ERROR=` lines on stderr with a non-zero exit.

## Flags

- `--repo OWNER/REPO`: override the target repository. Default: `character-ai/larch`.
- `--dry-run`: print the selected release and original state without editing.
- `--help`: print usage.

## Invariants

- Draft releases are ignored.
- The edit must be followed by a verification query before the script exits 0.
- The script depends on `gh` and `jq`; it fails before mutation if either binary is unavailable.

## Edit-in-sync

When changing CLI flags, output keys, release-selection semantics, or verification behavior, update `.claude/skills/release/SKILL.md` and this sibling contract in the same change. Run `/relevant-checks` after edits.
