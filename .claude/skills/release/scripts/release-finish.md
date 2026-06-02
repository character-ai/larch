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

1. Poll `gh pr view <pr> --json mergeCommit -q .mergeCommit.oid` with bounded backoff (up to ~10s).
2. Missing `mergeCommit.oid` after merge → exit **1** with `ERROR=merge-commit-missing` (no `origin/main` fallback).

## Origin coupling

`origin` remote owner/repo must match `--repo` before any git or `gh` write.

## Notes redaction

`--notes-file` is piped through `scripts/redact-secrets.sh` before `gh release create` / `edit`.

## Fail-closed version check

`git show "$TARGET_OID:.claude-plugin/plugin.json" | jq -r .version` must equal `--version` before any tag push.

## Tag idempotency

- Remote tag on a **different** OID → exit **1** (fail closed).
- Local/remote tag already on `TARGET_OID` → skip create; push only when remote lacks the tag.
- On push failure, re-check remote tag at `TARGET_OID` and continue when it matches (TOCTOU vs `release-tag.yaml`).
- Otherwise create tag at `TARGET_OID` and `git push origin`.

## GitHub Release

- `gh release create v<version> --title v<version> --notes-file <file> --repo <repo>` when absent.
- `gh release edit` with the same `--notes-file` when the release already exists (e.g. `release-tag.yaml` race).

## Promote

Calls `scripts/promote-release.sh <version> --repo <repo>` so Latest matches the same hub repo as all other `gh` steps.

## Outputs (stdout KV)

On exit **0** only (after `promote-release.sh` succeeds): `RELEASE_ACTION=create|edit`, then `TARGET_OID`, `TAG`, `VERSION`. Promote failure exits **1** before any success KV lines.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Tag/release/promote succeeded; full KV set on stdout |
| 1 | Operational/`gh`/git/promote failure |
| 2 | Usage or validation error |

## Edit-in-sync

- `.claude/skills/release/scripts/release-finish.sh`
- `scripts/promote-release.sh` (`--repo` passthrough)
- `.claude/skills/release/SKILL.md` Step 6
