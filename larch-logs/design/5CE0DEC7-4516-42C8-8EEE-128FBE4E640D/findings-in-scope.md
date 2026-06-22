### FINDING_1: Rollup path omits `parse_issue_input` semantics for capped items
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: blocking
- **Concern**: `issue_cap` validates with `parse_issue_input` but, on cap exceed, builds keep/roll lists and rollup bullets from `_parse_oos_blocks` raw heading titles and regex block bodies. It never applies `ParsedItem.malformed`, the `(malformed item — body unavailable)` placeholder, `_normalize_rollup_text` on titles, or parser-sourced description bodies for excerpts/file refs. Migrated fixtures (`case-malformed-no-body`, `case-malformed-with-body`, `case-markdown-normalization`, file refs after excerpt cutoff) will fail after pytest migration unless rollup composition matches the retired Bash loop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `### UPDATED: python/file_oos.py`, drive keep/roll item lists from `parse_issue_input` (use `ParsedItem.malformed` for `(malformed item — body unavailable)`, description body for excerpt/file-refs, `_normalize_rollup_text` on rollup titles); drop `_parse_oos_blocks` from the cap-exceeded path
  - From Cursor-Innovation: In `issue_cap`, build surplus rollups from `parse_issue_input` `ParsedItem` rows (or equivalent): when `item.malformed` or body empty, emit the bash placeholder and skip excerpt/file-ref extraction.
  - From Cursor-Requirements: Add to `### UPDATED: python/file_oos.py`: rollup bullets must derive normalized title, excerpt, and file refs from `parse_issue_input` item fields (matching the deleted shell loop), not `_parse_oos_blocks` alone.

### FINDING_2: File-reference extraction diverges from voting regex and safe-path contract
- **Reviewer(s)**: Cursor-Pragmatic Phase2, Codex-Generic
- **Severity**: important
- **Concern**: The plan leaves `_file_refs_from_body` on a narrower bespoke `_FILE_REF_RE` instead of porting the retired Bash helper’s contract: `voting.FILE_LINE_REGEXES` (any-re plus extensionless-re), `clean_match`, `path_is_safe` filtering (reject absolute, dash-prefixed, and `..` paths), and sort/dedupe. Root-level or extensionless refs (e.g. `README.md:12`, `Makefile`) after the excerpt cutoff can be dropped from the `[Files: …]` suffix, while unsafe refs may still surface; downstream file-conflict dependency planning can miss same-file serialization for the aggregate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic Phase2: Port _file_refs_from_body to use voting.FILE_LINE_REGEXES any-re plus extensionless-re and the Bash clean_match/path_is_safe filtering before deleting the helper.
  - From Codex-Generic: In python/file_oos.py, replace the _FILE_REF_RE loop with voting.FILE_LINE_REGEXES any-re plus extensionless-re matching and the Bash clean/safe/sort-dedupe behavior; aim the existing migrated file-reference fixture at a root-level or extensionless file ref after cutoff

### FINDING_3: Parser/heading parity stderr text not aligned for pytest migration
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The retired harness `case-parser-heading-parity-mismatch-cap-*` asserts stderr contains `ITEMS_TOTAL`. Planned `_validate_issue_cap_input` raises `parsed item count (...) != raw ...` with no `ITEMS_TOTAL` token. Migrated parity tests fail unless error text or pytest assertions are explicitly aligned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: In `python/file_oos.py` updates, require parity errors include `ITEMS_TOTAL` wording (or document updating the migrated pytest assertion to match the new message).

### FINDING_4: `case-warning-string-consistency` fixture omitted from migration plan
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Acceptance requires existing oos-issue-cap fixtures pass. The Bash harness case at `test-oos-issue-cap.sh:426-442` verifies the operator warning string in config docs and the helper files slated for deletion. The plan’s test migration list omits this case, so acceptance can pass pytest while dropping the warning-string contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add a migrated pytest case asserting the unchanged warning string remains in `docs/configuration-and-permissions.md` (and any other surviving canonical prose surface after deletions).
