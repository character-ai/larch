# .claude/skills/audit-runs/scripts/audit-preflight.sh — contract

Pre-flight checks for `/audit-runs`. Runs git fetch/pull, repo-identity verification, and concurrency guard.

## Output KV (stdout)

```
PREFLIGHT_OK=true|false
REASON=<empty when ok; human-readable message when false>
```

Normal outcomes exit `0`; caller reads `PREFLIGHT_OK` from stdout. **Unknown argv** (unrecognized flags/arguments) exits `1` with a stderr-only diagnostic — do not assume exit `0` implies a successful preflight parse.

## Steps

1. `git fetch origin main && git pull --ff-only` — fails closed if tree is dirty.
2. Repo-identity: compare `gh repo view -R REPO --json url` hostname with `git remote.origin.url`.
3. Concurrency guard: list `audit-report` issues with `--json number,createdAt`, filter via `jq` against `now − 5 minutes` (macOS-portable date). Skip when `--allow-concurrent`.

## Edit-in-sync

Update tests in `test-audit-runs.sh` (preflight section) when behavior changes.
