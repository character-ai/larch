## Goal
Split the "Correctness + Edge Cases" reviewer archetype into "Plan Fidelity" and "Code Robustness" specialist archetypes.

Split the "Correctness + Edge Cases" reviewer archetype into two new specialist archetypes: "Plan Fidelity" and "Code Robustness".

## Implementation Plan

### Approach
1. In `skills/shared/reviewer-templates.md`: replace the "## Reviewer: Correctness + Edge Cases" section with two new sections: "## Reviewer: Plan Fidelity" and "## Reviewer: Code Robustness". Update header/footer comments.
2. Create `scripts/generate-reviewer-plan-fidelity-agent.sh` + sibling `.md`.
3. Create `scripts/generate-reviewer-code-robustness-agent.sh` + sibling `.md`.
4. Run generators to produce `agents/reviewer-plan-fidelity.md` and `agents/reviewer-code-robustness.md`.
5. Remove old generator script, sibling doc, and generated agent file for correctness-edges.
6. Update `scripts/generators.tsv`: swap old row for two new rows.
7. Update `.claude/rules/reviewer-archetype-generation.md`: replace old generator in the list.
8. Update `docs/review-agents.md`: remove references to reviewer-correctness-edges.
9. Update `scripts/test-render-specialist-prompt.sh`: remove reviewer-correctness-edges from SPECIALISTS.
10. Update `scripts/test-check-generators.sh`: update expected registry rows.
11. Run `bash scripts/generate-pre-rendered-reviewer-prompts.sh` to regenerate pre-rendered bodies (drops reviewer-correctness-edges-body.txt, adds reviewer-plan-fidelity-body.txt and reviewer-code-robustness-body.txt).

### Edge Cases
- The `generate-pre-rendered-reviewer-prompts.sh` script uses a find-based glob, so it picks up new agent files automatically and drops removed ones when re-run.
- The test-check-generators.sh has a hardcoded expected registry row — must update it precisely.
- docs/review-agents.md lists reviewer usage; the "Correctness-Edges" label won't appear in the review panel (which uses hand-maintained files) so only doc/comment references need updating.

### Testing Strategy
- `bash scripts/test-render-specialist-prompt.sh` — verifies new agent files exist and can be rendered
- `bash scripts/test-check-generators.sh` — verifies generators.tsv stays consistent
- `make lint` (agent-lint, pre-commit) — verifies no drift or lint failures

## Test plan
- bash scripts/test-render-specialist-prompt.sh
- bash scripts/test-check-generators.sh
- make lint
