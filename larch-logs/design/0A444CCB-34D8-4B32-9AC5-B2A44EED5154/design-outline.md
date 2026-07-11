## Proposed Design Outline

### Goals
- Add a second fail-closed-language check to `lint_agent_tool_contract.py`, the follow-up the v1 module docstring reserved (I-Agent-1 backing, #6671).
- Record invariant I-Ship-1 in `ARCHITECTURAL_INVARIANTS.md` documenting the already-shipped PR-state guard (#6668/#6690).
- Record guideline G-Md-3 in `ARCHITECTURAL_GUIDELINES.md` for structured bug-report sections.

### Non-goals
- No new CLI flags, baselines, or config; the new lint check keeps the existing "no baseline by policy" stance.
- No code changes for Part 2; the invariant documents enforcement that already landed.
- No changes to unrelated lint checks, invariants, or guidelines.

### Approach sketch
- Part 1 (lint): extend `scan_file`'s tail past the v1 early-return so the v2 check runs independently; add `OUTPUT_MANDATE_RES`/`FAIL_CLOSED_RES` detectors and a `Finding.message` field, per the issue's verbatim code.
- Part 2 (invariant): append the verbatim I-Ship-1 block after `## Agent contracts` (confirmed the file's last section).
- Part 3 (guideline): append the verbatim G-Md-3 block after `### G-Md-2`, before `## Migration discipline` (confirmed exact anchor and spacing).
- The three parts touch disjoint files with no shared risk; land as one plan/change.

### Surfaces in scope
- `python/larch/lint/lint_agent_tool_contract.py`
- `python/tests/lint/test_lint_agent_tool_contract.py`
- `docs/linting.md`
- `ARCHITECTURAL_INVARIANTS.md`
- `ARCHITECTURAL_GUIDELINES.md`

### Open questions
- None.
