### FINDING_1: Stale line-94 grep conflicts with anti-halt SKILL rewrite
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan replaces the anti-halt embedded sentence containing `marker-first profile for completed Step 5c task output when _publish_rc is 0, 1, or 3` with a compact shared-profile pointer plus explicit binding pins, but only schedules new pins near line 94 and does not retire the existing line-94 grep that still requires that exact substring. After the SKILL edit, `make test-render-cost-line-callsites` fails at line 94 even when runtime behavior is correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In scripts/test-render-cost-line-callsites.sh, explicitly retire/replace the line-94 substring grep with anti-halt pins for shared-profile pointer, LARCH_FINAL_SUMMARY_BEGIN/END, design-step5c.sh, _publish_rc 0/1/3 carve-out, and Read/sidecar per the /design row.
  - From Cursor-Requirements: Under `### UPDATED: scripts/test-render-cost-line-callsites.sh`, explicitly retire the line-94 exact-string grep and replace it with pins on the new anti-halt binding (shared-profile pointer, `LARCH_FINAL_SUMMARY_BEGIN`/`END`, `design-step5c.sh` + `<task-notification>` source, `_publish_rc` 0/1/3 carve-out).

### FINDING_2: Harness pins omit per-site notification script names
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Plan SKILL binding requires site-specific sources (`design-step5c.sh` at anti-halt/Step 5c paths; `design-step-final-summary.sh` at cancellation per `skills/design/SKILL.md:321`), but the harness section only mandates generic `<task-notification>` and anti-halt `design-step5c.sh` pins. Cancellation or Step 5c sites could swap script names, pass lint, and still emit from the wrong completed task stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend scripts/test-render-cost-line-callsites.sh pins to require design-step-final-summary.sh at the Final summary block callsite and design-step5c.sh at Step 5c abort/item-5 callsites, each adjacent to marker-first pointers with LARCH_FINAL_SUMMARY_BEGIN/END.

### FINDING_3: Implement-side verbatim-emit harness pins not scheduled for retirement
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan deduplicates implement Step 17/18b/NEVER #17 inline algorithm to a shared-profile pointer and lists replacement contract-token pins (shared pointer, marker pair, foreground stdout source, no Read fallback). It does not enumerate retiring implement-SKILL greps for `emit the extracted body verbatim as plain chat markdown` and related full-body emit sentences (`test-render-cost-line-callsites.sh` lines 51-52, 71-73; `test-implement-structure.sh` line 276). After SKILL dedup, those exact strings move to the shared anchor only; stale greps fail `make lint` unless the author keeps duplicate prose in implement SKILL, defeating the dedup goal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add explicit harness retirement/replacement rows for implement-side verbatim-emit pins: drop or repoint lines 51-52 and 71-73 to shared-anchor or contract-token checks, and update test-implement-structure.sh line 276 similarly, consistent with the shared-doc emit pin already at test-render-cost-line-callsites.sh line 79.

---

**Merge notes**

| Raw inputs | Disposition |
|---|---|
| FINDING_1 + FINDING_3 | Merged → **FINDING_1** (same line-94 grep vs anti-halt rewrite risk; both Cursor-Arch and Cursor-Requirements) |
| FINDING_2 | Kept separate → **FINDING_2** (distinct fix: per-site script-name enforcement, not grep retirement) |
| FINDING_4 | Kept separate → **FINDING_3** (distinct surface: implement-side pins, not design anti-halt) |

No `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` token (non-empty merge).
