## Proposed Design Outline

### Goals
- Stop the scope-creep ratchet: stop re-baselining each review round on the prior round's bloated plan.
- Add a cumulative drift guard that flags the operator when the plan grows past a threshold multiple of the Step-2b baseline, and blocks silent auto-continue.
- Make Gate B the sole apply point — accepted findings applied only by explicit operator choice, on both tiers.

### Non-goals
- Re-anchoring each review round to the issue text (the issue-anchoring sibling owns that signal).
- Changing the sketch phase, dialectic, or the review-panel composition/voting.
- Changing Gate A or Gate C behavior, except for removing the `--manual` flag surface.

### Approach sketch
- Collapse `plan-review-loop.sh` to a single review pass: no `revise-plan-with-waterfall.sh` between rounds, retire the convergence rule and inter-round auto-apply.
- Gate B (Step 3.5) becomes the only apply surface; delete the `manual_gate_b=false` auto-apply branch so Gate B always prompts for explicit choice.
- Remove `--manual` / `-m` / `manual_gate_b` from the argv parser, run-params schema, and docs.
- Capture a tier-agnostic Step-2b baseline (plan body lines + diff estimate) so the drift guard works on SIMPLE.
- Drift guard compares the current plan vs that baseline; on exceed, fire `AskUserQuestion` (continue / cancel) and block auto-continue.

### Surfaces in scope
- `skills/design/scripts/plan-review-loop.sh`, `run-step3-review.sh`; `skills/design/SKILL.md` (Step 3 branch matrix, Step 2b.5)
- `skills/design/references/approval-gates.md`, `references/flags.md`
- `skills/design/scripts/parse-design-argv.sh`, `scripts/write-run-params.sh`, `design-init-runparams.sh`
- New drift-guard helper + baseline artifact; harnesses (`test-plan-review-loop.sh`, `test-step3-review-cap.sh`, `test-design-structure.sh`, …)

### Open questions
- Drift threshold multiple and whether it is env-configurable (default chosen in plan; e.g. 2× with an env override).
- Whether the Gate-C-level `review-round-count.txt` cap stays (likely yes — operators can still re-run the panel) while the inner `LARCH_DESIGN_ROUND_CAP` becomes vestigial at 1.
