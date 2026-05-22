# promote-latest-release.sh contract

`.claude/skills/release/scripts/promote-latest-release.sh` promotes the newest non-draft release in `character-ai/larch` for consumption. It is invoked only by the private `.claude/skills/release/SKILL.md` workflow.

## Behavior

The script queries GitHub releases with `gh release list --exclude-drafts --limit 100`, sorts by `publishedAt` descending in jq, and selects the newest non-draft release. On a live run, if that release is already `isPrerelease=false` and `isLatest=true`, the script prints `RELEASE_ALREADY_LATEST=true` and exits without calling `gh release edit`. Otherwise it prints `RELEASE_ALREADY_LATEST=false`, runs `gh release edit <tag> --prerelease=false --latest`, then verifies the result via `gh release list` scoped to non-draft releases and confirms `isPrerelease=false` and `isLatest=true`.

It prints machine-readable key-value lines on stdout:

- **Prelude (every successful live run; also the full stdout set for `--dry-run` except `DRY_RUN=true` is appended):** `RELEASE_REPO`, `RELEASE_TAG`, `RELEASE_PUBLISHED_AT`, `RELEASE_WAS_PRERELEASE`, `RELEASE_WAS_LATEST` (in that order).
- **After the prelude on a live run:** `RELEASE_ALREADY_LATEST` (`true` or `false`; omitted on `--dry-run`).
- **Post-edit verification (live runs only, and only when `RELEASE_ALREADY_LATEST=false`):** `RELEASE_IS_PRERELEASE`, `RELEASE_IS_LATEST`. These keys are absent when `RELEASE_ALREADY_LATEST=true` (early exit) and absent on `--dry-run`.

Failure diagnostics are `ERROR=` lines on stderr with a non-zero exit.

## Flags

- `--repo OWNER/REPO`: override the target repository. Default: `character-ai/larch`.
- `--dry-run`: print the selected release and original state without editing.
- `--help`: print usage.

## Invariants

- Draft releases are ignored.
- When the script performs `gh release edit`, that edit is followed by a verification query before the script exits 0. When the release is already latest and not a pre-release, the script skips the edit and exits 0 after printing `RELEASE_ALREADY_LATEST=true`.
- The script depends on `gh` and `jq`; it fails before mutation if either binary is unavailable.

## Edit-in-sync

When changing CLI flags, output keys, release-selection semantics, or verification behavior, update `.claude/skills/release/SKILL.md` and this sibling contract in the same change. Run `bash scripts/relevant-checks.sh` after edits.
