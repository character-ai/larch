## Decision 1: Tier selection
- **Question**: Which tier for issue #2676 refactor?
- **Resolution**: HARD (operator-selected; 4 sketches + 10-reviewer panel + per-finding approval)
- **Source**: user

## Decision 2: Voter 1 launch mechanism
- **Question**: Issue says "no launcher change" for Voter 1 (Agent-tool subagent), but a bash script cannot spawn an Agent-tool subagent. How to wire Voter 1 inside plan-review-loop.sh?
- **Resolution**: Use launch-claude-review.sh subprocess (mirroring dispatch-code-voters.sh / /implement review loop). Verified: dispatch-code-voters.sh:285-301 already does exactly this. The issue body's "no launcher change" wording is superseded by this user decision.
- **Source**: user (with codebase verification)

## Decision 3: Aggregator scope
- **Question**: Should plan-review-loop.sh introduce aggregate-findings.sh into /design (currently only used by /review), or keep orchestrator-side aggregation?
- **Resolution**: Yes — absorb #2644 R1/FINDING_27 into this refactor. The new script calls aggregate-findings.sh. Acceptance becomes "same session-root artifacts" (not bit-identical ballot dedup).
- **Source**: user

## Decision 4: Script scope
- **Question**: How much of Step 3 should plan-review-loop.sh own?
- **Resolution**: Panel dispatch + collect + ballot + Voter 2/3 + tally (script wraps from scout-plan-archetypes-wrapper.sh through tally; SKILL.md Step 3 collapses to emit-design-plan-preview.sh + plan-review-loop.sh).
- **Source**: user

## Decision 5: Voter 1 wiring location
- **Question**: Extend dispatch-plan-voters.sh to launch Voter 1, or keep it unchanged and have plan-review-loop.sh launch Voter 1 separately?
- **Resolution**: Extend scripts/dispatch-plan-voters.sh in-place to launch Voter 1 before Voter 2/3 (mirrors dispatch-code-voters.sh). /design and /implement voter-dispatch shapes converge.
- **Source**: user

## Decision 6: Trivial bypass location
- **Question**: Where should the review_budget=quick short-circuit live?
- **Resolution**: SKILL.md keeps the existing top-of-Step-3 branch (`if review_budget=quick → plan-review-quick.md`). plan-review-loop.sh assumes full-budget; trivial path never invokes it. Matches the issue's '/design --trivial is unchanged' acceptance.
- **Source**: user

## Decision 7: Round-num arg
- **Question**: Should plan-review-loop.sh accept --round-num <N> (default 1) now?
- **Resolution**: Yes. Optional --round-num flag, default 1; emit ROUNDS_COMPLETED=$round_num. Forward-compat surface for the multi-round companion. Single-pass behavior unchanged.
- **Source**: user

## Decision 8: Test harness scope
- **Question**: What should test-plan-review-loop.sh cover?
- **Resolution**: Hermetic unit harness with stubbed launchers (stub codex/cursor binaries + launch-claude-review.sh). Matches existing test-dispatch-plan-voters.sh / test-dispatch-code-voters.sh shape. Covers driver orchestration, aggregator-failure fallback, voter status parsing, tally KV emission, 0-judge fallback.
- **Source**: user
