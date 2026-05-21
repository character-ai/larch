---
name: release
description: "Use when publishing the newest character-ai/larch GitHub release for consumption: finds the latest non-draft release, clears pre-release, marks it as latest, then runs /upgrade-larch. Private to this larch repo; not plugin exported."
allowed-tools: Bash, Skill
disable-model-invocation: true
---

# Release

Publish the newest `character-ai/larch` GitHub release for consumption, then upgrade the local larch plugin install. This is a dev-only skill under `.claude/skills/release/`; it is not exported in the plugin package.

## Steps

1. Promote the latest non-draft GitHub release:

```bash
$PWD/.claude/skills/release/scripts/promote-latest-release.sh
```

On a live run, stdout always begins with this prelude (in order): `RELEASE_REPO`, `RELEASE_TAG`, `RELEASE_PUBLISHED_AT`, `RELEASE_WAS_PRERELEASE`, `RELEASE_WAS_LATEST`. After the prelude, if you see `RELEASE_ALREADY_LATEST=true`, the newest non-draft release is already promoted: the script exits without editing and does not emit `RELEASE_IS_PRERELEASE` / `RELEASE_IS_LATEST`. If you see `RELEASE_ALREADY_LATEST=false` instead, the script ran `gh release edit` (or is about to verify it) and then prints `RELEASE_IS_PRERELEASE=false` and `RELEASE_IS_LATEST=true`. With `--dry-run`, the script exits before editing and only prints the prelude keys plus `DRY_RUN=true` — do not expect `RELEASE_ALREADY_LATEST` or `RELEASE_IS_*` keys in that case. If the script prints an `ERROR=` line or exits non-zero, stop and surface the failure; do not run `/upgrade-larch`.

See `$PWD/.claude/skills/release/scripts/promote-latest-release.md` for the script contract and failure details.

2. Invoke `/upgrade-larch` via the Skill tool:

- Try skill: `"upgrade-larch"` first (bare name). If no skill matches, try skill: `"larch:upgrade-larch"` (fully-qualified plugin name).
- args: empty
- If neither name resolves, stop and report skill resolution failure. Do not attempt a different upgrade path.

After `/upgrade-larch` finishes successfully, tell the user to restart Claude Code so the upgraded plugin version is loaded.
