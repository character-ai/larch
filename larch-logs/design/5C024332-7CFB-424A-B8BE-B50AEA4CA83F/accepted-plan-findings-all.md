### FINDING_1: Syntax-policy fail orchestration is underspecified
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: The plan does not define how `syntax_policy=fail` interacts with lazy AST access and subsequent detector execution. A non-AST detector may omit syntax findings, while an AST-using detector may raise after a syntax finding is recorded, producing inconsistent behavior across rule types.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In run_rule, for .py sources with syntax_policy=fail, run a single pre-detect syntax probe (compile or ast.parse) before detect(); keep lazy ast caching for detectors that need the tree. skip may omit the file without calling detect().
  - From Codex-Innovation: Add an explicit orchestration contract. State whether fail/skip rules pre-parse Python sources or whether syntax policy applies only when AST access occurs. Align the tests with that choice, including an invalid-Python source handled by a non-AST detector.
  - From Cursor-Requirements: After recording one syntax finding for a source under `fail`, skip further work on that source (mirror `skip` omission) before calling `detect`; state this in Approach step 7 and `run_rule`


### FINDING_4: Syntax-error finding shape is unspecified
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The plan requires deterministic syntax findings but does not define their rule ID, message, or line normalization when `SyntaxError.lineno` is missing or invalid.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Fix the contract: use the active LintRule.rule_id, a fixed message such as "unable to parse Python", and normalize bad/missing lineno to line 1 (or last line), matching the edge-case rule.


### FINDING_7: Rendered output fields require single-line validation
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Concern**: The plan does not require all values used in rendered output to be non-empty single-line values. Newlines in a detector's `qualified_symbol`, a configured `rule_id`, or another rendered path/token could create multi-line output or inject additional records.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: A detector can return a qualified_symbol containing a newline, or a rule configuration can contain a newline in rule_id; deterministic `path:line: RULE_ID message` output then becomes multi-line or injects additional output records. Validate rule IDs, symbols, and every rendered path/token as non-empty single-line values before rendering.


### FINDING_8: Repository-root validation is incomplete
- **Reviewer(s)**: Codex-Arch, Codex-Requirements
- **Severity**: minor
- **Concern**: The plan does not explicitly verify that the supplied root is a Git work-tree root or define behavior for non-repository roots. Discovery from a nested directory or an injected successful runner can produce incorrect repository-relative paths or allow invalid roots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add an explicit repository-root check, define its injected-runner command and failure handling, and test non-repository roots separately from missing or non-directory roots


### FINDING_10: Suppression matching must inspect comments
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Concern**: Matching the suppression token anywhere on the physical source line can suppress findings when the token appears in code or a string literal, rather than in a comment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In Approach step 9 and the suppression helper, build per-line comment tokens (same pattern as `lint_unreachable_branch._comment_tokens_by_line`) and match `suppression_token` only inside those comments on the finding line


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


