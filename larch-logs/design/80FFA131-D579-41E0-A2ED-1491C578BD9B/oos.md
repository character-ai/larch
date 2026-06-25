### OOS_1: Leave hardcoded plan-review panel matrix in loaded SKILL prose
- **Description**: Leave hardcoded plan-review panel matrix in loaded SKILL prose. Scenario: `skills/design/SKILL.md` still describes the static Cursor/Codex panel shape. The registry centralizes Python dispatch; duplicating the matrix in SKILL is optional and was rejected as in-scope churn in round 3.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md
- **Phase**: design




Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted

### OOS_2: `DecomposePanelPolicy.archetypes` duplicates `DECOMPOSE_ARCHETYPES`
- **Description**: `DecomposePanelPolicy.archetypes` duplicates `DECOMPOSE_ARCHETYPES`. Scenario: The plan adds a fourth archetype list inside registry metadata while `python/decompose.py` keeps `DECOMPOSE_ARCHETYPES` as the dispatch loop source.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: python/config.py:97-100
- **Phase**: design




Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

### OOS_3: [OUT_OF_SCOPE] Keep the brainstorm slot matrix out of prose
- **Description**: [OUT_OF_SCOPE] Keep the brainstorm slot matrix out of prose. Scenario: The visible table and launch fences remain a second source of truth and can drift from external-defaults role even after the registry lands.
- **Reviewer**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/brainstorm.md:46-85
- **Phase**: design

Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

