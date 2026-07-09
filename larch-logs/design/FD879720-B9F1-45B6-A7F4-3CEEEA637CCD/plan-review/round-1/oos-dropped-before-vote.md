### OOS_2: No max length on validate_run_id
- **Description**: No max length on validate_run_id. Scenario: session_env allows 128 characters; unbounded IDs are unlikely to break paths here but diverge from the eventual RUN_ID source.
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/larch/report/progress_file.py
- **Phase**: design

### OOS_3: Cleanup does not remove empty clone directories after the last aged run dir is deleted
- **Description**: Cleanup does not remove empty clone directories after the last aged run dir is deleted. Scenario: Empty per-clone directories may linger under ~/.cache/larch/progress after retention. Harmless cache clutter with no effect on dormant behavior.
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/larch/report/progress_file.py
- **Phase**: design

