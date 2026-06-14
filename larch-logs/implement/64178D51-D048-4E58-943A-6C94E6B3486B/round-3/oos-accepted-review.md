### OOS_4: [OUT_OF_SCOPE] Architecture vs plan — wrapper cutover done, runtime still legacy bash blobs
- **Reviewer(s)**: dyn-plan-cli-contracts-output.txt
- **Severity**: important
- **Concern**: `python/plan_review.py` and `python/plan_review_panel.py` are mostly `_run_legacy` wrappers around gzip-embedded retired scripts, not the native stdlib port the C3a1 plan describes. Wrapper argv cutover (`design-step3-review.sh` → `plan-review run`, etc.) is consistent, but runtime behavior still depends on frozen bash blobs plus live symlinked helpers (`design-postplan-emit.sh`, `collect-agent-results.sh`, …).
- **Suggested revisions (informational for voters; coder decides)**:


### OOS_5: [OUT_OF_SCOPE] `SECURITY.md` publish-allowlist prose broader than concise runtime model
- **Reviewer(s)**: dyn-artifact-security-output.txt
- **Severity**: latent
- **Concern**: `SECURITY.md` publish-allowlist prose (around line 277) still describes a broader round-level set (`findings.md`, `ballot.txt`, `voting-tally.md`, etc.) than the concise staging surface in `python/plan_review.py:round_artifact_included`. Runtime publish behavior matches the concise model plus `design_artifact_excluded()` skips; the SECURITY paragraph was not tightened in this branch when authority moved to `python/plan_review.py`. That is documentation drift, not a runtime broadening.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_6: [OUT_OF_SCOPE] Additional skill/reference files still mention retired script basenames
- **Reviewer(s)**: dyn-retired-path-sweep-output.txt
- **Severity**: latent
- **Concern**: `skills/design/references/design-outline.md:121`, `skills/design/references/brainstorm.md:5,158`, `skills/shared/voting-protocol.md:11,226,266`, and `skills/design/references/flags.md:67` still mention `plan-review-loop.sh`, `tally-plan-review.sh`, or `emit-plan.sh` by basename. They were not all on the plan’s explicit update list, but they remain operator-facing drift.
- **Suggested revisions (informational for voters; coder decides)**:


