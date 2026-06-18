### OOS_5:
- **Description**: [OUT_OF_SCOPE] Partial annotate failure can leave a non-empty OOS sentinel that a later prepare treats as complete. Scenario: If /larch:issue creates one OOS issue and another fails, annotate writes oos-issues-created.md before returning nonzero; a rerun can then hit skip-sentinel and never re-file the failed OOS block
- **Reviewer**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/design_oos.py:415-421; skills/design/scripts/design-step5b-annotate.sh:139-145; skills/design/scripts/design-step5b-prepare.sh:151-153
- **Phase**: design
