### FINDING_1: mkitmp ndjson seed conflates precondition vs disposition-gap paths
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: `mkitmp` always seeds a RUN_ID-keyed `oos-issues.ndjson`, but the precondition case requires no resolvable ndjson. If the harness implements one shared `mkitmp`, the precondition test (exit 2) still finds the seeded ndjson and never reaches the pre-gate path, conflating disposition-gap and precondition scenarios.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add mkitmp option (or a second helper) to omit or hide ndjson for the precondition case; keep default mkitmp with ndjson for exit-1 disposition-gap (non-sec OOS requires resolvable ndjson per plan.txt:48)

### FINDING_2: log_checkpoint_failure omits required append-tool-failure.sh flags
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Edge, Cursor-Innovation
- **Severity**: important
- **Concern**: `log_checkpoint_failure` / `append-tool-failure.sh` invocations omit required `--log` and `--site`. Without them, `append-tool-failure.sh` fails (scripts/append-tool-failure.sh:68-73); `|| true` swallows the failure, so nothing is written to `execution-issues.md`. The FINDING_4 disposition-gap logging assertion then misses the file, Step 8+ audit rows are lost, and operators see a silent logging gap across plan.txt (35-37), checkpoint.md, and the `oos-disposition-checkpoint.sh` sketch (35-38).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Spell the full append call in the plan (match skills/implement/scripts/step-7a.sh:44-50): --log "$IMPLEMENT_TMPDIR/execution-issues.md", --site from the caller, plus --tool, --exit-code, --category, --output-file, --redact
  - From Cursor-Edge: Add --log "$IMPLEMENT_TMPDIR/execution-issues.md" and --site "$site" to every log_checkpoint_failure call; spell both in checkpoint.md
  - From Cursor-Innovation: Add `--log "$IMPLEMENT_TMPDIR/execution-issues.md"` to every `append-tool-failure.sh` call (match inline skills/implement/SKILL.md:1273-1274 and step-7a.sh:45); document in oos-disposition-checkpoint.md
