# Review Round 2

- Mode: `diff`
- 2 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: cap_hit carried forward but dropped at collect_findings
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, codex-specialist-edge-cases, cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: On degraded retry, `_degraded_retry_carry_forward` treats `STATUS=cap_hit` as substantive and carries those slots forward, but `collect_findings` gates parsing through `_collector_ok`, which accepts only `STATUS=OK`. Carried cap_hit files therefore survive relaunch reduction yet are skipped during collection, so partial cap-hit findings vanish from the retry aggregate and the run can report zero findings when a full relaunch might have produced ingestible output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.


### FINDING_5: Successful Claude fallback outputs absent from collector-results.env
- **Reviewer(s)**: codex-generalist
- **Severity**: important
- **Concern**: `_degraded_retry_carry_forward` builds the carry-forward set only from `collector-results.env`, but successful Claude fallback reviewer outputs are never recorded there with `STATUS=OK`; `collect_findings` parses `claude_files` directly and appends only `NOT_SUBSTANTIVE` Claude records. Scenario: a round-2 waterfall slot succeeds via phase-3 Claude, another slot is `NOT_SUBSTANTIVE`, and degraded retry relaunches the already-successful Claude slot because carry-forward cannot see it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generalist: Address the concern above.


