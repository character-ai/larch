# scripts/gh-run-logs.sh — contract

`scripts/gh-run-logs.sh` wraps `gh run view --log-failed` for the `/implement` Step 10 / 12c CI-failure-diagnosis path. Output is raw unstructured log text on stdout (NOT `KEY=value`) because the log content is consumed by an AI-driven diagnosis pass that needs the full log surface. Exit 0 on success, 1 on usage / `gh` failure.
