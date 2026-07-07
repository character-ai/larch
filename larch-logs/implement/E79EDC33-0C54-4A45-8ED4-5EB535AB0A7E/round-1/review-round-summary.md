# Review Round 1

- Mode: `diff`
- 6 accepted, 2 rejected (1 neutral)

## Accepted Findings

### FINDING_5: planned override durability breaks across trusted rewrites
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: The authority hash used to recognize a planned override is not durable across trusted rewrites, so a later edit can preserve the trailer but change the hash and cause the override to be ignored again.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Make the authority marker durable across trusted rewrites, or refresh it in every trusted rewrite that preserves the override trailer.


### FINDING_6: SIZE_TRIGGER_FIRED must fail closed
- **Reviewer(s)**: codex-specialist-correctness, dyn-dyn-plan-size
- **Severity**: major
- **Concern**: The publish-size gate can pass when `PLAN_SIZE_STATUS=ok` is present but `SIZE_TRIGGER_FIRED` is missing, which weakens the intended fail-closed behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From dyn-dyn-plan-size: Require SIZE_TRIGGER_FIRED to be exactly "true" or "false"; treat any other value (including absent) as PUBLISH_REFUSE_REASON=size-check-failed, mirroring the existing PLAN_SIZE_STATUS gate.


### FINDING_10: Step 5c should preserve refusal reason on rc=4
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: The Step 5c handoff path does not have a test proving that `PUBLISH_REFUSE_REASON` survives `safe_publish_env` when `publish_core` exits with rc=4, so refusal routing could be misdirected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Stub publish_core rc=4 with PUBLISH_REFUSE_REASON; assert step5c_core emits it in KV output.


