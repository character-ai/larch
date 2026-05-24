## Goal
Add Check 18 literal-anchor assertions to test-design-structure.sh for ## Plan Candidate for Review and ## Final Design Plan headers

## Implementation Plan
## Plan

Add a new `Check 18` block to `scripts/test-design-structure.sh`, immediately before the final `echo "PASS: ..."` line and after the existing `FINDING_21` block, that asserts:

1. The Step 3 block of `skills/design/SKILL.md` — extracted via `awk '/^<!-- step:3 /,/^<!-- step:3.5 /' "$SKILL_MD"` (same per-section extraction pattern as the existing Step 2b block) — contains the literal token `## Plan Candidate for Review`.
2. The Gate C block of `skills/design/references/approval-gates.md` — extracted via `awk '/^## Gate C/,/^## State invariants/' "$APPROVAL_MD"` (mirrors the existing per-section awk pattern, terminated by the next top-level `##` heading) — contains the literal token `## Final Design Plan`.

Both assertions use `grep -Fq` (fixed-string) on the extracted block and `fail "(18) …"` on miss, matching the prevailing style of every prior check. `APPROVAL_MD` is already bound in the FINDING_21 block; `SKILL_MD` is bound much earlier in the script.

Also update `scripts/test-design-structure.md` (sibling contract doc per `.claude/rules/script-md-siblings.md`) to mention the new `#2702 literal-anchor` coverage so the doc stays in sync.

The headers are currently emitted at runtime by `skills/design/scripts/emit-design-plan-preview.sh` (lines 103 / 116) and referenced in prose at `skills/design/SKILL.md:615` (Step 3 entry) and `skills/design/references/approval-gates.md:118` (Gate C Presentation). The new Check 18 protects the prose anchors so they can't be silently removed.

### Edge cases

- `^<!-- step:3 ` (trailing space) deliberately excludes `<!-- step:3.5` because Step 3.5's marker is `<!-- step:3.5 — Post-Review Chooser (Gate B) -->`.
- `^## State invariants` bounds the Gate C block; if that section is renamed, the range becomes open-ended but the assertion still passes when the anchor is present.
- If either header is moved out of its respective block or removed entirely, the assertion fails with `(18)` prefix in the fail message — intended structural protection.

### Failure modes

1. Awk range mis-extraction if marker tokens drift — same risk profile as the existing FINDING_21 Step 2b extraction; mitigation: reuse the FINDING_21 pattern verbatim.
2. Sibling `.md` drift — caught by `.claude/rules/script-md-siblings.md` enforcement; mitigation: update both files in the same commit.

## Acceptance

- `scripts/test-design-structure.sh` contains a new `Check 18` block with two `grep -Fq` assertions matching the descriptions above, each producing a `fail "(18) …"` message on miss.
- The new check is placed after the `FINDING_21` block (which itself ends near line 578) and before the final `echo "PASS: ..."` line.
- `bash scripts/test-design-structure.sh` exits 0 and prints `PASS: test-design-structure.sh — structural invariants hold (including security OOS exclusions)` on the current tree.
- Manual spot-check: temporarily removing `## Plan Candidate for Review` from `skills/design/SKILL.md` Step 3 (or `## Final Design Plan` from `skills/design/references/approval-gates.md` Gate C) makes `Check 18` fire with a `(18)` fail message, and restoring the header makes the test pass again.
- `scripts/test-design-structure.md` mentions the new `#2702` literal-anchor coverage.
- `make lint` still passes.

diff_lines: 20

## Test plan
(no test plan section in plan-file)
