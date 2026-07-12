### OOS_1: `progress_report._extract_oos_block` still segments reviewer markdown with a per-id `(?ms)^### {id}:...(?=^### |\Z)` regex outside `review_types.py`.
- **Description**: `progress_report._extract_oos_block` still segments reviewer markdown with a per-id `(?ms)^### {id}:...(?=^### |\Z)` regex outside `review_types.py`.. Scenario: Design/progress security-OOS adjustment keeps a fourth segmentation implementation that the `python/larch` ratchet will not remove, so grammar can drift from the shared owner.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/report/progress_report.py:1389-1401
- **Phase**: design



### OOS_2: [OUT_OF_SCOPE] `progress_report._extract_oos_block` still segments canonical reviewer blocks locally
- **Description**: [OUT_OF_SCOPE] `progress_report._extract_oos_block` still segments canonical reviewer blocks locally. Scenario: `_extract_oos_block` builds a per-ID `(?ms)^### <id>:...(?=^### |\Z)` regex over round findings files for design security-OOS tally adjustment. It is outside the firm migration list and will remain a second segmentation owner after the ratchet lands.
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/report/progress_report.py:1389-1401
- **Phase**: design



### OOS_3: Migrate `progress_report._extract_oos_block` dynamic per-ID block regex
- **Description**: Migrate `progress_report._extract_oos_block` dynamic per-ID block regex. Scenario: `_extract_oos_block` builds `(?ms)^### {oos_id}:...` block matchers outside `review_types.py`. The planned AST lint likely misses this `re.compile(rf"...")` form, so it can survive migration as a hidden second owner and drift from shared fence and boundary rules.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/report/progress_report.py:1389-1401
- **Phase**: design



