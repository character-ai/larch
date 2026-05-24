### DECISION_1: aggregator schema adaptation for /design ballots
**Resolution**: Add /design-specific input adapter to `aggregate-findings.sh` (or fork it) to handle the absence of severity lines on plan-review ballots.
**Disposition**: voted
**Vote tally**: THESIS=0, ANTI_THESIS=3
**Thesis summary**: Use `aggregate-findings.sh` as-is and bound the risk with a duplicate-finding fixture test that proves aggregation changes only dedup shape — schema conformance can be added cheaply as part of the fixture authoring.
**Antithesis summary**: `aggregate-findings.sh` enforces a `- **Severity**: important|latent|nit` line at the merge-validator boundary (lines 241-248, 628-632), but the canonical /design `FINDING_N` template in `plan-review.md` (lines 152-158) carries only title/concern/proposed-resolution fields — `tally-plan-review.sh` does not inject severity either, so forcing /design ballots through the unchanged aggregator is a hard mechanical contract failure, not a fixture-bounded risk.
**Why antithesis prevails**: All three judges anchored on the explicit `block_has_severity` validator in `aggregate-findings.sh:628-632`. The thesis's concession that conformance "can be added cheaply" is the antithesis's point — that conformance work IS the adapter, just smuggled under a different label. The cheapest concrete path is a thin shim in `plan-review-loop.sh` that injects synthetic severity lines into the ballot before aggregator invocation OR a `--input-mode=plan` flag on `aggregate-findings.sh` that opts the severity check out for /design callers. The plan in Step 2b MUST resolve this schema gap explicitly — `aggregate-findings.sh` cannot be invoked unchanged on /design ballots.

### DECISION_2: 0-judge fallback semantics
**Resolution**: Signal-only — plan-review-loop.sh emits `LOOP_STATUS=main-agent-vote-required` when all three voters fail; SKILL.md's existing main-agent-vote-required prose handles the rest.
**Disposition**: voted
**Vote tally**: THESIS=3, ANTI_THESIS=0
**Thesis summary**: `tally-plan-review.sh` already emits `TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required` when `eligible_count==0` (lines 105-110), and SKILL.md (around line 709) carries the canonical main-agent adjudication prose; propagating this as `LOOP_STATUS=main-agent-vote-required` keeps the MAV invariant in one place.
**Antithesis summary**: A synthetic Claude subprocess fallback (a second `launch-claude-review.sh` invocation labeled as "fallback judge") would recover the panel without escalating to main-agent adjudication, mirroring the failure-recovery pattern in `dispatch-code-voters.sh:285-301`.
**Why thesis prevails**: The 0-judge path is already a defined, safe, documented exit; adding a synthetic fallback launch grows the control surface without changing the six-artifact contract. Judges noted the antithesis's own concession that aggregator absorption and session-root artifact equivalence dominate behavioral risk — adding new branches in the same PR contradicts the "narrow refactor" framing. The synthetic fallback can be revisited in the multi-round companion when convergence semantics make the cost/benefit clearer.

### DECISION_3: reuse `collect-findings.sh` vs use only `collect-agent-results.sh`
**Resolution**: Use only `collect-agent-results.sh` (the existing /design pattern). Convert raw reviewer outputs to ballot.txt inline in plan-review-loop.sh (one helper function).
**Disposition**: voted
**Vote tally**: THESIS=3, ANTI_THESIS=0
**Thesis summary**: `scripts/test-design-structure.sh` (around lines 216-229) is a CI-enforced contract pinning `collect-agent-results.sh --timeout 1860 --substantive-validation --validation-mode` as the Step 3 collector; keeping that contract intact while adding a small inline ballot helper is the smallest blast radius.
**Antithesis summary**: `collect-findings.sh` is the existing /review converter from raw reviewer outputs to `findings.md`; reusing it (with `--review-tmpdir $DESIGN_TMPDIR`) consolidates the conversion logic, at the cost of resolving a flag-parity gap with `collect-agent-results.sh`.
**Why thesis prevails**: The CI pin is decisive. `collect-findings.sh` uses `--findings-file`/`--oos-file` rather than a `--review-tmpdir` for output staging, and its flag surface diverges from what plan-review currently uses. Patching that compatibility plus updating the test pin is more code touched than a ~20-line inline helper that converts raw outputs to ballot blocks. The antithesis's concession — that reuse requires a compatibility patch — is the deciding factor.

### DECISION_4: aggregator kill switch — /design-specific vs reuse existing
**Resolution**: Rely on existing `LARCH_AGGREGATOR_DISABLED=1` (per Codex-Innovation's verification that the env var already exists in `aggregate-findings.sh`). No new /design-specific variable.
**Disposition**: voted
**Vote tally**: THESIS=2, ANTI_THESIS=1
**Thesis summary**: `aggregate-findings.sh` (around lines 121-127) already provides the exact disable mechanism via `LARCH_AGGREGATOR_DISABLED=1`; there is no existing `LARCH_DESIGN_USE_AGGREGATOR` contract to preserve, so a /design-specific wrapper is strictly additive surface that must be documented, tested, and kept synchronized.
**Antithesis summary**: A two-line `LARCH_DESIGN_USE_AGGREGATOR=false → export LARCH_AGGREGATOR_DISABLED=1` wrapper in `plan-review-loop.sh` gives /design-specific discoverability and reduces operator confusion when the same variable controls both /review and /design behavior.
**Why thesis prevails**: Strict-minority pushback (1-judge) on operator discoverability is real but does not outweigh the synchronization cost of an additive wrapper. The deciding factor: this refactor's framing is "no behavior change" — adding even a small new env-var contract creates a future drift surface. Operators who need /design-specific rollback can use the existing `LARCH_AGGREGATOR_DISABLED=1`; documentation can call this out in `plan-review-loop.md`. The minority concession is captured in the implementation by adding a one-line documentation pointer in `plan-review-loop.md` explaining that `LARCH_AGGREGATOR_DISABLED=1` is the kill switch.

