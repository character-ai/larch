# Review Round 1

- Mode: `diff`
- 2 accepted, 4 rejected (1 neutral)

## Accepted Findings

### FINDING_1: CLI failure fallback skips identity-key filtering on rejected findings
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-design-flow-output.txt, dyn-report-framing-output.txt
- **Severity**: important
- **Concern**: When `plan-review emit-rejected --report-framing` exits non-zero, `design-step3b-tail.sh` prints the considered-not-adopted heading/annotation but `cat`s raw `rejected-findings.md` without the identity-key filtering `emit_rejected_findings` applies on the happy path. Operators can see findings already applied in earlier rounds under softer framing that implies deliberate non-adoption, regressing the #4849 filter on the resilience path the wrapper explicitly keeps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: On fallback, run filtering before cat (shared helper or filter-only CLI subcommand) then apply the same framing.
  - From dyn-design-flow-output.txt: On CLI failure, either retry once, or emit a warning and omit rejected output instead of dumping unfiltered content; if output is required, run a small shell/Python filter using the same applied-key ledger before framing.
  - From dyn-report-framing-output.txt: On fallback, still run filtering before display (e.g. a dedicated `emit-rejected --report-framing --allow-degraded` that never exits non-zero on read/filter paths), or frame only after best-effort filter in shell. Add a contract test that simulates CLI failure and asserts filtered+framed output.


### FINDING_3: Reviewer status table falls back to round 1 when round binding fails
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-design-flow-output.txt
- **Severity**: important
- **Concern**: When `latest-reviewer-status.tsv` is missing and round cannot be bound from notification stdout or the minimal env scan (`FINAL_ROUND_NUM` / `STEP3_REVIEW_ROUND_NUM` / `ROUNDS_COMPLETED`), the contract still defaults to round 1 via shell parameter expansion (`${ROUNDS_COMPLETED:-1}`) in multiple places. Orchestrators can print round-1 panel state during a later review round, misreporting failures/skips despite plan edge cases that say not to default silently to round 1.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: After binding attempts, if round is still unbound, omit the compact table or emit an explicit warning; remove or guard the :-1 default so it cannot silently misrepresent the panel.
  - From dyn-design-flow-output.txt: Require explicit round binding before using the per-round fallback; if binding fails, print a warning and skip the table rather than reading `round-1/reviewer-status.tsv`.


