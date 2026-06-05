### FINDING_15: [OUT_OF_SCOPE] Scope-anchor result-env CR/LF hardening is positive
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: CR/LF rejection before `emit_kv` and staging under validated `$DESIGN_TMPDIR` are appropriate hardening.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_16: [OUT_OF_SCOPE] Scope-anchor prompt handling reflects a broader policy gap
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `SECURITY.md` already flags delimiter-based hardening gaps, and this branch extends similar patterns to scope anchors without adopting stronger controls.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_20: [OUT_OF_SCOPE] Non-binding feature context retains unstripped `larch:plan`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-scope-anchor-flow-output.txt
- **Severity**: latent
- **Concern**: `plan-review-feature-context.txt` is built from the original feature file and can retain stale embedded `larch:plan` text, which could confuse operators or future consumers even if current binding paths use the stripped anchor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-scope-anchor-flow-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_23: [OUT_OF_SCOPE] Assessor still uses raw feature file instead of staged anchor
- **Reviewer(s)**: dyn-scope-anchor-flow-output.txt, dyn-env-handoff-output.txt
- **Severity**: latent
- **Concern**: `assess-plan-round.sh` still resolves `--feature-file` from raw `feature-description.txt` / `IMPLEMENT_TMPDIR` fallback instead of the staged scope anchor, leaving a plan-review stage without the new issue-anchor behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-anchor-flow-output.txt: Address the concern above.
  - From dyn-env-handoff-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_24: [OUT_OF_SCOPE] Brainstorm docs overstate Step 3 binding usage
- **Reviewer(s)**: dyn-scope-anchor-flow-output.txt
- **Severity**: latent
- **Concern**: `brainstorm.md` still describes Step 3 as downstream reader of merged plan-review feature context, while current binding scope comes from the staged anchor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-anchor-flow-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_25: [OUT_OF_SCOPE] Marker-aware handling applies to OOS blocks despite contract limiting it to FINDING blocks
- **Reviewer(s)**: dyn-scope-marker-output.txt, dyn-plan-aggregation-output.txt
- **Severity**: important
- **Concern**: The canonical detector and dedup path can treat `OOS_*` blocks with `[SCOPE-REDUCTION]` as marker-aware, although the plan says tagged OOS blocks get no special handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-marker-output.txt: Restrict `check-scope-reduction-marker.sh` candidates to `FINDING_*` headings (and FINDING-shaped Concern/`what` lines), or skip `is_tagged()` for the OOS dedup pass so only FINDING blocks participate in marker-aware merging.
  - From dyn-plan-aggregation-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_27: [OUT_OF_SCOPE] Live inline emitter appears aligned; coverage is the main gap
- **Reviewer(s)**: dyn-scope-marker-output.txt
- **Severity**: nit
- **Concern**: The live `/design` inline emitter places `[SCOPE-REDUCTION]` where the detector expects it; the noted issue is missing CI coverage rather than a proven runtime mismatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-marker-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_33: [OUT_OF_SCOPE] MainAgent re-tally preservation is prose-only
- **Reviewer(s)**: dyn-env-handoff-output.txt
- **Severity**: latent
- **Concern**: `SKILL.md` says to preserve `SCOPE_ANCHOR_FILE` during MainAgent re-tally, but `tally-plan-review.sh` does not emit it, leaving preservation dependent on orchestrator prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-env-handoff-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_34: [OUT_OF_SCOPE] Revise had pre-existing raw `<plan>` / `<findings>` inline blocks
- **Reviewer(s)**: dyn-prompt-boundary-output.txt
- **Severity**: latent
- **Concern**: Broader revise prompt delimiter/redaction gaps predate this branch for `<plan>` and `<findings>`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-boundary-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_35: [OUT_OF_SCOPE] Scout path-based routing is relatively less delimiter-prone
- **Reviewer(s)**: dyn-prompt-boundary-output.txt
- **Severity**: nit
- **Concern**: Scout plan review still routes descriptions through staged file paths rather than full inline embedding, reducing delimiter-breakout exposure compared with reviewer / voter inline paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-boundary-output.txt: Address the concern above.

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_6: [OUT_OF_SCOPE] Marker detector duplicates stdin and file Python paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-scope-marker-output.txt
- **Severity**: latent
- **Concern**: `check-scope-reduction-marker.sh` duplicates detector logic for `--file` and stdin, creating normalization drift risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From dyn-scope-marker-output.txt: Consider extracting one shared module.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_7: [OUT_OF_SCOPE] `is_scope_reduction_block` API is misleading / mostly test-only
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, dyn-scope-marker-output.txt
- **Severity**: latent
- **Concern**: `is_scope_reduction_block` documents inline block input but passes the argument as `--file`, and production tally does not use it, making the wrapper easy to misuse or misleading.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-scope-marker-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

