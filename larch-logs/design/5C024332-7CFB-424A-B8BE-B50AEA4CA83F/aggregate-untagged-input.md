### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/lint/engine.py
- **Concern**: Reason-bearing suppression grammar is underspecified relative to the repo-wide `: ok` contract. Scenario: Step 10 cites `lint_unreachable_branch._comment_tokens_by_line` for comment tokenization but not the paired `_suppression_reason` / `PRAGMA_RE` grammar. All three migration-target lints match `# {token}: ok {reason}` and treat bare `# {token}: ok` as an empty-reason error. A generic trailing-text matcher would reject existing suppressions or accept tokens in executable code with trailing text, breaking contract-unification piece 1.
- **Proposed resolution**: Pin suppression to the established reason grammar: scan only Python comment tokens, match `#\s*{re.escape(suppression_token)}:\s*ok\s+(\S.*)$` for a non-empty reason, and treat `#\s*{token}:\s*ok\s*$` as exit `2`. Reference `lint_unreachable_branch._suppression_reason` / `PRAGMA_RE` and `EMPTY_PRAGMA_RE` as the normative pattern in Approach step 10 and the engine.py suppression helper bullet.

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/lint/engine.py
- **Concern**: Step 10 names lint_unreachable_branch._comment_tokens_by_line while engine.py forbids imports from existing lint entry points. Scenario: An implementer cannot follow both constraints: either import a lint module (violating the no-import rule) or reimplement tokenization without a pinned contract, risking drift from the three migration-target lints
- **Proposed resolution**: Pin an inline private _comment_tokens_by_line helper in engine.py (tokenize.generate_tokens COMMENT extraction) and drop the cross-module reference; keep the no-import-from-lint-entry-points rule

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/engine.py
- **Concern**: Suppression grammar omits the repo-wide : ok infix used by unreachable-branch, markdown-heading-fence-state, and self-disarmable-gate. Scenario: Matching only suppression_token plus any trailing reason in a comment allows grammars like # lint-foo reason that none of the target lints use; piece 2 equivalence would need per-rule adapters or a breaking engine change
- **Proposed resolution**: Specify suppression as #{ws}{suppression_token}: ok {non-empty-reason} inside tokenize COMMENT tokens, with bare : ok (no reason) as exit 2; add tests that use the exact token strings future rules will register

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/lint/engine.py
- **Concern**: Git work-tree root check does not require lexical resolve() before comparing rev-parse output to supplied root. Scenario: git rev-parse --show-toplevel returns an absolute path while root may be relative or differently normalized; strict string equality rejects valid work-tree roots and fails acceptance tests on ordinary cwd layouts
- **Proposed resolution**: Compare Path(root).resolve() to Path(rev_parse_line).resolve(); document that symlink-normalization follows pathlib resolve semantics

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/lint/engine.py
- **Concern**: Plan-mandated invalid-metric tests lack a defined valid metric type. Scenario: Step 9 requires a supported coherent metric and tests reject invalid values, but never states the accepted type; two strict implementations can disagree (int-only vs int|float vs rejecting zero) while both claim compliance
- **Proposed resolution**: Pin Finding.metric as int | None (non-negative when present) to match complexity-baseline usage, or explicitly document the accepted numeric type and rejection cases in step 9 and the test section

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/engine.py
- **Concern**: Finding sort comparator tuple is unspecified. Scenario: Tests require deterministic ordering across shuffled discovery and detector output, but "stable repository-relative fields" allows multiple valid orderings and different stdout
- **Proposed resolution**: Tie-break explicitly as (path, line, rule_id, message) before rendering path:line: RULE_ID message

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/engine.py
- **Concern**: Suppression comment grammar omits the established : ok token. Scenario: Plan only requires a trailing reason inside comment tokens; implementations may match bare suppression_token text and diverge from lint_unreachable_branch and sibling pragma shape (# token: ok reason)
- **Proposed resolution**: Mirror PRAGMA_RE/EMPTY_PRAGMA_RE: accept only # <suppression_token>: ok <non-empty-reason> inside tokenize comment tokens; treat : ok with empty reason as exit 2

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/lint/engine.py
- **Concern**: Git root equality lacks explicit path normalization. Scenario: rev-parse may return /repo while the supplied root is /repo/ or a relative equivalent; strict string equality rejects a valid work-tree root before discovery
- **Proposed resolution**: Normalize both sides with Path(...).resolve() (same pattern as larch/git/repo_roots.py) before comparing toplevel to root
