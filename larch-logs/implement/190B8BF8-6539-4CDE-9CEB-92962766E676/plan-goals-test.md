## Goal
Implement the Codex → Cursor → Claude default implementer waterfall for /implement Step 2, with a diff_lines < 30 Claude inline carve-out from /design output, WHOLESALE_REJECTED=true for /review, and coder_fallback logging.

## Implementation Plan

### 1. skills/implement/SKILL.md — Coder simplicity override + waterfall

Replace the current orchestrator-estimate-based simplicity override (≤ ~100 lines) with diff_lines-based routing:
- Read diff_lines from `$IMPLEMENT_TMPDIR/design-export/diff-lines.txt` (written by /design)
- If diff_lines < 30 → coder=claude (carve-out)
- If diff_lines absent/≥30 AND coder_explicit=false:
  - If codex_available=true → coder=codex (mandatory; stays as default)
  - If codex_available=false AND cursor_available=true → coder=cursor (waterfall fallback)
  - If both unavailable → coder=claude + mandatory user-facing warning + execution-issues.md log

Update Step 2.4 print cases to cover the new Cursor-as-waterfall-fallback case.

### 2. skills/design/SKILL.md — diff_lines in plan output

Add to plan composition (Step 2b):
- Estimate the total diff size of the planned change in lines
- Append `diff_lines: <N>` at the end of plan.txt
- Write `$DESIGN_TMPDIR/diff-lines.txt` with just the integer for export

### 3. skills/review/SKILL.md — WHOLESALE_REJECTED=true protocol

Add to voting-protocol output section:
- New output flag: WHOLESALE_REJECTED=true
- Criteria: any specialist returns WRONG_DIRECTION tag OR ≥50% of specialists return BLOCKING in a single round
- Redo-escalation: when WHOLESALE_REJECTED=true, escalate to Claude main agent for redo regardless of vendor availability, passing prior implementer output as context

### 4. scripts/test-implement-step2-routing.sh (new)

Regression harness with test cases:
- PASS: SKILL.md contains diff_lines < 30 carve-out prose
- PASS: SKILL.md contains waterfall routing prose (Codex → Cursor → Claude)
- PASS: Absent diff_lines routes to waterfall (not carve-out)
- PASS: coder_explicit bypasses waterfall
- PASS: WHOLESALE_REJECTED=true mentioned in review SKILL.md

### 5. scripts/test-implement-step2-routing.md (new)

Sibling contract document per .claude/rules/script-md-siblings.md.

## Edge Cases
- coder_explicit=true: bypass both carve-out and waterfall entirely
- Quick mode (no /design): diff_lines absent → use waterfall
- design-export/diff-lines.txt missing: treat as absent → use waterfall
- Cursor fallback: emit user-visible warning, log to execution-issues.md

## Test Plan
1. Run scripts/test-implement-step2-routing.sh
2. Run /relevant-checks

diff_lines: 120
