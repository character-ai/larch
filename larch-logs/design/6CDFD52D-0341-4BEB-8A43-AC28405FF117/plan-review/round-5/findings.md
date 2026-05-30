### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:177
- **Concern**: Wait-relay harness cites `$REVIEW_TMPDIR/wait.log` but production uses `wait-for-claude-reviewers.log`. Scenario: Stub or seed writes `wait.log` while `collect-findings.sh` relays `wait_log="$REVIEW_TMPDIR/wait-for-claude-reviewers.log"` (~230); BEL/ESC fixture never hits the changed loops and the wait case false-greens
- **Proposed resolution**: Use `wait-for-claude-reviewers.log` everywhere in the plan and harness docs; seed the stub’s stderr into that path

### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:206-212
- **Concern**: `test-collect-agent-results.sh` coverage says stub `wait-for-reviewers.sh` but not that `collect-agent-results.sh` hardcodes `"$SCRIPT_DIR/wait-for-reviewers.sh"`. Scenario: PATH-only or in-repo shadow stubs never hit the WAIT_STDERR relay at `scripts/collect-agent-results.sh:308-311`; BEL/ESC stripping may ship untested
- **Proposed resolution**: Mirror the collect-findings harness contract: invoke from a minimal tree where `scripts/collect-agent-results.sh` and a stub `scripts/wait-for-reviewers.sh` share the same `SCRIPT_DIR` (copy/symlink real collector + real `lib-quiet.sh`/`redact-secrets.sh` siblings); document that PATH-only stubs are insufficient

### FINDING_3:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:177
- **Concern**: skills/review/scripts/collect-findings.sh:230. Scenario: Wrong wait log basename in plan (`$REVIEW_TMPDIR/wait.log`) vs production `wait-for-claude-reviewers.log`
- **Proposed resolution**: Stub/fixture bytes written to `wait.log` never get relayed; BEL/ESC grep passes vacuously or case never hits the wait relay Use `$REVIEW_TMPDIR/wait-for-claude-reviewers.log` everywhere (match `wait_log=` at collect-findings.sh:230)
