### OOS_1:
- **Description**: Phased static Codex fallback fixtures (`codex-specialist-security-output-phase2.txt` and `.meta`, included) are added to the harness, but neither doc-update section says to document phased static Codex inclusion in `scripts/test-larch-log-write-round.md` (larch-log.md already covers this at lines 28-29).. Scenario: The harness doc will assert phased static Codex inclusion without describing it; same pre-existing gap as phased Cursor (already tested at test-larch-log-write-round.sh:125).
- **Reviewer**: Cursor-dyn-doc-narrative-sync
- **Severity**: latent
- **Focus area**: correctness
- **Location**: plan.txt:31-34 vs plan.txt:36-40
- **Phase**: design

