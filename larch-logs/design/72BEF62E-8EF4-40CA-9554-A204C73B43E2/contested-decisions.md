### DECISION_1: aggregator schema adaptation for /design ballots
- **Chosen**: Use `aggregate-findings.sh` as-is on /design ballots; add explicit duplicate-finding fixture test to verify aggregation only changes dedup shape (not severity/scope/result).
- **Alternative**: Add /design-specific input adapter to `aggregate-findings.sh` (or fork it) to handle the absence of severity lines on plan-review ballots.
- **Tension**: Codex-Pragmatic flags that aggregate-findings.sh "validation expects code-review-style structure such as severity lines" — a real correctness risk. Cursor-Arch suggests reuse is straightforward (just pass --review-tmpdir). The risk: aggregate-findings.sh may emit warnings or skip rows on /design ballots.
- **Impact**: High
- **Affected files**: skills/review/scripts/aggregate-findings.sh, skills/design/scripts/plan-review-loop.sh, skills/design/scripts/test-plan-review-loop.sh

### DECISION_2: 0-judge fallback semantics
- **Chosen**: Signal-only — plan-review-loop.sh emits `LOOP_STATUS=main-agent-vote-required` when all three voters fail; SKILL.md's existing main-agent-vote-required prose handles the rest.
- **Alternative**: plan-review-loop.sh attempts a synthetic Claude subprocess fallback (a second launch-claude-review.sh invocation labeled as "fallback judge") before signaling main-agent-vote-required.
- **Tension**: Codex-Innovation proposes the synthetic fallback as a clearer failure recovery; Codex-Pragmatic prefers preserving the existing main-agent-vote-required path. Signal-only is smaller blast radius and keeps the MAV invariant in one place; synthetic fallback adds reliability but a new code path.
- **Impact**: Medium
- **Affected files**: skills/design/scripts/plan-review-loop.sh, skills/design/SKILL.md (Step 3 trailing prose stays)

### DECISION_3: reuse `collect-findings.sh` vs use only `collect-agent-results.sh`
- **Chosen**: Use only `collect-agent-results.sh` (the existing /design pattern). Convert raw reviewer outputs to ballot.txt inline in plan-review-loop.sh (one helper function).
- **Alternative**: Reuse `skills/review/scripts/collect-findings.sh` with `--review-tmpdir $DESIGN_TMPDIR`; first resolve the flag-parity gap with collect-agent-results.sh.
- **Tension**: Cursor-Arch advocates reuse for /review parallelism; Codex sketches use the existing pattern (don't argue against, but don't endorse). Reuse increases code consolidation but expands blast radius (must resolve flag-parity gap; changes /review test harness coverage).
- **Impact**: Medium
- **Affected files**: skills/design/scripts/plan-review-loop.sh, skills/review/scripts/collect-findings.sh (only on alternative)

### DECISION_4: aggregator kill switch — /design-specific wrapper or rely on existing
- **Chosen**: Rely on existing `LARCH_AGGREGATOR_DISABLED=1` (per Codex-Innovation's verification that the env var already exists in aggregate-findings.sh). No new /design-specific variable.
- **Alternative**: Add a thin convenience wrapper `LARCH_DESIGN_USE_AGGREGATOR=false` in plan-review-loop.sh that sets LARCH_AGGREGATOR_DISABLED before invoking aggregate-findings.sh.
- **Tension**: Codex-Innovation suggests the convenience wrapper for clearer /design-specific rollback; Codex-Pragmatic doesn't mention a kill switch. The convenience wrapper increases surface; relying on the existing var is YAGNI.
- **Impact**: Low
- **Affected files**: skills/design/scripts/plan-review-loop.sh
