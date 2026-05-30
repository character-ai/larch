Merging duplicate wait-log findings and verifying against the codebase so normalized concerns stay accurate.
### FINDING_1: Plan/harness wait log basename mismatches production relay path
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, unknown-slot
- **Severity**: important
- **Concern**: The wait-relay plan and harness reference `$REVIEW_TMPDIR/wait.log`, but production `collect-findings.sh` sets `wait_log="$REVIEW_TMPDIR/wait-for-claude-reviewers.log"` (line 230). If stubs or fixtures seed `wait.log` instead of that basename, the wait-relay and BEL/ESC cases can false-green because relay logic never reads the fixture bytes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation, Cursor-Pragmatic: Use `wait-for-claude-reviewers.log` everywhere in the plan and harness docs; seed the stub's stderr into that path
  - From unknown-slot: Stub/fixture bytes written to `wait.log` never get relayed; BEL/ESC grep passes vacuously or case never hits the wait relay Use `$REVIEW_TMPDIR/wait-for-claude-reviewers.log` everywhere (match `wait_log=` at collect-findings.sh:230)

### FINDING_2: `collect-agent-results` harness may miss SCRIPT_DIR wait stub
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `test-collect-agent-results.sh` coverage may stub `wait-for-reviewers.sh` on PATH, but `collect-agent-results.sh` invokes `"$SCRIPT_DIR/wait-for-reviewers.sh"` (lines 308–311). PATH-only or in-repo shadow stubs never exercise the `WAIT_STDERR` relay; BEL/ESC stripping can ship untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Mirror the collect-findings harness contract: invoke from a minimal tree where `scripts/collect-agent-results.sh` and a stub `scripts/wait-for-reviewers.sh` share the same `SCRIPT_DIR` (copy/symlink real collector + real `lib-quiet.sh`/`redact-secrets.sh` siblings); document that PATH-only stubs are insufficient

---

**Merge notes (for voters, not machine output):** FINDING_1 and FINDING_3 from the raw input describe the same `wait.log` vs `wait-for-claude-reviewers.log` risk at `collect-findings.sh:230`; they were merged into `FINDING_1` with all three reviewer slots attributed. FINDING_2 is a separate code path (`scripts/collect-agent-results.sh` + `SCRIPT_DIR` invocation) and remains `FINDING_2`. Production confirms the production basename at ```230:230:skills/review/scripts/collect-findings.sh``` and the hardcoded wait script path at ```308:308:scripts/collect-agent-results.sh```.
