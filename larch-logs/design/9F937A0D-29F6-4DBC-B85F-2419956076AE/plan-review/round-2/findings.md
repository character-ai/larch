### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:82-91
- **Concern**: mkitmp always seeds RUN_ID-keyed oos-issues.ndjson but the precondition case needs no resolvable ndjson. Scenario: Harness implements one mkitmp; precondition test (exit 2) still finds the seeded ndjson and never hits the pre-gate path; disposition-gap vs precondition cases conflate
- **Proposed resolution**: Add mkitmp option (or a second helper) to omit or hide ndjson for the precondition case; keep default mkitmp with ndjson for exit-1 disposition-gap (non-sec OOS requires resolvable ndjson per plan.txt:48)

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch, Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:35-37
- **Concern**: log_checkpoint_failure append line omits required --log and --site. Scenario: Without --log, append-tool-failure.sh fails (scripts/append-tool-failure.sh:68-72); || true swallows it and FINDING_4 disposition-gap logging assertion misses execution-issues.md
- **Proposed resolution**: Spell the full append call in the plan (match skills/implement/scripts/step-7a.sh:44-50): --log "$IMPLEMENT_TMPDIR/execution-issues.md", --site from the caller, plus --tool, --exit-code, --category, --output-file, --redact

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:35-37
- **Concern**: log_checkpoint_failure omits required append-tool-failure.sh flags. Scenario: Example invocation lists only --tool --exit-code --category --output-file --redact; scripts/append-tool-failure.sh requires --log and --site (scripts/append-tool-failure.sh:68-73). Literal port would not write execution-issues.md; FINDING_4 harness grep would fail and operators lose Tool Failures audit rows
- **Proposed resolution**: Add --log "$IMPLEMENT_TMPDIR/execution-issues.md" and --site "$site" to every log_checkpoint_failure call; spell both in checkpoint.md

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/oos-disposition-checkpoint.sh:35-38
- **Concern**: `log_checkpoint_failure` sketch omits required `--log`. Scenario: `append-tool-failure.sh` requires `--log` (scripts/append-tool-failure.sh:68); without it append exits 1, `|| true` swallows it, no `execution-issues.md` entry — FINDING_4 harness and Step 8+ audit trail fail silently
- **Proposed resolution**: Add `--log "$IMPLEMENT_TMPDIR/execution-issues.md"` to every `append-tool-failure.sh` call (match inline skills/implement/SKILL.md:1273-1274 and step-7a.sh:45); document in oos-disposition-checkpoint.md
