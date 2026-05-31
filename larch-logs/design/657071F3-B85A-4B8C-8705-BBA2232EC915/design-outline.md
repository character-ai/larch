## Proposed Design Outline

### Goals
- When a codex/cursor agent fails (non-zero or timeout) in any `/implement`-side lane, surface a redacted, bounded stderr tail to chat — end-to-end.
- Cover all 5 lanes: codex/cursor implement, codex/cursor CI-fix, and the lint-fix-loop.
- Gap 2: add a behavioral test asserting collector stderr tails reach FD 2 when a panel reviewer fails.

### Non-goals
- No change to already-wired review/research/sketch lanes (`collect-agent-results.sh`, `launch-claude-review.sh`).
- No new tail/redaction logic — reuse `lib-failed-agent-stderr-tail.sh` from #3202.
- No change to launcher output/sentinel/telemetry contracts or existing `execution-issues.md` logging.

### Approach sketch
- All 5 lanes already route through `run-external-agent.sh`; lean on its #3202 stderr-tail hook rather than adding direct-CLI hooks.
- Per lane, ensure the failed agent's tail is captured at the choke point and the consumer (`step2-implement.sh`, `ship-pr.sh`, `lint-fix-loop.sh`) emits it to chat on failure.
- Redact before display; keep `execution-issues.md` logging additive.
- Gap 2: new failing-panel case in `test-plan-review-loop.sh` guarding the `plan-review-loop.sh` FD 2/4 tee.

### Surfaces in scope
- Launchers: `scripts/launch-codex-implement.sh`, `scripts/launch-cursor-implement.sh`, `scripts/launch-codex-ci.sh`, `scripts/launch-cursor-ci.sh`, `scripts/lint-fix-loop.sh`.
- Consumers: `skills/implement/scripts/step2-implement.sh`, `scripts/ship-pr.sh`.
- Reuse `scripts/lib-failed-agent-stderr-tail.sh` (minimal extension only if forced).
- Tests: `skills/design/scripts/test-plan-review-loop.sh` (+ `plan-review-loop.sh` only if the test exposes a tee bug).

### Open questions
- Exact choke point per lane (run-external-agent hook vs. consumer-side emit) — resolved in the plan, since SIMPLE skips sketches.
- Whether any lane needs a small `lib-failed-agent-stderr-tail.sh` extension vs. pure reuse.
