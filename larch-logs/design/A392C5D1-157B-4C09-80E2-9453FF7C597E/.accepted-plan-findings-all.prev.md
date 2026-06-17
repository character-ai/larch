### FINDING_1: Plan-review embedded assets still call deleted prune scripts
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: blocking
- **Concern**: The plan deletes `scripts/reviewer-prune.sh` and `scripts/lib-prune-decision.sh` but does not update the gzip-embedded `/design` plan-review runtime materialized from `python/plan_review.py` (`_LEGACY_ASSETS`, e.g. `dispatch-plan-review-panel.sh` and `plan-review-loop.sh`). Those embedded bash bodies still source or invoke the deleted script paths while the change plan only updates prose or ports the in-scope `review_pipeline` surface. After deletion, `python3 python/cli.py plan-review run` / panel dispatch can fail before rounds 3–4 pruning or recording completes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: python/plan_review.py: patch _decode_legacy_asset for dispatch-plan-review-panel.sh to call python3 "$PLUGIN_ROOT/python/cli.py" review reviewer-prune (mirror the existing dispatch-waterfall rewrite) or regenerate the embedded blob; add pytest in python/test_plan_review.py asserting embedded panel no longer references scripts/reviewer-prune.sh.
  - From Codex-Arch: Add python/plan_review.py, and python/plan_review_panel.py if needed, to the change plan. Update the materialized embedded plan-review loop/panel to use the new review reviewer-prune CLI and Python prune-decision helpers, or generate temp-root compatibility wrappers before deleting the scripts
  - From Cursor-Innovation: Add ### UPDATED: python/plan_review.py: extend _decode_legacy_asset (and regenerate affected _LEGACY_ASSETS blobs if needed) to replace reviewer-prune.sh and lib-prune-decision.sh invocations with python3 python/cli.py review reviewer-prune record|filter; add pytest like test_embedded_plan_review_loop_uses_migrated_collector asserting embedded assets no longer reference deleted script paths
  - From Codex-Innovation: Update python/plan_review.py in this PR: patch or regenerate the embedded plan-review assets so they call python3 python/cli.py review reviewer-prune and no longer source scripts/lib-prune-decision.sh, or route their prune decisions through the new Python helpers before deleting the scripts. Also update the plan-review tests that decode or exercise those embedded assets.
  - From Cursor-Pragmatic: Keep reviewer-prune.sh deletion in G1, but add an explicit plan step to regenerate the affected _LEGACY_ASSETS blobs (at minimum skills/design/scripts/dispatch-plan-review-panel.sh and skills/design/scripts/plan-review-loop.sh) to invoke python3 "$PLUGIN_ROOT/python/cli.py" review reviewer-prune {filter,record}; add a test_plan_review.py embedded-body assertion mirroring test_embedded_plan_review_loop_uses_migrated_collector
  - From Codex-Pragmatic: Add python/plan_review.py to the plan; regenerate or adjust the embedded dispatch-plan-review-panel.sh and plan-review-loop.sh assets to call python3 "$PLUGIN_ROOT/python/cli.py" review reviewer-prune and use the Python prune-decision helpers while preserving PANEL_PRUNED_EMPTY and ledger KVs
  - From Cursor-Requirements: Add an explicit step to regenerate or hand-edit embedded plan-review assets in python/plan_review.py so pruning calls python3 python/cli.py review reviewer-prune {record,filter}; add a plan-review pytest or harness assertion for rounds 3-4 prune before deleting scripts/reviewer-prune.sh.
  - From Codex-Requirements: Add python/plan_review.py to the plan and update/regenerate the embedded assets to use python3 python/cli.py review reviewer-prune record/filter and the ported prune-decision logic


### FINDING_2: Retired-path literals remain in lint and config surfaces
- **Reviewer(s)**: Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: blocking
- **Concern**: Retired-path cleanup omits tracked exact references outside the main port/delete list. After `python/migrated-scripts.tsv` records the deleted `reviewer-prune`, `lib-prune-decision`, and `dispatch-panel` paths, remaining literals in `agent-lint.toml`, `.claude/rules/topology-generation.md`, and `scripts/test-review-structure.md` will cause `make lint-retired-scripts` (and thus the required final gate) to fail even though review dispatch moves to `python/review_pipeline.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add agent-lint.toml and .claude/rules/topology-generation.md to Files to modify/create; remove the deleted script allowlist entries and retarget the topology rule path to the live Python review_pipeline authority
  - From Cursor-Requirements: Add ### UPDATED: .claude/rules/topology-generation.md replacing the dispatch-panel.sh paths: entry with python/review_pipeline.py (or drop the line if topology no longer needs that authority).
  - From Codex-Requirements: Include these files in Files to modify/create and replace or remove the retired path references, including the test-review-structure.md contract alongside the shell harness update



