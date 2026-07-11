### OOS_3: G-Md-3 recommends reusing _balanced_fence_line_indices but the helper stays private
- **Description**: G-Md-3 recommends reusing _balanced_fence_line_indices but the helper stays private. Scenario: file_oos.py already imports it with reportPrivateUsage; a third consumer would repeat the private import pattern.
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/larch/issue/issue_create.py
- **Phase**: design

