# scripts/gh-run-logs.sh — contract

`scripts/gh-run-logs.sh` wraps `gh run view --log-failed` for the `/implement` Step 10 / 12c CI-failure-diagnosis path. Output is unstructured log text on stdout (NOT `KEY=value`) capped at the last 100 lines via `tail -100` to prevent arbitrarily large logs from flooding the orchestrator context. A pointer comment is prepended on its own line before the log excerpt:

```
--- CI log (run <RUN_ID>, repo <REPO>) — last 100 lines shown. Full log: https://github.com/<REPO>/actions/runs/<RUN_ID> ---
```

Exit 0 on success (even when the full log has no failed-step lines), 1 on usage / `gh` failure, 2 when the run is still in progress (transient polling state — the "is still in progress; logs will be available" message was detected in `gh run view` output). Callers MUST treat exit 2 as a non-failure to avoid logging spurious CI Issues entries. If `gh run view` succeeds but produces zero lines of failed output, only the pointer comment appears on stdout.
