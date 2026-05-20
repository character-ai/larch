# Review Round 1

- Mode: `diff`
- Accepted findings: 4
- Rejected findings: 1
- Exonerated findings: 0
- Neutral findings: 0

## Accepted Findings

### FINDING_5: risk-integration: .claude/rules/external-tool-launcher-parity.md:1-12
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Implementation plan overstates this rule as the regression guard for new serial-lock sites; rule paths omit the four touched scripts and the rule text does not cover serial locks. Future regression could drop lock calls without this rule firing on those paths. Align plan text with actual checks, extend rule paths if desired, or rely on explicit tests/relevant-checks.
- **Suggested revision**: Address the concern above.


### FINDING_6: risk-integration: .claude/rules/external-tool-launcher-parity.md:2-3
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Rule paths omit the four edited spawn scripts while the plan calls this rule the regression guard. Future contributor removes serial-lock calls in e.g. scripts/run-negotiation-round.sh without the path-triggered parity rule or CI failing. Add those scripts (or a dedicated lint) to the parity rule paths: or add a harness/grep check that enforces acquire+release_after before codex/cursor spawns.
- **Suggested revision**: Address the concern above.


### FINDING_8: risk-integration: scripts/run-negotiation-round.md
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] New KeyChain serial lock prose implies all Cursor-side KeyChain I/O is serialized at spawn. Darwin `cursor_auth_preflight` still runs `security find-generic-password` before `external_serial_lock_acquire`, so overlapping negotiation or other KeyChain traffic is still possible during preflight even though `cursor agent` startup is locked. Clarify that the lock wraps the `cursor agent` invocation (and note preflight remains outside the lock), matching actual ordering in scripts/run-negotiation-round.sh:110-121.
- **Suggested revision**: Address the concern above.


### FINDING_9: risk-integration: scripts/run-negotiation-round.sh:82-118
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No automated test targets the new serial-lock lines; repo has no test-run-negotiation-round harness. Linux CI always passes the acquire/release lines as no-ops; a macOS-only regression (missing lock, wrong order) ships unnoticed. Mirror scripts/test-launch-review.sh serial-lock assertions with LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME=Darwin or add a focused negotiation-round harness.
- **Suggested revision**: Address the concern above.


