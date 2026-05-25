### [Plan Review] FINDING_14

### FINDING_14: Breadcrumb-monitor mode selection is not observable
- **Reviewer(s)**: Codex-dyn-monitor-shell-bridge
- **Severity**: latent
- **Concern**: The sibling documentation does not require a state machine or diagnostics for primary-vs-fallback activation, making tests unable to prove which mode produced near-instant output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-monitor-shell-bridge: Require breadcrumb-monitor.md to define a mode-selection state machine, observable diagnostics such as MODE=monitor or MODE=fallback in test mode, activation thresholds, and which latency assertions apply to each mode


