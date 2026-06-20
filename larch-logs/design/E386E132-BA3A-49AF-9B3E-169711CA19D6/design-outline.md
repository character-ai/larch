## Proposed Design Outline

### Goals
- Stop `WARN_PLAN_FILES_UNTOUCHED` firing for plan files the plan itself marks optional.
- Add a `### MAY_UPDATE: <path>` scope heading recognized across the plan-grammar consumers.
- Keep the warning firm for unconditional `### NEW: / ### UPDATED: / ### REWRITTEN:` paths.

### Non-goals
- No change to gating; the coverage diagnostic stays warn-only.
- No retroactive re-flagging of old run logs or existing `### UPDATED:` conditional plans.
- No new dirty-tree or `plan scope-paths` behavior beyond recognizing the keyword.

### Approach sketch
- Teach `issue_wire.extract_scope_paths` to recognize `MAY_UPDATE`, gated by a new `include_optional` param (default: include).
- `implement_dispatch._explicit_plan_scope_paths` calls it with optional excluded, so coverage skips MAY_UPDATE paths.
- Add `MAY_UPDATE` to the `plan_quality.py` plan-size heading counter so optional files still count.
- Update /design authoring (`design_lifecycle.py`), reviewer grammar note (`rendering.py`), and `docs/issue-anchored-plan.md`.

### Surfaces in scope
- `python/issue_wire.py`, `python/implement_dispatch.py`, `python/plan_quality.py`
- `python/design_lifecycle.py`, `python/rendering.py`
- `docs/issue-anchored-plan.md`, `skills/design/references/readability-style.md`
- Tests: `python/test_issue_wire.py`, `python/test_implement_dispatch.py`, `python/test_plan_quality.py`

### Open questions
- None.
