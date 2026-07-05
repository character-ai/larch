# Review Round 1

- Mode: `diff`
- 2 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_2: sink matcher misses real output paths
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-correctness, codex-specialist-edge-cases, dyn-dyn-lint-scope
- **Severity**: important
- **Concern**: The sink matcher only covers a narrow subset of call shapes, so direct imports, bare helper names, wrapper chains, `_plain_diagnostic`, `_emit_kv`, `sys.stdout/stderr.write`, and `BreadcrumbWriter` aliases can still emit U+2014 undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Also treat bare Name callees emit emit_kv diagnostic as sinks or ban direct imports in favor of logging_util.*
  - From cursor-specialist-edge-cases: Extend sink tracking to out.append/extend→print chains, wrapper callees, and prompt constants; or document and test the explicit coverage boundary.
  - From cursor-specialist-edge-cases: Add bare-name sink detection for logging_util imports or enforce attribute-call style repo-wide.
  - From cursor-specialist-testing: Add failing fixtures for each listed sink plus clean-pass cases per the plan test matrix.
  - From cursor-specialist-testing: Add _plain_diagnostic to NAME_SINKS, scrub call sites, and add a unit test.
  - From cursor-specialist-testing: Recognize bare _emit_kv in _callee_is_sink with a unit test, or document the accepted blind spot.
  - From codex-specialist-correctness: Track local names assigned from `logging_util.BreadcrumbWriter()` / `BreadcrumbWriter()` and treat `.emit(...)` on those names as a sink. Add a regression test with a non-special receiver name.
  - From codex-specialist-edge-cases: Treat imported `logging_util` output helpers as sinks (import-aware matching), add `_plain_diagnostic` (and similar stderr wrappers) to the sink set, and cover module-local `emit()` helpers that delegate to `print`; add regression tests for each bypass class.
  - From dyn-dyn-lint-scope: Treat imported `logging_util` output helpers as sinks (import-aware matching), add `_plain_diagnostic` (and similar stderr wrappers) to the sink set, and cover module-local `emit()` helpers that delegate to `print`; add regression tests for each bypass class.


### FINDING_3: blockquote examples are linted
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases, codex-specialist-testing, dyn-dyn-lint-scope
- **Severity**: important
- **Concern**: Blockquote-prefixed instructional lines still get scanned, so quoted prose that contains a `Print:`/`print` template can fail even though the plan excludes quoted prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Ignore blockquote lines before applying `PRINT_TEMPLATE_RE` and the `⏩` status-line check. Add a regression test for a quoted print template with U+2014.
  - From codex-specialist-edge-cases: Skip lines whose first non-whitespace character is `>`, or restrict inline-template matching to lines that are clearly orchestrator print directives (for example `Print:` at line start), and add a blockquote regression test.
  - From codex-specialist-testing: Skip blockquote lines before print-template matching and add a regression test for quoted Print/print templates.
  - From dyn-dyn-lint-scope: Skip lines whose first non-whitespace character is `>`, or restrict inline-template matching to lines that are clearly orchestrator print directives (for example `Print:` at line start), and add a blockquote regression test.


