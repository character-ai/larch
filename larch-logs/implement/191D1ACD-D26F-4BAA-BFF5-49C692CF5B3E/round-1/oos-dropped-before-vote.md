### OOS_1: [OUT_OF_SCOPE] risk-integration: scripts/hook-bg-poll-guard.sh:547-567
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Probe-clamp can deny sentinel probes after marker removal when normalize-status fails without writing step-3-terminal. Orchestrator may still stall on recovery probes even though the bg wait ended; unlike the fixed bug, this does not recreate a live-marker denial on every tool call. Consider clearing probe-denial counters on marker removal or ensuring all terminal normalize paths mint hook-release sentinels; out of scope for this minimal fix per plan.
- **Suggested revision**: Address the concern above.

