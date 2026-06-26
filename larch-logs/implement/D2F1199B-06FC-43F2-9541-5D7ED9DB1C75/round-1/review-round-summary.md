# Review Round 1

- Mode: `diff`
- 3 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_6: Per-tier lint-fix timeout cut to 300s may abort valid fixes
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-testing
- **Severity**: important
- **Concern**: Per-tier external fixer timeout was reduced to 300s across claude, codex, and cursor launchers (from 1800s). A valid lint-fix that needs more than five minutes on a large or cold repo now times out and returns `main-agent-required` instead of completing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Restore the longer per-tier ceiling, or gate the 300s limit behind a narrower documented fast-path budget.
  - From cursor-specialist-testing: Split from relocation PR or restore higher per-tier limit; add slow-success regression test if keeping 300s


### FINDING_7: 600s lint-fix total budget not enforced on success or before next tier
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: important
- **Concern**: The 600s wall-clock budget guard runs only after failed tiers, not before starting the next tier and not on the success branch. A successful tier can return `applied` after the cap is already exceeded; a slow failure near ~590s can still launch the next tier for up to 300s more (~890s wall time), delaying main-agent handoff despite the documented 600s cap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Check elapsed time before each dispatch and immediately after success; treat over-budget successes as lint-fix-budget-exceeded.
  - From cursor-specialist-edge-cases: Check remaining budget before dispatching each tier; if elapsed >= 600s, set budget_exceeded and break without starting another external agent.
  - From cursor-specialist-testing: Check budget before each tier dispatch; add monotonic-time stub test for tier skip
  - From codex-specialist-edge-cases: re-check the budget on the success branch before breaking, and if the deadline has passed return the capped outcome instead of success.
  - From codex-specialist-testing: Check elapsed time immediately after every tool invocation, before any success break, and divert over-budget successes through the budget-exceeded fallback.


### FINDING_8: Unmatched trailing quote in refuse-path redaction command
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: latent
- **Concern**: The redaction command in `preflight-plan-audit.md` line 73 has an unmatched trailing `"` after `secrets`, so copying the refuse-path command verbatim causes a shell parse error before `audit-questions.redacted.md` is written. This only hits the rare `AUDIT=refuse` path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: delete the stray quote and keep the command as `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" redact secrets`.


