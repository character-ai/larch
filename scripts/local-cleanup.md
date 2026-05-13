# scripts/local-cleanup.sh — contract

`scripts/local-cleanup.sh` is the post-merge local-tidy-up step invoked by `/implement` Step 14: switch to `main`, fetch + reset to `origin/main`, then delete the feature branch named via `--branch`. Treats branch deletion failure as non-fatal (the branch may already be gone, e.g. if the operator manually deleted it). Refuses to run with `--branch main` for safety. Outputs `CLEANUP_SUCCESS=true|false`, `CURRENT_BRANCH=<name>`, `BRANCH_DELETED=true|false` so the caller can report partial-success warnings without interrupting the post-merge flow.

Step 3 uses `git fetch origin main && git reset --hard origin/main` instead of `git pull` so the operation is unconditionally fast-forward-safe regardless of local divergence (e.g. orphaned commits from a prior stalled run). The fetch is best-effort; a fetch failure leaves the local `origin/main` ref at its prior value, which is still safe to reset to. Reset failure exits 0 with `CLEANUP_SUCCESS=false`.
