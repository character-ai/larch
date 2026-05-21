## Goal
Add OOS silent-drop gate: policy hardening + mechanical gate script + audit scan

## Implementation Plan

Goal: Fix silent-drop of voted-in OOS findings at Step 9a.1 by adding policy hardening,
a mechanical gate, and a retroactive audit scan.

### Files to modify

1. **skills/implement/SKILL.md** — three edits:
   - In `## NEVER List` (after existing rule 16), add rule 17: "NEVER silently drop a voted-in OOS finding."
   - In `### OOS triage policy` block (after rule 4 / Actionable consequence paragraph), add Terminal disposition invariant paragraph.
   - Tighten the carve-out sentence in the Actionable consequence paragraph to lead with the consequence.
   - In `## NEVER List`, add rule 18: "NEVER set `OOS_PENDING=false` without a passing `oos-disposition-gate.sh` invocation (fork-mode and repo-unavailable carve-outs)."
   - In Step 8+ OOS checkpoint prose (around L1755), wire the gate: after `/issue` block, before `state_set OOS_PENDING false` prose, add the gate invocation.

2. **skills/implement/scripts/oos-disposition-gate.sh** — new file.
   Contract: --accepted-files, --filed-urls-file, --commit-range, --fork-mode, --repo-unavailable.
   Logic: skip if fork-mode/repo-unavailable; count OOS_N entries minus security-routed; count filed URLs; count Inline-triage commits; pass if filed>0 OR inline>=non_security; fail exit 1 if non_security>0 AND filed==0 AND inline==0; exit 2 on bad args.

3. **skills/implement/scripts/oos-disposition-gate.md** — sibling contract doc.

4. **skills/implement/scripts/test-oos-disposition-gate.sh** — harness with >=6 scenarios.

5. **.claude/skills/audit-runs/scans.tsv** — add row for `oos-silent-drop`.

6. **.claude/skills/audit-runs/scripts/audit-scan-run.sh** — add `scan_oos_silent_drop()` function and wire it in the `case` dispatcher.

7. **scripts/test-implement-structure.sh** — add two literal-pin assertions:
   - Pin for "Terminal disposition invariant" text in SKILL.md.
   - Pin for "NEVER silently drop a voted-in OOS finding" in SKILL.md.

### Testing strategy
- `make lint-bash32` to verify Bash 3.2 compatibility.
- `make agent-lint` for skill structure lint.
- `bash scripts/test-implement-structure.sh` to verify new pins pass.
- `bash skills/implement/scripts/test-oos-disposition-gate.sh` to verify gate harness.

### Edge cases
- Security-routed entries must be excluded from accepted count (uses `focus-area\s*=\s*security` match).
- Fork-mode and repo-unavailable skip the gate entirely.
- Combined OOS (N source entries → 1 filed URL) passes because filed_count > 0.
- Inline-fold check counts `Inline-triage rule N:` commit body lines (per-entry breadcrumbs).

## Test plan
(no test plan section in plan-file)
