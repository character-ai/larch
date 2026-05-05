# scripts/gh-pr-checks.sh — contract

`scripts/gh-pr-checks.sh` wraps `gh pr checks` and prints the raw checks output to stdout (NOT `KEY=value`) because callers parse the checks listing themselves to identify failed checks. Used as the fallback CI-diagnosis path in `/implement` Step 12c when `ci-status.sh`'s `FAILED_RUN_ID` is empty. Exit 0 on success, 1 on usage / `gh` failure.
