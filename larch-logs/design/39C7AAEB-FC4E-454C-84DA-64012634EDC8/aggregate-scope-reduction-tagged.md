### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:35-64
- **Concern**: [SCOPE-REDUCTION] Two-phase staged/durable HEAD pinning plus PR-body and final-summary surfacing exceeds issue acceptance. Scenario: Issue acceptance requires absent-file no-op, design gate notes, and implement warnings only; Phase B pin, diff_fingerprint, invalidate/reassess loops, ship.py hooks, and final_report append add substantial moving parts beyond chat-level warnings
- **Proposed resolution**: Defer Phase B durable surfacing to a follow-up: Phase A chat/execution-issues warning only for v1; drop pin_note_from_staged, note_consumable, and PR/final-summary append until durable surfacing is explicitly accepted

### FINDING_9:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:225-235; skills/implement/SKILL.md:537-540,720-721; scripts/test-implement-fence-shape.sh:149-166
- **Concern**: [SCOPE-REDUCTION] New architectural-guidelines launcher scripts duplicate the existing direct cli.py launcher pattern. Scenario: The plan adds three runtime .sh files even though existing /implement fences already launch python/cli.py through larch-run and the fence harness accepts .py targets. The issue needs the new CLI verbs, not extra wrapper files.
- **Proposed resolution**: Remove the three step-architectural-guidelines-*.sh files. Use direct one-line fences such as bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py architectural-guidelines read. Keep only the fence-count/test updates needed for those direct fences.
