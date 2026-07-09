### OOS_1: [OUT_OF_SCOPE] The degraded write-failure path still appends issue detail after the existing summary body, so the new “summary last” contract is lost when `_write_enriched_post_publish_summary` hits OSError.
- **Description**: [OUT_OF_SCOPE] The degraded write-failure path still appends issue detail after the existing summary body, so the new “summary last” contract is lost when `_write_enriched_post_publish_summary` hits OSError.. Scenario: If the enriched rewrite fails, the fallback body can still publish `## /design run ...` before `## Review Phase Detail` and `## Exec Issues and Warnings`.
- **Reviewer**: Codex-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/design/design_summary.py:313-330
- **Phase**: design



