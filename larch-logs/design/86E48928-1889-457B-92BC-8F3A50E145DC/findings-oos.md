### OOS_1: Renderer default-path derivation duplicates explicit --findings-ledger-file wiring at every dispatch site
- **Description**: Renderer default-path derivation duplicates explicit --findings-ledger-file wiring at every dispatch site. Scenario: Every production dispatch path already plans explicit flag passing plus Codex sentinel FINDINGS_LEDGER_FILE; fallback derivation in three renderers adds ~60 lines and a second resolution surface without a caller that omits flags
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/rendering.py:76-84
- **Phase**: design



