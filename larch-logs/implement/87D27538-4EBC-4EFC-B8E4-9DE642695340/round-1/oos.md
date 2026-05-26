### FINDING_10: [OUT_OF_SCOPE] **Latent** `risk-integration` [`scripts/lint-fix-loop.sh:366-368`](scripts/lint-fix-loop.sh) — If a coder makes a valid commit and also leaves an uncommitted forbidden-path edit, `post_dispatch_forbidden_revert` fails with `forbidden-path-violation` while the good commit remains on HEAD unpushed; `ship-pr.sh` maps that to `dispatch-failed`, not the old `10-head-changed` stall. This is plan-intended fail-closed behavior, but it can still leave a good fix committed locally without push. **Suggested fix:** Only if product wants push-after-revert: emit `applied` after reverting residual working-tree forbidden edits when the commit-content check already passed (document the relaxed security tradeoff).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 2. **Latent** `risk-integration` [`scripts/lint-fix-loop.sh:366-368`](scripts/lint-fix-loop.sh) — If a coder makes a valid commit and also leaves an uncommitted forbidden-path edit, `post_dispatch_forbidden_revert` fails with `forbidden-path-violation` while the good commit remains on HEAD unpushed; `ship-pr.sh` maps that to `dispatch-failed`, not the old `10-head-changed` stall. This is plan-intended fail-closed behavior, but it can still leave a good fix committed locally without push. **Suggested fix:** Only if product wants push-after-revert: emit `applied` after reverting residual working-tree forbidden edits when the commit-content check already passed (document the relaxed security tradeoff).
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_15: [OUT_OF_SCOPE] risk-integration: SECURITY.md:133
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Unrelated ADOPTED sentinel documentation from #2878 in the same diff. No direct impact on #2909 test obligations. Split or note in PR description; no test action required for #2909.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_16: [OUT_OF_SCOPE] correctness: scripts/lint-fix-loop.sh:366-369
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Working-tree forbidden violation after accepted coder commit does not reset HEAD. Coder commit could remain on branch while helper reports forbidden-path-violation; parent may take dispatch-failed path. Optional follow-up test/fix if product wants hard reset on that failure shape.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_18: [OUT_OF_SCOPE] security: scripts/lint-fix-loop.sh:147-148,173-174
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Prefix forbidden-path matching allows sibling directory names (submod vs submod-evil). Pre-existing semantics shared by post_dispatch_forbidden_revert; not introduced by this branch. Harden prefix matching in a follow-up (e.g. require trailing slash boundary).
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_25: [OUT_OF_SCOPE] architecture: scripts/ship-pr.sh:1600-1603
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] _stage_and_push_ci_fixes runs full relevant-checks lint-fix after per-job success. Extra external dispatches and failure modes after shard-local fix; pre-existing orchestration. Out of scope for #2909; tune separately if latency/recursion is a concern.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_26: [OUT_OF_SCOPE] correctness: scripts/lint-fix-loop.sh:313-317
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Pre-dispatch forbidden_paths_file not refreshed after coder adds new submodule entries. New submodule path in commit may evade list until CI relevant-checks fails post-push. Pre-existing gap acknowledged in plan.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_27: [OUT_OF_SCOPE] security: SECURITY.md:133
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] ADOPTED sentinel validation text is from another merged commit on this branch. Not part of e59c905d feature diff. Review under #2936, not #2909.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_7: [OUT_OF_SCOPE] code-quality: SECURITY.md:133
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] ADOPTED validation paragraph is from #2878 not #2909. Unrelated security doc change rides the same PR diff. Split or note in PR description; no change required for #2909 logic.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_8: [OUT_OF_SCOPE] architecture: scripts/lint-fix-loop.sh:393-408
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Dirty baseline with unchanged HEAD can emit applied without commit SHA (pre-existing). Unrelated dirty-tree scenarios may still confuse operators; not regressed by this branch. Track separately if desired; out of scope for #2909.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_9: [OUT_OF_SCOPE] **Latent** `correctness` [`scripts/test-lint-fix-loop.sh`](scripts/test-lint-fix-loop.sh) — The plan and docs call out history rewrites (`commit --amend`, rebase) as fail-closed via `merge-base --is-ancestor`, but there is no dedicated regression case (unlike detached-HEAD, branch-switch, and dirty-baseline). **Suggested fix:** Add a wrapper that amends or rebases the tip commit and assert `FAILURE_REASON=head-changed-after-dispatch`.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **Latent** `correctness` [`scripts/test-lint-fix-loop.sh`](scripts/test-lint-fix-loop.sh) — The plan and docs call out history rewrites (`commit --amend`, rebase) as fail-closed via `merge-base --is-ancestor`, but there is no dedicated regression case (unlike detached-HEAD, branch-switch, and dirty-baseline). **Suggested fix:** Add a wrapper that amends or rebases the tip commit and assert `FAILURE_REASON=head-changed-after-dispatch`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

