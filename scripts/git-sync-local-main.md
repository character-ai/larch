# scripts/git-sync-local-main.sh — contract

`scripts/git-sync-local-main.sh` fast-forwards the local `main` ref to `origin/main` (silent no-op if local `main` does not exist). It supports CI-fix rebase and release/version classification callers that need merge-base computations to resolve against the latest remote base rather than a stale local `main`. The script does NOT check out `main`: it advances the ref via `git fetch origin main:main` (when the working tree is on a feature branch) or via `git pull --ff-only` semantics (when already on `main`).
