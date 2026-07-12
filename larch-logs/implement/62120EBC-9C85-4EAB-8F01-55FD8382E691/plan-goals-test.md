## Goal
Implement issue #7018: [IMPLEMENTING] Add another specialist review archetype to /design, /implement, and /review: architectural guidelines and invariants compliance checker.

## Implementation Plan
## Plan

## Approach

Add `architectural-compliance` as a hand-maintained static code-review specialist, matching `correctness`, `edge-cases`, and `testing` for tiering, vendors, pruning, voting, manifest coverage, and test fixtures.

Restrict rendered architectural knowledge to this specialist and the existing `/design` `arch` reviewer. Keep coder and plan-drafter feeds unchanged.

### UPDATED: python/larch/core/config.py

- Add `architectural-compliance` to `_CODE_REVIEW_ARCHETYPES`.
- Preserve the generated slot matrix and document all four static lenses.

### UPDATED: python/larch/review/review_pipeline_shared.py

- Add `architectural-compliance` to `STATIC_REVIEWERS` so manifest-missing coverage requires its output.

### UPDATED: python/larch/rendering/rendering.py

- Render architectural knowledge only for `reviewer-architectural-compliance` in code review.
- Keep invariants at every tier and guidelines above TRIVIAL.
- Include architectural content and its hash in payload accounting and cache keys only for that specialist.
- Strengthen `/design` `arch` to explicitly review guideline and invariant compliance.
- Attach architectural knowledge only to static `/design` `arch`, excluding other static and dynamic plan reviewers.

### NEW: agents/reviewer-architectural-compliance.md

- Add the hand-maintained specialist with the existing static-specialist frontmatter, evidence tools, necessity gate, output grammar, and OOS limits.
- Require concrete `I-*` or `G-*` citations and code evidence; exclude undocumented preferences and style advice.
- Retain the architectural-policy carve-out only here.

### NEW: agents/pre-rendered/reviewer-architectural-compliance-body.txt

- Generate the runtime body from the new specialist agent.

### UPDATED: agents/pre-rendered/.manifest

- Regenerate checksums and add the new body.

### UPDATED: skills/shared/reviewer-templates.md

- Remove the `I-*` and `G-*` carve-out from unified and non-compliance specialist templates.

### UPDATED: agents/code-reviewer.md

- Regenerate from the updated shared template.

### UPDATED: agents/reviewer-plan-fidelity.md

- Regenerate without architectural-compliance instructions.

### UPDATED: agents/reviewer-code-robustness.md


### UPDATED: agents/reviewer-security-structure-tests.md


### UPDATED: agents/pre-rendered/reviewer-plan-fidelity-body.txt

- Regenerate from the updated agent.

### UPDATED: agents/pre-rendered/reviewer-code-robustness-body.txt


### UPDATED: agents/pre-rendered/reviewer-security-structure-tests-body.txt


### UPDATED: python/larch/design/plan_scout.py

- Reserve `architectural-compliance` for both scout modes.
- Prevent code-review scout output from proposing a dynamic duplicate.

### UPDATED: skills/design/scripts/scout-plan-archetypes-prompt.txt

- Reserve the compliance slug and state that static `arch` owns plan architectural compliance.

### UPDATED: skills/review/SKILL.md

- Add `architectural-compliance` to the static panel and clarify it alone receives architectural knowledge.

### UPDATED: skills/implement/SKILL.md

- Reserve the new static slug from coder-scout dynamic proposals.

### UPDATED: skills/shared/topology.tsv

- Project the four-specialist code-review panel and vendor-per-tier behavior.
- Keep `/design` at four static personalities because compliance remains folded into `arch`.

### UPDATED: docs/topology.md

- Regenerate the topology projection.

### UPDATED: docs/review-agents.md

- Document the dedicated compliance specialist.
- Remove claims that unified or unrelated reviewers enforce supplied policy.
- Describe `/design` compliance as an `Architecture/Standards` responsibility while preserving tier, vendor, pruning, and no-fallback contracts.

### UPDATED: docs/workflow-lifecycle.md

