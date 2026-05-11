# scripts/gh-run-logs.sh — contract

`scripts/gh-run-logs.sh` wraps `gh run view --log-failed` for the `/implement` Step 10 / 12c CI-failure-diagnosis path. Output is unstructured log text on stdout (NOT `KEY=value`) capped at the last 100 lines to prevent arbitrarily large logs from flooding the orchestrator context. A pointer comment is prepended with the full-artifact URL (`https://github.com/<repo>/actions/runs/<id>`) so the orchestrator can surface the link when surfacing CI failures. Exit 0 on success, 1 on usage / `gh` failure.
