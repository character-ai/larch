### OOS_1: [OUT_OF_SCOPE] Empty zero-byte sentinel file is not directly tested
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: nit
- **Concern**: The zero-byte `oos-issues-created.md` path is not explicitly covered by tests, even though the implementation currently returns `(0, "")` for an empty file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Add test_oos_info_empty_file with sentinel.write_text("") and assert (0, "").

### OOS_2: [OUT_OF_SCOPE] Render integration tests do not assert OOS CLI args
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The render integration tests do not assert `--oos-count` / `--oos-urls` CLI args, so a wiring regression could still surface as `OOS filed: 0` in summaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add one render_final_summary_main test with oos-issues-created.md fixture asserting run-summary args (optional hardening).

### OOS_3: [OUT_OF_SCOPE] OOS file-map field-count constant is duplicated
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: `_OOS_FILE_MAP_FIELD_COUNT` is duplicated from `design_oos.py`, so writer-format changes require manual sync across modules.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Share constant or a small parse helper from design_oos if drift becomes recurring.

