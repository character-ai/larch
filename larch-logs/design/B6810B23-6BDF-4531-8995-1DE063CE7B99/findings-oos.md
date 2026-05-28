### OOS_1:
- **Description**: WARN bullet still says Phase 3 fallback count drives threshold. Scenario: After the plan lands, /review can emit WARN=cost-fallback-exceeded-threshold when combined phase-2 fall-through plus phase-3 exceeds the threshold while FALLBACK_COUNT stays phase-3-only; readers of dispatch-panel.md will mis-tune LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD or mis-debug logs
- **Reviewer**: Cursor-dyn-kv-consumer-sync
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/review/scripts/dispatch-panel.md:17
- **Phase**: design

