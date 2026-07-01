## Proposed Design Outline

### Goals
- Fix `_is_illustrative_placeholder` in `lint_bg_wait_coverage.py` so it stops exempting real launch fences that use `<...>` runtime-substituted placeholders (currently exempts brainstorm.md's Framing launch by accident).
- Arm real bg-wait-marker coverage for brainstorm.md's two external launches (Framing, Scope): add a marker directive line directly before each fence, and register matching `CommandMapping` entries.
- Document, rather than silently omit, why `/research`'s background fences stay out of `SCOPE_PATTERNS` (per Round-1 Decision 1).

### Non-goals
- Do not add `skills/research/**` to `SCOPE_PATTERNS` (per Round-1 Decision 1: no functional stall-recovery/marker-reading system exists for /research today).
- Do not redesign `_nearest_launch_fence`'s proximity/ordering algorithm (12-line forward-only window, one fence per directive) (per Round-1 Decision 2).
- Do not add new runtime `.bg-wait-active`-writing code; this lint's registry (`KNOWN_BACKGROUND_COMMANDS`) only requires a conscious static acknowledgment, not new marker-writing plumbing.

### Approach sketch
- `python/larch/lint/lint_bg_wait_coverage.py`: narrow/remove `_is_illustrative_placeholder`; add 1 new `CommandMapping` entry covering brainstorm's Framing + Scope launches (shared substrings); add an explanatory comment near `SCOPE_PATTERNS` documenting the /research exemption.
- `skills/design/references/brainstorm.md`: add a marker directive line directly before each of the two external-launch fences (Framing at ~line 77, Scope at ~line 83), matching the existing SKILL.md convention.
- `python/tests/lint/test_lint_bg_wait_coverage.py`: add regression cases — a real command using `<...>` placeholders must still be flagged when unregistered; brainstorm's two now-registered commands must pass; confirm `/research` fences remain untouched/unflagged (out of scope, by design).

### Surfaces in scope
- `python/larch/lint/lint_bg_wait_coverage.py`
- `python/tests/lint/test_lint_bg_wait_coverage.py`
- `skills/design/references/brainstorm.md`

### Open questions
- None.
