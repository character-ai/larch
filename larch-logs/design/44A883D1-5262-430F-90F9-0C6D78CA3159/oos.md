### OOS_1: [OUT_OF_SCOPE] The docs-sync stale-phrase list does not cover the worded phrase `four static specialists per vendor`.
- **Description**: [OUT_OF_SCOPE] The docs-sync stale-phrase list does not cover the worded phrase `four static specialists per vendor`.. Scenario: A future reintroduction of the old public wording could pass the documentation harness.
- **Reviewer**: Codex-Innovation
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: scripts/test-quick-mode-docs-sync.sh:96-101; scripts/test-quick-mode-docs-sync.md
- **Phase**: design




Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### OOS_2: `review.panel` embedded `doc_fallback` still documents MODERATE Codex `gpt-5.6-luna`
- **Description**: `review.panel` embedded `doc_fallback` still documents MODERATE Codex `gpt-5.6-luna`. Scenario: The plan updates hand-maintained docs and `skills/implement/SKILL.md`, but leaves `ROLE_DEFAULTS["review.panel"].doc_fallback` describing MODERATE luna pairs. Registry readers can see stale routing after MODERATE moves to terra.
- **Reviewer**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: python/larch/core/config.py:483
- **Phase**: design

Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

