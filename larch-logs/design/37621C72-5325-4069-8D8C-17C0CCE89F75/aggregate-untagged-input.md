### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/design/decompose.py:336-339
- **Concern**: The decompose update requires byte-compatible placeholder output while delegating to compose_named_block, which cannot reproduce the current blank line before the end marker.. Scenario: compose_named_block strips trailing newlines from inner and appends exactly one newline before <!-- larch:plan:end -->. The inline placeholder today has two newlines after the prose line (one blank line). An implementer chasing byte-compatible may fight compose_named_block or hand-compose markers again.
- **Proposed resolution**: Revise the decompose bullet: drop unconditional byte-compatible wording for inner newlines; state that visible fence and prose must match, allow one newline delta before the end marker, and golden-pin the exact fenced block in test_decompose.py after switching to compose_named_block.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/design/design_router.py:128-132
- **Concern**: Plan edge case requires empty valid plan blocks to route already-planned but test_design_lifecycle.py additions omit that case. Scenario: An implementer may use if plan_inner: instead of plan_inner is not None and treat <!-- larch:plan:start -->\n<!-- larch:plan:end --> as unplanned
- **Proposed resolution**: Add one routing test with an empty-inner valid plan block asserting ROUTE=already-planned. In design_router.py use plan_inner is not None (or malformed == "" and plan_inner is not None).

### FINDING_4:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/issue/issue_wire.py:54-56
- **Concern**: The planned multiline public regex reuses `\s*`, which can consume newlines and accept a marker whose syntax is split across multiple lines.. Scenario: An issue body containing `<!--\nlarch:plan:start -->` can be treated as a valid marker by `diagnostic_prefix` or `parse_named_block`, causing diagnostic text to be truncated or `/design` to report `already-planned` for malformed input.
- **Proposed resolution**: Use horizontal whitespace in the public line-anchored expression, such as `[ \t]*`, and add a regression case proving that marker syntax split across lines is rejected while ordinary whitespace-tolerant single-line markers remain accepted.

### FINDING_5:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/design/design_router.py:128
- **Concern**: Router plan-presence check must use `is not None`, not truthiness. Scenario: `parse_named_block` returns `("", "")` for an empty but valid `larch:plan` block; `if inner:` treats that as absent and routes to `proceed` instead of `already-planned`, contradicting the plan edge case
- **Proposed resolution**: In the `design_router.py` UPDATED bullets, require `inner, _malformed = issue_wire.parse_named_block(body=body, marker="plan"); has_plan = inner is not None`

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/design/test_design_lifecycle.py
- **Concern**: Mandated router tests omit empty valid plan-block coverage. Scenario: Edge cases require empty valid blocks to count as planned and failure modes warn against truthiness, but the listed new tests only cover whitespace tolerance and malformed/incomplete blocks; a truthiness regression would slip through
- **Proposed resolution**: Add a routing test with body `<!-- larch:plan:start -->\n<!-- larch:plan:end -->` (or whitespace-tolerant equivalent) and assert `ROUTE=already-planned`

### FINDING_7:
- **Reviewer(s)**: Cursor-dyn-Marker Contract Auditor
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/design/test_design_lifecycle.py:plan
- **Concern**: Empty valid plan block routing test omitted from test plan. Scenario: Edge cases require empty but valid `larch:plan` blocks to route `already-planned` because `parse_named_block` returns `("", "")`. Failure modes warn against truthiness checks, but the listed router tests cover whitespace tolerance and malformed/incomplete blocks only. An `if plan_inner:` guard would send empty plans to `proceed` instead of `already-planned`.
- **Proposed resolution**: Add an explicit `design route` case with body `<!-- larch:plan:start -->\n<!-- larch:plan:end -->` asserting `ROUTE=already-planned`, plus a negative control with only a start marker.

### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-Marker Contract Auditor
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/design/design_router.py:128-132
- **Concern**: Plan does not mandate `is not None` presence check in the router edit step. Scenario: The `### UPDATED: design_router.py` section says to use `parse_named_block` but does not spell out `has_plan = plan_inner is not None`. The current substring check at line 128 is truthy in spirit; swapping to `if plan_inner:` after parse would mishandle empty valid blocks even though edge cases and failure modes describe the trap.
- **Proposed resolution**: In the `design_router.py` plan bullet, require `plan_inner, malformed = issue_wire.parse_named_block(...); has_plan = plan_inner is not None` (malformed already yields `None`) and forbid truthiness on `plan_inner`. ## Findings ### 1. correctness — `python/tests/design/test_design_lifecycle.py` (plan) The plan’s edge cases and failure modes correctly state that empty but valid plan blocks must route to `already-planned`, and that presence must use `is not None`. The `### UPDATED: python/tests/design/test_design_lifecycle.py` section does not list an empty-block routing case. Without it, the truthiness regression called out in failure modes is easy to ship. **Suggested revision:** Add a `design route` test whose body is only start/end markers with no inner lines; assert `ROUTE=already-planned`. ### 2. correctness — `python/larch/design/design_router.py:128-132` (`route_main`) Today `route_main` uses a paired substring check: has_plan = "<!-- larch:plan:start -->" in body and "<!-- larch:plan:end -->" in body if has_clarify: route = "clarify" elif has_plan: route = "already-planned" The plan correctly moves this to `issue_wire.parse_named_block` and excludes the `design-pause` literal at line 85. It does not, in the file edit bullets, require the non-truthiness guard. That gap matters because `parse_named_block` returns `""` for empty valid blocks (`test_compose_named_block_strips_trailing_lf` in `test_issue_wire.py`). **Suggested revision:** In the `design_router.py` plan step, specify `has_plan = plan_inner is not None` explicitly. ## Assessment summary The plan otherwise aligns with the issue scope and minimum-change intent: - All three verified bypass sites (`decompose.py:336-339`, `learn_from_bugs.py:66`, `design_router.py:128`) are covered. - `named_block_marker_re` with `re.MULTILINE`, routing `_line_is_marker` through it, and consumer delegation match current `issue_wire` grammar (`issue_wire.py:54-59`). - `learn_from_bugs` keeps heading fallbacks; only the lax case-insensitive partial plan regex is removed. - `design-pause` substring routing at `design_router.py:85` is correctly left alone. - Post-change grep for runtime `larch:plan:start` literals is appropriate; remaining hits are tests, fixtures, or `issue_wire` ownership. - `decompose.py` newline drift is already acknowledged in failure modes with a compose spy test; no extra scope needed. No other in-scope gaps found for plan grammar changes, pause-path edits, or fourth runtime bypass sites.

### FINDING_9:
- **Reviewer(s)**: Codex-dyn-Marker Contract Auditor
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/issue/issue_wire.py:54-59 (_marker_re/_line_is_marker)
- **Concern**: Public `named_block_marker_re` must preserve full-line matching when used with `re.MULTILINE`, but reusing the existing `\s*` expression allows newline characters inside the marker line.. Scenario: `learn_from_bugs.diagnostic_prefix()` can treat a malformed marker split across two lines, such as `<!-- larch:plan:start\n -->`, as a valid boundary, while `parse_named_block()` processes lines individually and rejects it. This violates the plan's malformed-marker contract and makes public and internal recognition diverge.
- **Proposed resolution**: Use whitespace classes that exclude `\r` and `\n` in the shared expression, route both public and internal matching through it, and add a regression case proving a split-line marker is rejected.
