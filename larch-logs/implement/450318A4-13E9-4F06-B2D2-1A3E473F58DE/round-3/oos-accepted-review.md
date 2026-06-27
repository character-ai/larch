### OOS_5: risk-integration: python/larch/state/session_env.py:953-959
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] REPO_ROOT recovery now writes whatever repo_roots.consumer_repo_root() returns from the current cwd into source-env.sh when env anchors are absent. If session setup runs from the plugin checkout, source-env.sh can persist the plugin repo as the design root, so later calibration resolution trusts the wrong larch-logs tree or loses feedback. Only persist REPO_ROOT when it is known to point at the consumer checkout, or leave it unset and let the later resolver walk the other anchors.
- **Suggested revision**: Address the concern above.


