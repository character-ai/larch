## Decision 1: Tier enumeration
- **Question**: How many tiers should `/design` have after consolidation?
- **Resolution**: Exactly two: `SIMPLE` and `HARD`. `TRIVIAL` is removed entirely.
- **Source**: user

## Decision 2: New SIMPLE semantics
- **Question**: What does the new SIMPLE tier do?
- **Resolution**: No sketch phase (Step 2a skipped), no dialectic (Step 2a.5 skipped). Runs the FULL external review panel (10 static + up to 12 dynamic externals + 3-judge voting). Plan-command validator runs. Same Gates A/B/C as HARD.
- **Source**: user

## Decision 3: New HARD semantics
- **Question**: What does the new HARD tier do?
- **Resolution**: Unchanged from current HARD behavior. 4 personality sketches (Cursor Arch/Edge + Codex Innovation/Pragmatic), Step 2a.5 dialectic on contested decisions, full panel review, validator runs.
- **Source**: user

## Decision 4: run-params.json schema collapse
- **Question**: Should run-params.json retain `quick_mode`, `review_budget`, `workflow_path`, `sketch_budget` as separate fields?
- **Resolution**: No. Collapse to a single enum: `design_classification: SIMPLE | HARD`. All behavior derived from it. Schema version bumps to 2. Keep `partition_requested` and `brainstorm_requested`. Drop `design_classification_source` and `design_classification_reason` as well (no longer meaningful with caller-forwarded-only).
- **Source**: user

## Decision 5: --trivial argv handling
- **Question**: What should `/design --trivial …` do after removal?
- **Resolution**: Hard error with a clear message; exit 1. No silent upgrade, no deprecation warning, no backward-compat shim.
- **Source**: user

## Decision 6: Tier-gate UX
- **Question**: What does the tier gate prompt look like after TRIVIAL is gone?
- **Resolution**: 2-option AskUserQuestion (SIMPLE / HARD). No automatic default; user picks.
- **Source**: user

## Decision 7: Cleanup scope
- **Question**: How broad should the cleanup be?
- **Resolution**: Full repo cleanup. All references to TRIVIAL_DOC_ONLY, --trivial, quick_mode, sketch_budget=0|2 (quick-mode path), review_budget, workflow_path enum fields, plan-review-quick.md, read-design-review-budget.sh, invoke-plan-validator-if-not-quick.sh gate, NO_SKETCHES_CLASSIFIED_TRIVIAL sentinel. Files: skills/design/SKILL.md, references/*.md, scripts inside the design skill, scripts/write-run-params.sh, scripts/test-write-run-params.{sh,md}, scripts/write-run-params.md, scripts/test-design-structure.sh, docs/skills.md, docs/workflow-lifecycle.md, README.md, .claude-plugin/plugin.json. CHANGELOG.md historical entries are NOT rewritten (history is immutable); the new CHANGELOG entry is added by /implement on landing.
- **Source**: user

## Decision 8: Sentinel rename
- **Question**: The `NO_SKETCHES_CLASSIFIED_TRIVIAL` sentinel string is misnamed after the rename.
- **Resolution**: Rename to `NO_SKETCHES_CLASSIFIED_SIMPLE` (still meaningful — new SIMPLE is the no-sketch tier). The `TRIVIAL_DOC_ONLY` classification enum value is removed entirely (no replacement).
- **Source**: user

## Decision 9: Step 5d L3-velocity comment
- **Question**: Keep or remove the gated tracking comment from issue #2670 → #2672?
- **Resolution**: Remove the entire Step 5d block. No backward-compat paper trail. Minimal complexity. Also remove the deferred L3 velocity prose from references/flags.md.
- **Source**: user

## Decision 10: plan-review-quick.md
- **Question**: Keep or delete the quick plan-review reference?
- **Resolution**: Delete. No tier uses the Claude-only quick review path anymore (new SIMPLE uses full external panel).
- **Source**: user

## Decision 11: review-budget gating helpers
- **Question**: What happens to read-design-review-budget.sh and invoke-plan-validator-if-not-quick.sh?
- **Resolution**: Delete read-design-review-budget.sh (no field to read). Inline the validator call (or rename to invoke-plan-validator.sh) — validator now always runs unconditionally on both SIMPLE and HARD.
- **Source**: user

## Decision 12: Per-tier prose in approval-gates.md
- **Question**: Keep the per-tier narrative ("--trivial typically picks Ready for review on first prompt", etc.)?
- **Resolution**: Drop the per-tier narrative entirely. Cross-tier invariant sentence collapses to "Gates apply uniformly across SIMPLE and HARD."
- **Source**: user

## Decision 13: Gate C "Re-run review panel" cap (per-tier)
- **Question**: Should the review panel re-run loop have an enforced cap, and is the cap per-tier?
- **Resolution**: Yes, per-tier. **SIMPLE = 3 total review runs** (initial + at most 2 re-runs). **HARD = 5 total review runs** (initial + at most 4 re-runs). After the cap is reached, the "Re-run review panel" option is hidden from Gate C; only Approve / Discuss further remain. Gate A "Discuss more" stays uncapped.
- **Source**: user

## Decision 14: CHANGELOG history immutability
- **Question**: Should historical CHANGELOG entries that mention --trivial be edited?
- **Resolution**: No. Historical entries describe past releases and remain accurate to those releases. The new CHANGELOG entry for this PR is added by /implement.
- **Source**: codebase (commit history immutability convention)

## Decision 15: Per-tier emphasis for designer and reviewers
- **Question**: Should the SIMPLE/HARD tiers carry different emphasis instructions for both the plan author (Step 2b) and the plan reviewers (Step 3)?
- **Resolution**: Yes.
  - **SIMPLE**: Emphasis on **simplicity and minimizing changes**. The plan author bias is "smallest change that achieves the goal; resist adding files, abstractions, refactors, or scope not strictly required." Reviewer bias is "flag scope creep and unnecessary complexity; do not request additions; prefer EXONERATE on nits and forward-looking concerns; accept only findings whose fix is materially required for correctness."
  - **HARD**: Emphasis on **thoroughness**. The plan author bias is "surface all relevant edge cases, failure modes, and cross-cutting concerns; do not omit considerations to save effort." Reviewer bias is "flag missed considerations; request additions when warranted; engage seriously with edge-case and architecture findings."
- **Implementation surface**: tier emphasis text is injected into (a) the Step 2b plan-writer self-direction prose in SKILL.md, (b) the Step 3 reviewer prompt template (`render-plan-review-prompt.sh` / `plan-review.md`), and (c) the tier-gate AskUserQuestion option descriptions in Step 0b. Concrete wording deferred to the implementation plan (Step 2b).
- **Source**: user
