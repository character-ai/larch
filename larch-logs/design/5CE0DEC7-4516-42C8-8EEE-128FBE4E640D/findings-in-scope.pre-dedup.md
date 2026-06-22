### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/file_oos.py:672-731
- **Concern**: Rollup path omits parse-input malformed semantics and title normalization. Scenario: Plan lists malformed-item and markdown-normalization bash fixtures, but `issue_cap` still builds rollups from `_parse_oos_blocks` raw heading titles and full regex bodies; it never uses `ParsedItem.malformed` or `_normalize_rollup_text` on titles, so `case-malformed-no-body` and `case-markdown-normalization` will fail after pytest migration
- **Proposed resolution**: In `### UPDATED: python/file_oos.py`, drive keep/roll item lists from `parse_issue_input` (use `ParsedItem.malformed` for `(malformed item — body unavailable)`, description body for excerpt/file-refs, `_normalize_rollup_text` on rollup titles); drop `_parse_oos_blocks` from the cap-exceeded path



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/file_oos.py:672-684
- **Concern**: Rollup loop lacks malformed-item handling the bash fixtures require. Scenario: Plan lists malformed OOS cases but `_aggregate_block` still walks `_parse_oos_blocks` items and always excerpts raw block text; bash emits `(malformed item — body unavailable)` when parse-input has no body file. Migrated `case-malformed-no-body` fails.
- **Proposed resolution**: In `issue_cap`, build surplus rollups from `parse_issue_input` `ParsedItem` rows (or equivalent): when `item.malformed` or body empty, emit the bash placeholder and skip excerpt/file-ref extraction.



### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic Phase2
- **Severity**: important
- **Focus area**: security
- **Location**: python/file_oos.py:648-656
- **Concern**: OOS cap plan does not pin the retired helper's file-reference extraction contract to the shared voting regex plus safe-path filter. Scenario: The deleted Bash helper extracted refs with python/cli.py voting file-line-regex and rejected absolute, dash-prefixed, and .. paths. The current Python helper uses a narrower bespoke regex, so root-level refs like README.md or Makefile can be dropped, while unsafe refs after the excerpt cutoff can be surfaced in the aggregate Files suffix.
- **Proposed resolution**: Port _file_refs_from_body to use voting.FILE_LINE_REGEXES any-re plus extensionless-re and the Bash clean_match/path_is_safe filtering before deleting the helper.



### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/file_oos.py:672-731
- **Concern**: Plan omits rollup bullet composition parity for capped items. Scenario: Current `issue_cap` validates with `parse_issue_input` but builds rollups from `_parse_oos_blocks` heading titles and raw block bodies; Bash uses parser `ITEM_*_TITLE` / body files with title normalization, `(malformed item — body unavailable)` fallback, and full-body file-ref scan. Listed fixtures (malformed with/without body, markdown normalization, file refs after excerpt cutoff) fail without this change.
- **Proposed resolution**: Add to `### UPDATED: python/file_oos.py`: rollup bullets must derive normalized title, excerpt, and file refs from `parse_issue_input` item fields (matching the deleted shell loop), not `_parse_oos_blocks` alone.



### FINDING_5:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-oos-issue-cap.sh:384-407
- **Concern**: Parser/heading parity stderr text not specified for pytest migration. Scenario: Existing fixture asserts stderr contains `ITEMS_TOTAL`; planned `_validate_issue_cap_input` raises `parsed item count (...) != raw ...` with no `ITEMS_TOTAL` token. Migrated parity tests fail unless error text or assertions are aligned.
- **Proposed resolution**: In `python/file_oos.py` updates, require parity errors include `ITEMS_TOTAL` wording (or document updating the migrated pytest assertion to match the new message).



### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_file_oos.py:29-53
- **Concern**: `case-warning-string-consistency` fixture not listed for migration. Scenario: Acceptance requires existing oos-issue-cap fixtures pass; Bash harness case at test-oos-issue-cap.sh:426-442 verifies the operator warning string in config docs and deleted helper files. Plan test list omits this case, so acceptance can pass pytest while dropping the warning-string contract.
- **Proposed resolution**: Add a migrated pytest case asserting the unchanged warning string remains in `docs/configuration-and-permissions.md` (and any other surviving canonical prose surface after deletions).



### FINDING_7:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/file_oos.py:648-656; skills/implement/scripts/oos-issue-cap.sh:173-198
- **Concern**: Plan preserves simplified Python file-ref extraction instead of the Bash/voting regex contract. Scenario: A capped rolled-up item whose body mentions README.md:12 or Makefile after the excerpt cutoff loses the [Files:] suffix, while the retired helper would preserve it; downstream file-conflict deps may miss same-file serialization for the aggregate
- **Proposed resolution**: In python/file_oos.py, replace the _FILE_REF_RE loop with voting.FILE_LINE_REGEXES any-re plus extensionless-re matching and the Bash clean/safe/sort-dedupe behavior; aim the existing migrated file-reference fixture at a root-level or extensionless file ref after cutoff



