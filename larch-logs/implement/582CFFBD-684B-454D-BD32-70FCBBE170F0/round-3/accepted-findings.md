### FINDING_10: oos-silent-drop inline triage can false-pass from unrelated parent-repo commits when artifacts are missing
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Fallback scans `merge-base..HEAD` of the parent repo when transcript artifacts are missing, so partial/copied run logs without `session-transcript` / `codex-commit-message` can yield a misleading pass.
- **Suggested revision**: Return zero, skip, or restrict logging to paths under `RUN_DIR` when artifacts are absent unless the run directory is an isolated git root; avoid parent-repo history as evidence in that mode.


