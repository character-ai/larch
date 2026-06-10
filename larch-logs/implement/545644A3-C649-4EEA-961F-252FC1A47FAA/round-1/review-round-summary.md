# Review Round 1

- Mode: `diff`
- 6 accepted, 6 rejected (3 neutral)

## Accepted Findings

### FINDING_10: dispatch-plan-review-panel.md still claims 10 static slots
- **Reviewer(s)**: codex-specialist-security-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/dispatch-plan-review-panel.md` still says static plan review renders “10 slots,” contradicting the current four-archetype-per-vendor manifest.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt: Remove the hardcoded count and describe it as static plan-review prompts/slots.
  - From cursor-specialist-correctness-output.txt: Rewrite Purpose with count-free per-archetype wording.
  - From cursor-specialist-testing-output.txt: Remove the 10-slot count or describe per-archetype vendor rows without a fixed total.


### FINDING_13: test-dispatch-panel still expects four both-down phase3 outputs
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `skills/review/scripts/test-dispatch-panel.sh` still requires at least four phase3 outputs for the both-down path, but the reduced three-archetype path creates three Claude phase3 files, causing the test to fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Lower threshold to 3 (or assert exact count).


### FINDING_14: dynamic plan-review scout still believes Edge is an active static archetype
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The `/design` dynamic scout prompt and wrapper still describe or reserve a five-personality static panel including `edge`, so HARD `/design` scouting may suppress or misclassify dynamic reviewer suggestions based on a slot that is no longer launched.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Update the scout prompt and wrapper docs/filter to match the new four-slot panel, or explicitly document `edge` as a folded historical/reserved lens rather than an active static archetype, and add/update the wrapper harness to pin the new wording.
  - From codex-specialist-testing-output.txt: Update the prompt to list the four current archetypes and add a prompt/wrapper assertion.


### FINDING_2: docs/review-agents.md publishes stale /design and /review topology
- **Reviewer(s)**: cursor-specialist-security-output.txt, codex-specialist-security-output.txt, cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-risk-integration-output.txt, dyn-architecture-output.txt
- **Severity**: important
- **Concern**: `docs/review-agents.md` still describes removed or hardcoded reviewer topology: `/design` lists the removed Edge-cases/Failure-modes archetype and omits Requirements/Completeness, while `/review` still claims “4 specialists per available vendor” despite runtime dispatch using three static code-review archetypes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Update archetype list and vendor count prose; add 4 specialists per vendor to test-quick-mode-docs-sync STALE_PHRASES.
  - From codex-specialist-security-output.txt: Update this table/paragraph to remove Edge from design, include Requirements, and avoid the hardcoded `/review` count.
  - From cursor-specialist-correctness-output.txt: Replace count-specific wording with specialists per available vendor aligned with dispatch-panel.md.
  - From cursor-specialist-correctness-output.txt: Update the table to Arch Innovation Pragmatic Requirements only.
  - From codex-specialist-correctness-output.txt: Update the /design archetype list and replace the /review hardcoded count with count-free wording or authoritative links.
  - From cursor-specialist-edge-cases-output.txt: Rewrite the table row to Arch Innovation Pragmatic Requirements per topology.md.
  - From cursor-specialist-edge-cases-output.txt: Replace count with specialists per vendor or list correctness edge-cases testing.
  - From codex-specialist-edge-cases-output.txt: Sweep these remaining references to remove fixed counts and `Edge`/`security` static-slot claims, pointing readers to `skills/shared/topology.tsv` / dispatch scripts where possible.
  - From cursor-specialist-testing-output.txt: Replace with count-free specialists-per-vendor wording aligned with dispatch-panel.md.
  - From cursor-specialist-testing-output.txt: Update row to arch innovation pragmatic requirements only.
  - From dyn-risk-integration-output.txt: Update line 95 to the four remaining plan-review lenses (Arch, Innovation, Pragmatic, Requirements) and line 100 to count-free “specialists per vendor” wording consistent with `skills/shared/topology.tsv` and `dispatch-panel.sh`.
  - From dyn-architecture-output.txt: Rewrite that cell to match the four static lenses (`Architecture/Standards`, `Innovation/Exploration`, `Pragmatism/Safety`, `Requirements/Completeness`) and note that former edge/failure coverage is folded into `arch` and `pragmatic` prompts per `skills/design/scripts/render-plan-review-prompt.sh`.
  - From dyn-architecture-output.txt: Change line 100 to the same count-agnostic phrasing used elsewhere (“specialists per vendor”) and point readers to `dispatch-panel.md` for the authoritative archetype list.


### FINDING_4: docs/collaborative-sketches.md still says /review has four active archetypes
- **Reviewer(s)**: cursor-specialist-security-output.txt, codex-specialist-security-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, dyn-architecture-output.txt
- **Severity**: important
- **Concern**: `docs/collaborative-sketches.md` still documents `/review` fallback behavior as “Four active archetypes” per vendor, contradicting the reduced three-archetype static review panel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Replace with active static archetypes wording without a stale count.
  - From codex-specialist-security-output.txt: Replace the count with count-free wording or list the current active archetypes.
  - From codex-specialist-correctness-output.txt: Use count-free wording and add Four active archetypes / 4 specialists per available vendor to stale phrase checks.
  - From cursor-specialist-edge-cases-output.txt: Remove the count or name the three active archetypes.
  - From codex-specialist-edge-cases-output.txt: Sweep these remaining references to remove fixed counts and `Edge`/`security` static-slot claims, pointing readers to `skills/shared/topology.tsv` / dispatch scripts where possible.
  - From dyn-architecture-output.txt: Replace “Four active archetypes” with count-agnostic language (“active static archetypes” or “specialists per vendor”) consistent with `skills/review/scripts/dispatch-panel.md` and the updated fallback table intent in `docs/collaborative-sketches.md`.


### FINDING_5: skills/design/SKILL.md example still advertises stale 10-reviewer panel
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: A `/design` progress example still says the Step 3 plan-review panel has 10 reviewers with removed Edge slots, giving operators stale breadcrumbs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Remove count from example; align reviewer table with four archetypes.


