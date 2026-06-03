# scripts/promote-release.sh — contract

`scripts/promote-release.sh` promotes a GitHub Release to "Latest" and clears its pre-release flag by semver version number. Used to designate which release appears on the repo's front page.

## Purpose

The operator-run `/release` skill (`release-finish.sh`) creates the tag and GitHub Release and normally promotes to "Latest" in the same run (it invokes `promote-release.sh` at the end of `release-finish.sh`). This script also promotes an existing version to "Latest" and clears any pre-release flag when used standalone (retry after partial finish, legacy releases, or promote-only).

## Usage

```bash
scripts/promote-release.sh 12.4.5
scripts/promote-release.sh 12.4.5 --repo OWNER/REPO
```

The argument is a bare semver (`X.Y.Z`) — no `v` prefix. The script prepends `v` internally.

Optional `--repo OWNER/REPO` threads through every `gh release view`, `gh release list`, and `gh release edit` call. When omitted, `gh` uses the current repository (existing callers unchanged). `/release` (`release-finish.sh`) must pass the same `REPO` as all other release `gh` steps.

## Behavior

1. Validates the argument matches `^[0-9]+\.[0-9]+\.[0-9]+$`.
2. Checks that `v<VERSION>` exists as a GitHub Release via `gh release view`.
3. Queries `gh release list --json tagName,isLatest` to find the current "Latest" release.
4. If `v<VERSION>` is already "Latest", prints a message and exits 0.
5. Otherwise, runs `gh release edit v<VERSION> --latest --prerelease=false` to promote it (marks as latest and clears the pre-release flag).

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Release promoted (or already latest) |
| 1 | Release not found or `gh` error |
| 2 | Usage / argument error |

## Dependencies

- `gh` — authenticated with repo access

## Edit-in-sync

- `scripts/promote-release.sh` — the script itself
- `.claude/skills/release/scripts/release-finish.sh` — creates the tag and Release during `/release`; this script promotes to Latest (also invoked at the end of `release-finish.sh`)
- `docs/installation-and-setup.md` — documents the "Latest" release concept and version pinning
