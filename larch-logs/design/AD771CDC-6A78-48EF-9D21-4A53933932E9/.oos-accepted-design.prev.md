### OOS_1:
- **Description**: `${OUTPUT}.sidecar` source order misses custom stderr sinks. Scenario: Launchers that redirect CLI stderr elsewhere (`launch-codex-implement.sh`/`launch-cursor-implement.sh` `--sidecar-log`, `lint-fix-loop.sh` `codex.wrapper.log`) never populate `${OUTPUT}.sidecar`; the planned first-existing source is often `.diag` wrapper text, not agent stderr—undercutting “all lanes” foreground coverage outside `launch-review.sh`/`launch-codex-ci.sh`
- **Reviewer**: unknown-slot
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/run-external-agent.sh:67-71
- **Phase**: design

