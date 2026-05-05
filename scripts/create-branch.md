# scripts/create-branch.sh — contract

`scripts/create-branch.sh` is the branch-state probe and branch-creator used by `/design` Step 1, `/implement` Step 1 (which delegates the branch decision to `/design` in normal mode and replicates it inline in quick mode), and `/fix-issue` (indirectly via `/implement`). Two modes:

- `--check` — read-only probe. Emits `CURRENT_BRANCH`, `IS_MAIN`, `IS_USER_BRANCH`, `USER_PREFIX` (derived from `git config user.name`). No side effects.
- `--branch <name>` — create a new branch from latest `origin/main` (fetches first). Emits `BRANCH_NAME=<name>`.

`USER_PREFIX` is the kebab-case form of `user.name` and is the canonical owner-prefix for new branches (e.g. `sergey-zhupanov/<feature>`); skills compose `<USER_PREFIX>/<short-feature-name>` when on `main`. `IS_USER_BRANCH=true` when `CURRENT_BRANCH` already starts with `<USER_PREFIX>/`. Detached-HEAD also reports `IS_MAIN=true` (no current branch); callers handle that path by creating a new branch from `origin/main`. The script is invoked early in every long-running skill so the rest of the run can assume a clean feature-branch state.
