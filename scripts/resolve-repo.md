# resolve-repo.sh contract

## Purpose

`scripts/resolve-repo.sh` prints the current GitHub repository as `OWNER/REPO` for scripts that must pass an explicit `--repo` to `gh pr` / `gh issue` calls.

## Resolution Order

1. `gh repo view --json nameWithOwner --jq '.nameWithOwner'`
2. `git remote get-url origin`, normalized from common GitHub SSH and HTTPS URL forms

If both sources fail or the resolved value is not shaped like `OWNER/REPO`, the script exits non-zero and emits `ERROR=could not resolve repo (gh repo view + git remote both failed)` on stderr.

## Output

Success writes exactly one line on stdout:

```
OWNER/REPO
```

## Primary Callers

Shell helpers under `scripts/` and `skills/*/scripts/` use this wrapper before repo-targeted `gh pr` / `gh issue` calls. Callers that can degrade in offline harnesses may treat a non-zero exit as an empty repo and omit `--repo`; callers that need `repos/$REPO/...` API paths fail closed when resolution fails.

## Test Harness

`scripts/test-resolve-repo.sh` covers `gh repo view` success, git remote fallback, and complete resolution failure.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.
