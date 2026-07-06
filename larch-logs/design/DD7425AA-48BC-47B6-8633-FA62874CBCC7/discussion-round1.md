## Decision 1: Reviewer surfaces that receive the knowledge files + rubric carve-out
- **Question**: Which reviewer surfaces should treat documented `G-*`/`I-*` violations as in-scope and receive both `ARCHITECTURAL_GUIDELINES.md` and `ARCHITECTURAL_INVARIANTS.md`?
- **Resolution**: BOTH the code reviewers (`/implement` Step 5 and `/review`) AND the `/design` Step 3 plan-review reviewers. The rubric carve-out lives in the shared `skills/shared/reviewer-templates.md` (so it reaches all generated archetypes), and both files are wired as explicit reviewer inputs on the code-review path and the plan-review path.
- **Source**: user

## Decision 2: Coder acknowledgment enforcement
- **Question**: Should the Step 2 coder's one-line acknowledgment (e.g. "honoring I-Sec-1, G-Py-4") be visible-only, or mechanically verified?
- **Resolution**: Mechanically verified. The dispatcher (or a check) validates that the acknowledgment is present in the coder's output/manifest and warns/fails when it is missing. This touches the dispatch/manifest layer and applies uniformly across the Step 2 implementer types (Claude, Codex, Cursor) that emit a manifest/output.
- **Source**: user

## Decision 3: Invariant mechanical backstop (lint/hook/test)
- **Question**: Should this issue add any lint/hook/test backstop for invariants now?
- **Resolution**: Deferred. This issue delivers the reader + coder-feed + reviewer-rubric wiring only. Per-invariant backstops land later when actual invariants are written; nothing to enforce against a blank `ARCHITECTURAL_INVARIANTS.md`.
- **Source**: user

## Decision 4: Confirmed non-goals (from the issue's Out of scope)
- **Question**: What stays out of scope?
- **Resolution**: (a) Populating `ARCHITECTURAL_INVARIANTS.md` with actual invariants (the blank seed lands via its own PR/tracking issue #6467/#6468). (b) Reader/parser implementation details (`I-*` heading grammar) beyond mirroring the existing `G-*` reader.
- **Source**: user / issue body

## Hard constraints to preserve
- **Question**: What must not break?
- **Resolution**: Reuse the existing `read_guidelines` present/absent/invalid contract (symlink rejection, repo-root containment, regular-file checks, fail-closed). Every knowledge file is independently optional: present -> include; absent -> omit silently; invalid/symlink/non-regular -> omit and warn. The prompt assembler must existence-gate every include so a missing file never yields a dangling "read this path" instruction. No inter-file dependencies. Editing `skills/shared/reviewer-templates.md` requires regenerating the four generated reviewer archetypes and passing CI `generate check`. The new invariants reader mirrors the `G-*` reader (`I-*` ids); do not over-build the parser. Do not regress `/implement` Step 8 compose-time guideline assessment or `/design` Gate C assessment.
- **Source**: codebase / issue body
