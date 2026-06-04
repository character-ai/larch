### FINDING_1: Dynamic reviewer totals undercount emitted Codex twin rows
- **Reviewer(s)**: Cursor-Arch, Codex-Innovation
- **Severity**: important
- **Concern**: Codex dynamic twin rows are not reflected in dynamic slot accounting, so `DYNAMIC_SLOTS`, `SLOT_COUNT`, and launch breadcrumbs can report fewer reviewers than were actually emitted/launched.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: When both vendors are up, increment dynamic counts for each emitted dynamic row (or derive `DYNAMIC_SLOTS`/`SLOT_COUNT` from manifest line count); extend `test-dispatch-panel.sh` dynamic cases to assert doubled dynamic totals and breadcrumb math
  - From Codex-Innovation: Increment DYNAMIC_SLOTS per emitted dynamic row or derive it from manifest rows, then update dispatch-panel tests and docs


### FINDING_2: Codex specialist raw outputs would be committed to run logs
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic
- **Severity**: important
- **Concern**: The run-log filter excludes Cursor specialist raw outputs but not new Codex specialist raw outputs, so `codex-specialist-*-output.txt` files could be included in committed round logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add scripts/larch-log.sh and its test/docs to the plan; exclude codex-specialist-*-output.txt and sidecars alongside cursor-specialist patterns
  - From Codex-Pragmatic: Extend the exclusion pattern and larch-log tests to cover codex-specialist-*-output.txt raw outputs alongside cursor-specialist-*-output.txt.


### FINDING_3: Phrase-sync plan misses runtime, generator, and contract sources
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Codex-dyn-phrase-sync-completeness
- **Severity**: important
- **Concern**: The phrase migration for replacing stale `6 Cursor specialists` wording omits several canonical or harness-checked owners, including the `/implement` Step 5 banner, topology generator sources, and sibling contract docs. This can leave stale runtime output, fail docs-sync/generator checks, or regenerate stale topology text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add these files to the phrase-sync step and replace the old phrase with the same canonical wording used in README/docs/topology.tsv/test-quick-mode-docs-sync.sh
  - From Cursor-Innovation: Add `skills/implement/SKILL.md` to the atomic phrase-replacement file list (same canonical string as README/docs)
  - From Codex-Innovation: Update scripts/generate-topology-docs.sh with the canonical phrase before regenerating docs/topology.md
  - From Cursor-Pragmatic: Add skills/implement/SKILL.md to the file list and replace the banner phrase atomically with the canonical string
  - From Codex-Pragmatic: Add skills/implement/SKILL.md to the phrase-sync change and replace the banner text with the same canonical phrase.
  - From Cursor-Requirements: Add `### UPDATED: skills/implement/SKILL.md` — replace the Step 5 banner phrase with the same canonical string used in README/docs and `POS_MARKERS`
  - From Codex-Requirements: Add these files to the update list; apply the canonical phrase to the generator source before regenerating docs/topology.md, and update the quick-mode docs-sync .md with the script
  - From Codex-dyn-phrase-sync-completeness: Add UPDATED entries for skills/implement/SKILL.md and scripts/test-quick-mode-docs-sync.md; change the Step 5 banner and sibling marker table to the same canonical phrase.
  - From Codex-dyn-phrase-sync-completeness: Add UPDATED entries for scripts/generate-topology-docs.sh and scripts/generate-topology-docs.md; change the static header/contract text to the canonical phrase before regenerating docs/topology.md.


