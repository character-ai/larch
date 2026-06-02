# release-finish.sh — contract

Publish tail for `/release`: resolve the squash-merge commit, verify `plugin.json` version, ensure tag + GitHub Release, then promote to Latest.

## Usage

```bash
.claude/skills/release/scripts/release-finish.sh \
  --version <X.Y.Z> \
  --notes-file <path> \
  --repo OWNER/REPO \
  --pr <N>
```

## `TARGET_OID` resolution

1. Prefer `gh pr view <pr> --json mergeCommit -q .mergeCommit.oid` when non-empty.
2. Else `git fetch origin main` and `git rev-parse origin/main^{commit}`.

Do not use a stale local `refs/heads/main` after the release branch merge.

## Fail-closed version check

`git show "$TARGET_OID:.claude-plugin/plugin.json" | jq -r .version` must equal `--version` before any tag push.

## Tag idempotency

- Remote tag on a **different** OID → exit **1** (fail closed).
- Local/remote tag already on `TARGET_OID` → skip create; push only when remote lacks the tag.
- Otherwise create annotated/lightweight tag at `TARGET_OID` and `git push origin`.

## GitHub Release

- `gh release create v<version> --title v<version> --notes-file <file> --repo <repo>` when absent.
- `gh release edit` with the same `--notes-file` when the release already exists (e.g. `release-tag.yaml` race).

## Promote

Calls `scripts/promote-release.sh <version> --repo <repo>` so Latest matches the same hub repo as all other `gh` steps.

## Outputs (stdout KV)

`TARGET_OID`, `TAG`, `VERSION`, and `RELEASE_ACTION=create|edit`.

## Edit-in-sync

- `.claude/skills/release/scripts/release-finish.sh`
- `scripts/promote-release.sh` (`--repo` passthrough)
- `.claude/skills/release/SKILL.md` Step 6
