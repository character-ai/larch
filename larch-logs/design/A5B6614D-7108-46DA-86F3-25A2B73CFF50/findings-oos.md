### OOS_1: [OUT_OF_SCOPE] Reassessment prose still centers optional invalidate before Phase A reruns
- **Description**: [OUT_OF_SCOPE] Reassessment prose still centers optional invalidate before Phase A reruns. Scenario: The plan updates conflict-resolution reassessment to `prepare`, but the SKILL.md reassessment paragraph still treats standalone `architectural-guidelines invalidate` as the outside-subsection hook while Phase A entry clearing is authoritative. After the fold, that prose can steer reruns toward invalidate-only cleanup instead of the single prepare fence, partially undoing the turn savings.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:791
- **Phase**: design



### OOS_2: [OUT_OF_SCOPE] Harness still lacks anti-rm-loop prose pin
- **Description**: [OUT_OF_SCOPE] Harness still lacks anti-rm-loop prose pin. Scenario: The plan adds a literal check for prepare exit-code routing but not the `do not add an orchestrator-side rm loop` guard that prevented #5365-style regression. A future SKILL revert could reintroduce orchestrator `rm` without CI failure.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/test-architectural-guidelines-step.sh
- **Phase**: design



