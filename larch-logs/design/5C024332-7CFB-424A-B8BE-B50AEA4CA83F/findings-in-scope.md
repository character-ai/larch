### FINDING_1: Suppression grammar must preserve the established `: ok` contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: The suppression contract is underspecified unless it requires Python comment-token matching with the repo-wide `# <token>: ok <non-empty-reason>` grammar. Without that constraint, implementations may accept unsupported forms, reject existing suppressions, or mishandle bare `: ok` pragmas that should produce exit code 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin suppression to the established reason grammar: scan only Python comment tokens, match `#\s*{re.escape(suppression_token)}:\s*ok\s+(\S.*)$` for a non-empty reason, and treat `#\s*{token}:\s*ok\s*$` as exit `2`. Reference `lint_unreachable_branch._suppression_reason` / `PRAGMA_RE` and `EMPTY_PRAGMA_RE` as the normative pattern in Approach step 10 and the engine.py suppression helper bullet.
  - From Cursor-Innovation: Specify suppression as #{ws}{suppression_token}: ok {non-empty-reason} inside tokenize COMMENT tokens, with bare : ok (no reason) as exit 2; add tests that use the exact token strings future rules will register
  - From Cursor-Pragmatic: Mirror PRAGMA_RE/EMPTY_PRAGMA_RE: accept only # <suppression_token>: ok <non-empty-reason> inside tokenize comment tokens; treat : ok with empty reason as exit 2

### FINDING_2: Keep comment tokenization self-contained in `engine.py`
- **Reviewer(s)**: Cursor-Innovation, Cursor-Arch
- **Severity**: major
- **Concern**: The plan simultaneously references `lint_unreachable_branch._comment_tokens_by_line` and prohibits imports from existing lint entry points. This leaves the implementation path ambiguous and risks either violating the import constraint or reimplementing tokenization without a pinned contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pin an inline private _comment_tokens_by_line helper in engine.py (tokenize.generate_tokens COMMENT extraction) and drop the cross-module reference; keep the no-import-from-lint-entry-points rule
  - From Cursor-Arch: Pin suppression to the established reason grammar: scan only Python comment tokens, match `#\s*{re.escape(suppression_token)}:\s*ok\s+(\S.*)$` for a non-empty reason, and treat `#\s*{token}:\s*ok\s*$` as exit `2`. Reference `lint_unreachable_branch._suppression_reason` / `PRAGMA_RE` and `EMPTY_PRAGMA_RE` as the normative pattern in Approach step 10 and the engine.py suppression helper bullet.

### FINDING_3: Normalize repository-root paths before comparison
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: minor
- **Concern**: Comparing the raw `git rev-parse --show-toplevel` string with the supplied root can reject valid roots that are relative, have trailing separators, or use a different lexical representation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Compare Path(root).resolve() to Path(rev_parse_line).resolve(); document that symlink-normalization follows pathlib resolve semantics
  - From Cursor-Pragmatic: Normalize both sides with Path(...).resolve() (same pattern as larch/git/repo_roots.py) before comparing toplevel to root

### FINDING_4: Define the accepted `Finding.metric` type and validation
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The plan requires validation of invalid metrics but does not define the valid metric domain, allowing incompatible implementations to disagree about whether integers, floats, zero, or negative values are accepted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pin Finding.metric as int | None (non-negative when present) to match complexity-baseline usage, or explicitly document the accepted numeric type and rejection cases in step 9 and the test section

### FINDING_5: Specify the deterministic finding sort key
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: “Stable repository-relative fields” does not uniquely define ordering, so implementations may produce different deterministic outputs for the same findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Tie-break explicitly as (path, line, rule_id, message) before rendering path:line: RULE_ID message