### FINDING_4: Threshold denominator change omits direct harness and contract docs
- **Reviewer(s)**: Codex-Edge, Codex-Innovation, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-output-naming-contracts, Cursor-dyn-reversion-completeness, Codex-dyn-reversion-completeness, Codex-dyn-phrase-sync-completeness
- **Severity**: important
- **Concern**: The plan changes reviewer failure threshold semantics, defaults, and `--intended-slots` behavior but omits the dedicated threshold regression harness and contract documentation that still encode 6-slot/legacy assumptions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Add skills/review/scripts/test-check-reviewer-failure-threshold.sh and skills/review/scripts/test-check-reviewer-failure-threshold.md to the plan; update cases for default 4, --intended-slots 4 and 8, both-down launched=4, and dynamic Codex-twin exclusion
  - From Codex-Innovation: Update this harness and its .md contract for --intended-slots 4 and 8, the new default, and dynamic Codex-output exclusion cases
  - From Codex-Pragmatic: Add test-check-reviewer-failure-threshold.sh and .md to the plan; update cases to exercise --intended-slots 4 and 8 plus the fallback default.
  - From Codex-Requirements: Add check-reviewer-failure-threshold.md and test-check-reviewer-failure-threshold.sh to the plan and testing list; cover --intended-slots 4 and 8, default 4, launched-slots equal intended, and dyn-*-codex-output exclusion
  - From Cursor-dyn-output-naming-contracts: Add skills/review/scripts/test-check-reviewer-failure-threshold.sh (and sibling .md) to the plan: migrate fixtures to --intended-slots 4/8, and add one case with REVIEWER_FILE ending in dyn-example-codex-output.txt to lock the Codex dynamic-twin exclusion contract
  - From Cursor-dyn-reversion-completeness: Add `skills/review/scripts/test-check-reviewer-failure-threshold.sh` and `skills/review/scripts/check-reviewer-failure-threshold.md` to the UPDATED list; add 4-slot and 8-slot cases with explicit `--intended-slots` / `--launched-slots`; retire 12-record HARD fixtures unless they pass matching flags
  - From Codex-dyn-reversion-completeness: Add these files as explicit edit targets; update tests/docs for --intended-slots, default 4, 4-slot and 8-slot thresholds, and dynamic-slot exclusion under the new naming
  - From Codex-dyn-phrase-sync-completeness: Add these files as explicit edit targets; update tests/docs for --intended-slots, default 4, 4-slot and 8-slot thresholds, and dynamic-slot exclusion under the new naming


### FINDING_5: Pre-rendered reviewer prompts are not regenerated after source prompt edits
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The plan edits reviewer source prompt files but does not regenerate the pre-rendered bodies used at runtime, so Cursor/Codex prompts can miss the intended folded structure and plan-fidelity changes and generator checks can drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Regenerate agents/pre-rendered/reviewer-edge-cases-body.txt, agents/pre-rendered/reviewer-testing-body.txt, and agents/pre-rendered/.manifest via scripts/generate-pre-rendered-reviewer-prompts.sh


### FINDING_7: Retired structure and plan-fidelity slugs must remain reserved
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The plan treats removal of retired `structure` and `plan-fidelity` reserved slugs as optional cleanup, which conflicts with the goal of preventing those folded lenses from returning as dynamic archetypes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Remove the optional cleanup; keep structure and plan-fidelity reserved in both lists with a short comment.
  - From Codex-Requirements: Remove the optional cleanup; keep structure and plan-fidelity reserved in both lists, and only update comments or prompt text as needed


### FINDING_8: Dynamic vendor gating can duplicate Codex dynamic reviews
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: Dynamic slots are described as keeping the existing Cursor-primary row and appending a Codex twin, rather than gating rows by vendor availability like static slots. In Codex-only runs, that can cause Codex to review the same dynamic archetype twice.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Revise the plan to gate dynamic Cursor rows on CURSOR_AVAILABLE, Codex rows on CODEX_AVAILABLE, and emit one Cursor-primary Claude-fallback row only when neither vendor is available; add single-vendor dynamic assertions


### FINDING_9: Diagram stale-phrase check is only manual
- **Reviewer(s)**: Codex-dyn-phrase-sync-completeness
- **Severity**: important
- **Concern**: The review diagram can retain stale `6 Cursor specialists` topology text because the plan relies on manual confirmation rather than any harness-enforced assertion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-phrase-sync-completeness: Add a minimal grep assertion in an existing docs-sync or review-structure harness that forbids the stale phrase or requires the canonical phrase in skills/review/diagram.svg; keep manual render confirmation only as a supplemental visual check.

