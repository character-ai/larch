### OOS_1: Per-source `oos-5` ineligibility needs to be explicit
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: The skill does not say whether `oos-5` should continue for unaffected sources when only some sources are temporarily ineligible, so an orchestrator could stop the whole phase and leave approved groups unapplied.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Clarify per-source ineligibility: oos-5 still runs; only affected sources are excluded from --source-issues and deferred-close.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected (latent-rerouted)

### OOS_2: Free-prose rescue matching needs ambiguity handling
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: A free-form rescue instruction can map to zero or multiple merit keys, which makes it possible to keep or reject the wrong items.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add default-keep-on-ambiguity and require re-confirmation when rescue matches multiple keys.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected (latent-rerouted)

### OOS_3: `STATUS=blocked` items must stay blocked through merit gating
- **Reviewer(s)**: dyn-dyn-oos-merit
- **Severity**: important
- **Concern**: If dependency wiring fails, a blocked item can be treated as eligible and enter merit selection, which risks closing work that should remain open.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-oos-merit: On `STATUS=blocked`, treat the item as blocked for merit and closure even when the dependency wire fails (with a warning); only run the merit gate when the item is genuinely not blocked (`STATUS=ambiguous` / file-exists actual paths).


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)
