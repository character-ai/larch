### OOS_1: [OUT_OF_SCOPE] Duplicate voter payload wiring across two dispatch modules
- **Description**: [OUT_OF_SCOPE] Duplicate voter payload wiring across two dispatch modules. Scenario: `plan_review_panel.py` and `agent_voters.py` both hand-build per-tool voter manifests with nearly identical render-and-write loops; duplicating the new payload sidecar and `payload_files` logic in both places increases the 950-line diff and drift risk
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/agents/agent_voters.py:220-306
- **Phase**: design



