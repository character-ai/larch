### OOS_1: [OUT_OF_SCOPE] Bash `ship-pr.sh` still defaults missing `LAUNCHER_EXIT` to `0`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `scripts/ship-pr.sh:2493-2494,1720-1721,2876-2877`: Bash CI/conflict launcher paths still default missing `LAUNCHER_EXIT` to `0` via `${launcher_exit:-0}` even when the wrapper exits non-zero without emitting the KV line. Python paths (`python/rebase.py`, `python/ci_monitor.py`) now fail closed through `agents.resolve_launcher_exit`, but the legacy bash `ship-pr.sh` waterfall retains the original misclassification gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: When `LARCH_SHIP_PR_IMPL=bash`, mirror `resolve_launcher_exit` semantics (prefer `.done`, then parsed stdout, then `max(wrapper_rc, 1)` on failure).


