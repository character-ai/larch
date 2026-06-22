### OOS_1: [OUT_OF_SCOPE] Capped aggregate retry evidence can retain only the first source stable ID
- **Description**: [OUT_OF_SCOPE] Capped aggregate retry evidence can retain only the first source stable ID. Scenario: When issue_cap rewrites seven accepted blocks into one aggregate, _stable_ids_by_combined_item is computed from the pre-cap combined_text. A retry after filing can match persisted evidence to only the first original block and re-file the rolled-up remainder.
- **Reviewer**: Cursor-Pragmatic Phase2
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/oos_filer.py:786-806
- **Phase**: design