- Replace the claim that every Step 5 reviewer receives architectural knowledge with the dedicated-specialist contract.
- Keep Step 2 coder feeds, manifest acknowledgment, and Step 8 assessment unchanged.

### UPDATED: README.md

- Distinguish architectural-knowledge author feeds from specialist reviewer feeds.

### UPDATED: python/skill-closure-baseline.json

- Regenerate the prompt-closure baseline.

### UPDATED: scripts/test-review-structure.sh

- Add `reviewer-architectural-compliance` to the specialist-agent header assertion and update its count.

### UPDATED: python/review_test_support.py

- Expand shared review-core dispatch stubs’ external and Claude static-output loops, full manifests, and collector records to include `architectural-compliance`.
- Update the missing-static-output fixture variant so coverage tests can specifically represent missing compliance output without retaining a three-slot assumption.

### UPDATED: python/tests/rendering/test_rendering.py

- Verify compliance receives tier-appropriate architectural blocks while ordinary code specialists receive neither block.
- Verify only static `/design` `arch` receives the blocks and associated payload accounting.
- Cover cache separation between compliance and ordinary specialists.

### UPDATED: python/tests/core/test_external_role_defaults.py

- Update panel-slot fixture expectations to include Cursor and Codex compliance slots.

### UPDATED: python/tests/review/test_review_pipeline.py

- Update tier matrix, slot-set, model-role, static-count, and manifest-missing coverage expectations from three to four code-review archetypes.
- Verify missing compliance output fails fallback coverage.
- Expand custom review-core dispatch, manifest, and collector stubs—including the static-plus-dynamic straggler fixture—to emit compliance records and coherent slot counts.

### UPDATED: python/tests/design/test_plan_scout.py

- Verify the compliance slug is rejected as a dynamic review or plan-review archetype.

## Edge cases

- Missing or invalid architecture files leave compliance and `arch` prompts usable without empty policy sections.
- TRIVIAL receives invariants but not guidelines.
- Dynamic plan-review prompts do not inherit policy from an architecture focus area.
- Cache hits never reuse a compliance prompt for another specialist.
- A missing manifest still requires compliance through `STATIC_REVIEWERS`.
- Absent vendors, round-two pruning, and shared test stubs account for the added slot.

## Failure modes

- Broad renderer plumbing could leak policy to every reviewer.
- A stem or slug mismatch could create the slot but omit policy context.
- Stale generated agents or bodies could preserve the removed carve-out.
- Manifest-missing fallback or shared review-core stubs could omit compliance and produce false coverage results.
- Fixed-count tests, closure baseline, or docs could retain the three-specialist panel.
- Missing scout reservations could duplicate compliance coverage dynamically.

## Testing strategy

- Run focused rendering, role-default, review-pipeline, and plan-scout pytest files.
- Run `scripts/test-review-structure.sh`.
- Run pre-rendered reviewer generation, affected reviewer generators, and topology-doc generation.
- Run `python3 python/cli.py lint skill-closure-growth --write`, then verify without `--write`.
- Run `python3 python/cli.py generate check`.
- Run changed-file Python lint and the topology rule-path check.
- Grep generated prompts and bodies to confirm only compliance retains the architectural carve-out.
- Exercise TRIVIAL and HARD prompts for compliance, an ordinary specialist, `/design` `arch`, and a non-Arch plan reviewer.

## Acceptance

- Run focused rendering, role-default, review-pipeline, and plan-scout pytest files.
- Run `scripts/test-review-structure.sh`.
- Run pre-rendered reviewer generation, affected reviewer generators, and topology-doc generation.
- Run `python3 python/cli.py lint skill-closure-growth --write`, then verify without `--write`.
- Run `python3 python/cli.py generate check`.
- Run changed-file Python lint and the topology rule-path check.
- Grep generated prompts and bodies to confirm only compliance retains the architectural carve-out.
- Exercise TRIVIAL and HARD prompts for compliance, an ordinary specialist, `/design` `arch`, and a non-Arch plan reviewer.

oversize_override: operator
diff_lines: 480

## Test plan
(no test plan section in plan-file)
