### OOS_1: TSV omits cache_create_effective while ratio uses it
- **Description**: TSV omits cache_create_effective while ratio uses it. Scenario: The export lists raw cache_create plus split columns and ratio, but not the effective numerator. Downstream readers dividing cache_create by cache_read will disagree with ranked ratio when legacy combined cache_create is nonzero and split buckets are zero (common on claude_sub).
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: python/larch/report/tokens.py
- **Phase**: design




Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

### OOS_2: TSV exports raw `cache_create` plus split columns while `ratio` uses `_cache_create_effective`
- **Description**: TSV exports raw `cache_create` plus split columns while `ratio` uses `_cache_create_effective`. Scenario: Downstream readers recomputing `cache_create` / `cache_read` from exported bucket columns will disagree with ranked `ratio` and order, especially for `claude_sub` and legacy per-step rows where split buckets are zero but combined `cache_create` is nonzero.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: python/larch/report/tokens.py:_render_cache_efficiency_tsv
- **Phase**: design




Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

### OOS_3: Issue titles are copied into the per-run TSV without TAB or newline sanitization
- **Description**: Issue titles are copied into the per-run TSV without TAB or newline sanitization. Scenario: `RunRecord.title` comes from manifest text and can contain tabs or newlines, which can break naive TSV parsers or shift columns for operators opening the outlier table.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/larch/report/tokens.py:_render_cache_efficiency_tsv
- **Phase**: design

Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

