## Goal
Remove the diff_lines <= 3 carve-out from /implement coder selection; update all cross-file references

## Implementation Plan

Objective: Remove the `diff_lines <= 3` carve-out from /implement Step 1's coder selection, update all cross-file references, and ensure the regression harness matches the new contract.

Files to modify:

1. skills/implement/SKILL.md — Remove the carve-out block and update all references:
   - Lines 862, 929: `### Coder simplicity override` → `### Implementer waterfall`
   - Line 976: Remove the `⚡ diff_lines <= 3` breadcrumb mention
   - Line 1009: Update the legal next-actions matrix entry
   - Line 1068: Rename section heading
   - Lines 1072-1078: Replace carve-out block with simplified routing text
   - Line 1098: Update legacy --codex-available note (remove carve-out mention)
   - Line 1227: Remove the `diff_lines <= 3` auto-routed bullet

2. scripts/test-implement-step2-routing.sh — Remove the 3 assertions that pin the now-removed carve-out; update the explicit-coder-bypass assertion text

3. scripts/test-implement-step2-routing.md — Remove description of `diff_lines <= 3` carve-out

4. SECURITY.md — Update line 46 routing description

5. skills/design/SKILL.md — Update 3 references (lines 367, 553, 847) to say diff_lines is informational, no longer a routing trigger

Approach: Mechanical text edits across 5 files. The waterfall (Cursor → Codex → claude when both unavailable) is preserved. The diff_lines: N line in plan.txt and diff-lines.txt export remain (still useful as informational sizing context).

Testing: Run bash scripts/test-implement-step2-routing.sh + /relevant-checks after changes.

diff_lines: 80

## Test plan
(no test plan section in plan-file)
