## Decision 1: Which remediation options are in-scope?
- **Question**: A only / A+B / A+C / A+B+C?
- **Resolution**: A + B + C (maximally defensive). Wire test-design-structure.sh into relevant-checks.sh (A), add a new scripts/check-contains-pins.sh post-commit spot-check (B), and add Codex implementer prompt guidance (C).
- **Source**: user

## Decision 2: Scope of Option A's harness wiring
- **Question**: Wire only test-design-structure.sh into relevant-checks.sh, or all pin-heavy harnesses?
- **Resolution**: Only test-design-structure.sh. Other pin-heavy harnesses (test-anti-halt-banners.sh, test-prompt-template-invariants.sh, test-subskill-anchors.sh, etc.) are out of scope; they can be added later if a similar divergence recurs.
- **Source**: user

## Decision 3: Hard constraints (from codebase)
- **Question**: What existing infrastructure must not break?
- **Resolution**:
  - Bash 3.2 portability required for any new shell scripts (BASH_AUTHORING.md §3).
  - relevant-checks.sh case-statement pattern is the canonical file-trigger routing mechanism — new file patterns must follow the existing `append_target_once <make-target>` shape.
  - agents/codex-implementer.md is the canonical Codex implementer prompt source.
  - test-design-structure.sh already exists and is wired into `make test-design-structure` and `test-harnesses-14`; the implementation must add a `relevant-checks.sh` routing branch, NOT modify the existing test or Makefile target.
- **Source**: codebase

## Decision 4: Out-of-scope
- **Question**: What is explicitly NOT in scope?
- **Resolution**:
  - Refactoring test-design-structure.sh internals.
  - Changing how pre-commit hooks work.
  - Backfilling case branches for other pin-heavy harnesses.
- **Source**: user
