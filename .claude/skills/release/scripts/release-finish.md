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

1. Poll `gh pr view <pr> --json mergeCommit -q .mergeCommit.oid` with bounded backoff (up to ~10s). `mergeCommit.oid` must match `^[0-9a-fA-F]{7,40}$` or it is treated as missing.
2. `git fetch origin main` immediately after the poll loop (surface `ERROR=fetch-failed` with stderr on failure).
3. Missing `mergeCommit.oid` after poll → use `origin/main^{commit}` as `TARGET_OID` when `plugin.json` `.version` equals `--version`; otherwise exit **1** with `ERROR=merge-commit-missing`.
4. Resolve `TARGET_OID` with repeated `git fetch origin main` (same backoff) until the OID is local and on `origin/main`; SHA-only `git fetch origin <oid>` is a last resort with distinct `ERROR=target-oid-not-on-origin-main` vs `ERROR=fetch-failed`.

## Origin coupling

`origin` remote owner/repo must match `--repo` before any git or `gh` write.

## Notes redaction

`--notes-file` is piped through `scripts/redact-tmpdir-paths.sh` then `scripts/redact-secrets.sh` before `gh release create` / `edit`.

## Fail-closed version check

After `git fetch origin main` (or a direct fetch of `TARGET_OID` when `origin/main` is not yet at the merge commit), `git show "$TARGET_OID:.claude-plugin/plugin.json" | jq -r .version` must equal `--version` before any tag push. `LARCH_RELEASE_FINISH_AT_VERSION` (test harness only) must match the tree version when set; it does not bypass the plugin.json read.

## Tag idempotency

- Remote tag checks use peeled commit OIDs (`refs/tags/${TAG}^{}`) so annotated tags compare commit SHAs, not tag object SHAs.
- Remote tag on a **different** OID → exit **1** (fail closed) before release/promote steps.
- After every `ls-remote` probe that finds a remote tag, re-verify the peeled commit OID equals `TARGET_OID`.
- Local/remote tag already on `TARGET_OID` → skip create; push only when remote lacks the tag.
- Stale **local** tag on a different OID when **remote** tag already matches `TARGET_OID` → `git tag -f` realigns local ref and continue (idempotent re-run safety).
- On push failure, re-check remote tag at `TARGET_OID` and continue when it matches (concurrent-write / TOCTOU safety).
- Otherwise create tag at `TARGET_OID` and `git push origin`.

## Partial-failure recovery

If tag push and `gh release create`/`edit` succeed but `promote-release.sh` fails, the tag and GitHub Release exist but are not Latest. Re-run `release-finish.sh` with the same `--version`, `--notes-file`, `--repo`, and `--pr`: tag/release steps are idempotent when the remote tag and release already point at `TARGET_OID`, and only promote is retried. Alternatively invoke `scripts/promote-release.sh <version> --repo <repo>` directly for a promote-only retry.

If Step 6 failed after the release PR merged, a full `/release` re-run hits `ERROR=release-already-cut` in prepare — resume with `release-finish.sh` (or promote-only) instead.

## Remote tag OID mismatch

When `ERROR=remote tag … exists on different commit`, the peeled remote tag OID does not match `TARGET_OID`. Verify `git show "$TARGET_OID:.claude-plugin/plugin.json"` reports `.version` equal to `--version`. If a legacy or manual tag points at the wrong commit, delete or move the incorrect remote tag only with maintainer intent, `git fetch origin main`, then re-run `release-finish.sh` with the same arguments.

## GitHub Release

- `gh release create v<version> --title v<version> --notes-file <file> --repo <repo>` when absent.
- `gh release edit` with the same `--notes-file` when the release already exists (idempotent re-run).

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
