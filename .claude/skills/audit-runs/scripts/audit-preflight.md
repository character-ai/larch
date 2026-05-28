# .claude/skills/audit-runs/scripts/audit-preflight.sh — contract

Requires `--skill <design|implement>`. Concurrency guard is shared across skills (label `audit-report`).

Pre-flight checks for `/audit-runs`. Runs git fetch/pull, repo-identity verification, and concurrency guard.

## Output KV (stdout)

```
PREFLIGHT_OK=true|false
REASON=<empty when ok; human-readable message when false>
```

Normal outcomes exit `0`; caller reads `PREFLIGHT_OK` from stdout. **Unknown argv** (unrecognized flags/arguments) exits `1` with a stderr-only diagnostic — do not assume exit `0` implies a successful preflight parse.

## Steps

1. **Git sync**: always `git fetch origin main`. If the current branch is `main`, then `git pull --ff-only origin main` (fails closed when the tree is dirty or the branch cannot fast-forward). On a non-`main` branch, if local `main` exists and is strictly behind `origin/main` (fast-forwardable), fail with guidance to update `main` first; otherwise continue without pulling `main` automatically.
2. Repo-identity: normalize `git remote.origin.url` and `gh repo view REPO --json url` to `owner/repo` and require an exact match (mismatch `REASON` names the normalized pair).
3. Concurrency guard: list `audit-report` issues with `--json number,createdAt`, filter via `jq` against `now − 5 minutes` (macOS-portable date). Skip when `--allow-concurrent`.

## Edit-in-sync

Update tests in `test-audit-runs.sh` (preflight section) when behavior changes.
