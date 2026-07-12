### FINDING_1: Suppression grammar must preserve the established `: ok` contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: The suppression contract is underspecified unless it requires Python comment-token matching with the repo-wide `# <token>: ok <non-empty-reason>` grammar. Without that constraint, implementations may accept unsupported forms, reject existing suppressions, or mishandle bare `: ok` pragmas that should produce exit code 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin suppression to the established reason grammar: scan only Python comment tokens, match `#\s*{re.escape(suppression_token)}:\s*ok\s+(\S.*)$` for a non-empty reason, and treat `#\s*{token}:\s*ok\s*$` as exit `2`. Reference `lint_unreachable_branch._suppression_reason` / `PRAGMA_RE` and `EMPTY_PRAGMA_RE` as the normative pattern in Approach step 10 and the engine.py suppression helper bullet.
  - From Cursor-Innovation: Specify suppression as #{ws}{suppression_token}: ok {non-empty-reason} inside tokenize COMMENT tokens, with bare : ok (no reason) as exit 2; add tests that use the exact token strings future rules will register
  - From Cursor-Pragmatic: Mirror PRAGMA_RE/EMPTY_PRAGMA_RE: accept only # <suppression_token>: ok <non-empty-reason> inside tokenize comment tokens; treat : ok with empty reason as exit 2


### FINDING_5: Specify the deterministic finding sort key
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: “Stable repository-relative fields” does not uniquely define ordering, so implementations may produce different deterministic outputs for the same findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Tie-break explicitly as (path, line, rule_id, message) before rendering path:line: RULE_ID message


