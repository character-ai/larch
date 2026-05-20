## Goal
Add NEVER #16 and inline foreground warning for ship-pr.sh in /implement SKILL.md

## Implementation Plan

Three edits to `skills/implement/SKILL.md`:

**Edit 1 — Add NEVER #16** (after NEVER #15 at line 63, before "Single-runner assumption" at line 64):
Add a new numbered entry prohibiting `run_in_background: true` for `ship-pr.sh`, with WHY (async task-notification breaks turn-boundary contract, stalls in --auto mode), HOW TO APPLY (foreground call, 10-min timeout covers CI wait, --resume-phase recovery pattern on timeout), CI-backed: no.

**Edit 2 — Add inline warning before `Invoke:` block** (line 1725 in Step 8+):
Add a blockquote warning immediately before the "Invoke:" label that says `ship-pr.sh` MUST be foreground, must not use `run_in_background: true`, and documents the manual `--resume-phase` recovery pattern for timeout/turn-end cases.

**Edit 3 — (covered by NEVER #16 and inline warning)**: The `--resume-phase` recovery pattern is documented inline in both Edit 1 (NEVER #16 How to apply) and Edit 2 (inline warning), so no additional standalone section is needed.

Files to modify:
- `skills/implement/SKILL.md` — two insertions only

Verification: run `/relevant-checks` after edits (pre-commit + agent-lint). No logic changes, no test changes needed.

## Test plan
(no test plan section in plan-file)
