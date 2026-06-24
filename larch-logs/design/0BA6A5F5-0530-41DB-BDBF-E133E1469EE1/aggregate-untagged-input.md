### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-render-cost-line-callsites.sh:94
- **Concern**: Anti-halt SKILL rewrite conflicts with stale line-94 grep. Scenario: The plan requires replacing the anti-halt embedded sentence `marker-first profile for completed Step 5c task output when _publish_rc is 0, 1, or 3` (plan.txt:105) but only says to add binding pins near line 94 (plan.txt:139), not retire the existing grep that still requires that exact substring. After SKILL edits, make test-render-cost-line-callsites fails even when behavior is correct.
- **Proposed resolution**: In scripts/test-render-cost-line-callsites.sh, explicitly retire/replace the line-94 substring grep with anti-halt pins for shared-profile pointer, LARCH_FINAL_SUMMARY_BEGIN/END, design-step5c.sh, _publish_rc 0/1/3 carve-out, and Read/sidecar per the /design row.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:138-139
- **Concern**: Harness design pins do not enforce per-site notification script names. Scenario: Plan SKILL binding requires site-specific sources (design-step5c.sh at anti-halt/Step 5c paths; design-step-final-summary.sh at cancellation per skills/design/SKILL.md:321), but the harness section only mandates generic `<task-notification>` (plan.txt:138) and anti-halt design-step5c.sh (plan.txt:139). Cancellation or Step 5c sites could swap script names, pass lint, and still emit from the wrong completed task stdout.
- **Proposed resolution**: Extend scripts/test-render-cost-line-callsites.sh pins to require design-step-final-summary.sh at the Final summary block callsite and design-step5c.sh at Step 5c abort/item-5 callsites, each adjacent to marker-first pointers with LARCH_FINAL_SUMMARY_BEGIN/END.

### FINDING_3:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-render-cost-line-callsites.sh:94
- **Concern**: Anti-halt binding edit retires the only grep target for the line-94 `_publish_rc` carve-out pin. Scenario: Plan requires replacing the anti-halt continuation sentence that embeds `marker-first profile for completed Step 5c task output when _publish_rc is 0, 1, or 3` with a compact shared-profile pointer plus explicit marker/source binding (skills/design/SKILL.md binding sites). That substring currently appears only in anti-halt (~line 29), not in Step 5d prose. Harness line 94 still greps for it. Plan adds new anti-halt binding pins near line 94 but does not require removing or retargeting the existing line-94 grep. After the SKILL edit, `make test-render-cost-line-callsites` fails even when behavior is preserved.
- **Proposed resolution**: Under `### UPDATED: scripts/test-render-cost-line-callsites.sh`, explicitly retire the line-94 exact-string grep and replace it with pins on the new anti-halt binding (shared-profile pointer, `LARCH_FINAL_SUMMARY_BEGIN`/`END`, `design-step5c.sh` + `<task-notification>` source, `_publish_rc` 0/1/3 carve-out).

### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-render-cost-line-callsites.sh:51-52,71-73;scripts/test-implement-structure.sh:276
- **Concern**: Implement-side verbatim-emit exact-string harness pins are not scheduled for retirement. Scenario: Plan deduplicates Step 17/18b/NEVER #17 inline algorithm to a shared-profile pointer and lists replacement contract-token pins (shared pointer, marker pair, foreground stdout source, no Read fallback). It does not enumerate retiring implement-SKILL greps for `emit the extracted body verbatim as plain chat markdown` and related full-body emit sentences (test-render-cost-line-callsites.sh lines 51-52, 71-73; test-implement-structure.sh line 276). After SKILL dedup, those exact strings move to the shared anchor only; stale greps fail `make lint` unless the author keeps duplicate prose in implement SKILL, defeating the dedup goal.
- **Proposed resolution**: Add explicit harness retirement/replacement rows for implement-side verbatim-emit pins: drop or repoint lines 51-52 and 71-73 to shared-anchor or contract-token checks, and update test-implement-structure.sh line 276 similarly, consistent with the shared-doc emit pin already at test-render-cost-line-callsites.sh line 79.
