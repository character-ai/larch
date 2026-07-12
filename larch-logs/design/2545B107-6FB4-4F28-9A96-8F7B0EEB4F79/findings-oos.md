### OOS_1: ok() will sit beside gh_result with the same success CommandResult shape
- **Description**: ok() will sit beside gh_result with the same success CommandResult shape. Scenario: Adding ok() without making gh_result delegate to it leaves two one-line success factories that future edits can drift apart
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: python/test_support.py:108-110
- **Phase**: design



