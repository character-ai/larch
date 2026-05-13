# scripts/local-cleanup.sh — contract

`scripts/local-cleanup.sh` is the post-merge local-tidy-up step invoked by `/implement` Step 14: switch to `main`, fetch + pull latest, then delete the feature branch named via `--branch`. Treats branch deletion failure as non-fatal (the branch may already be gone, e.g. if the operator manually deleted it). Refuses to run with `--branch main` for safety. Outputs `CLEANUP_SUCCESS=true|false`, `CURRENT_BRANCH=<name>`, `BRANCH_DELETED=true|false` so the caller can report partial-success warnings without interrupting the post-merge flow.
