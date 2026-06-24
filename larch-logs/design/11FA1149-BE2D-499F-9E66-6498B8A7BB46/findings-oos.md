### OOS_1: [OUT_OF_SCOPE] Stale docs and prompt surfaces still say pruning uses unweighted accepted-minus-rejected counts after the weighted-net change
- **Description**: [OUT_OF_SCOPE] Stale docs and prompt surfaces still say pruning uses unweighted accepted-minus-rejected counts after the weighted-net change. Scenario: After this PR lands, reviewers and operators can read prompt text or docs that contradict the live prune gate, then debug or optimize against the wrong signal
- **Reviewer**: Codex-Generic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/rendering.py:887; skills/shared/voting-protocol.md:196-198; docs/configuration-and-permissions.md:272; docs/point-competition.md:20,117
- **Phase**: design



