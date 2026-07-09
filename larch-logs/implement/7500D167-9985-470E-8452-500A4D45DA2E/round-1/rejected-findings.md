### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: definition-header traversal and regex call-site coverage are incomplete
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: The walker stops before visiting function/class header expressions, and regex match sites are only examined through the first positional argument, so valid literal sites on those AST surfaces can be missed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Keep the nested-scope recursion, but also walk the definition's other child expressions before returning, or restructure the walker so only the body gets a fresh scope and every other child node still gets visited.
  - From codex-specialist-edge-cases: Walk function/class header expressions separately from bodies, and inspect the relevant regex keyword arguments instead of only node.args[0].


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (0 YES)

### FINDING_4: scan_file silently skips unreadable or unparseable files
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Returning an empty finding list on syntax or I/O errors can hide lifecycle-prefix violations in that file and make check mode look clean when it is not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (0 YES)

### FINDING_5: keyword-only literal call arguments bypass prefix and regex checks
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-plan-fidelity-auto, dyn-dyn-ast-ratchet
- **Severity**: major
- **Concern**: `_call_contexts` only inspects positional arguments, so keyword-only string literals passed to prefix methods or regex helpers are skipped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Also scan relevant node.keywords with _literal_values / _regex_literal_matches and add keyword-only pytest coverage
  - From cursor-specialist-plan-fidelity-auto: Also inspect node.keywords for string-literal values on prefix methods and re compile/search/match/fullmatch; add tests for keyword-only fixtures.
  - From dyn-dyn-ast-ratchet: Add a small helper that collects string literals from both `node.args` and `node.keywords` (match `arg is None` for `re.compile(..., flags=…)` and `arg == "prefix"`/`"pat"` for prefix methods, or accept any keyword whose value is a string/tuple/list/set literal), then run the existing matchers on those values.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (0 YES)

### FINDING_6: bare imported regex helpers are skipped
- **Reviewer(s)**: dyn-dyn-ast-ratchet
- **Severity**: major
- **Concern**: Regex detection is limited to `re.<fn>(…)`, so bare imported helpers such as `compile(...)` or `search(...)` are missed even though they are valid string-literal regex match sites.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-ast-ratchet: Also accept `ast.Name` callees whose `id` is in `REGEX_FUNCTIONS` when the name is unbound in-file or treat both `re.fn` and imported `fn` forms, with tests for `from re import compile as _compile`.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** dismissed (0 YES)

### FINDING_10: duplicate live-identity coverage is missing
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: There is no coverage for the fail-closed path that rejects duplicate live identities, so a walker regression could emit duplicate keys without a tested exit-2 guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add fixtures that produce duplicate (file, qualified_symbol, token, constant, context, occurrence) keys and assert main() returns 2 with duplicate live identity stderr in check and --write modes.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

