### FINDING_16: [OUT_OF_SCOPE] Ship-state writer/parser quoting mismatch can mis-hydrate context
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-shipstate-output.txt
- **Severity**: latent
- **Concern**: `ship-pr-state.sh` is written as raw unquoted `KEY=value` but later read via shlex-aware finalize parsing in some paths, so special characters can round-trip inconsistently and mis-hydrate fields.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-shipstate-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_19: [OUT_OF_SCOPE] Optional structure pins for Python handoff/stall docs were not added
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-selector-output.txt
- **Severity**: latent
- **Concern**: Static guard coverage does not pin some optional plan prose around stall-recovery layering, conflict-resolution Python handoff, Phantom registry wording, or Steps 10/12 driver-neutral language.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt, dyn-selector-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_20: [OUT_OF_SCOPE] Steps 10/12 prose remains bash-specific
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-selector-output.txt
- **Severity**: important
- **Concern**: Steps 10/12 still describe `ship-pr.sh`, `PHASE=done`, and bash continuation semantics even though Python JSON routing is now default.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-selector-output.txt: Reword this block to “active Step 8+ driver” throughout: Python path continues from JSON `outcome` / exit code and scoped `ship-pr-state.sh` keys; bash opt-in keeps the existing `ship-pr.sh` / `PHASE=done` wording. Add a structure-test pin for the updated prose.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_21: [OUT_OF_SCOPE] Duplicate postmerge `phase=done` write
- **Reviewer(s)**: dyn-shipstate-output.txt
- **Severity**: nit
- **Concern**: `python/ship.py` duplicates the postmerge `phase=done` write already done inside `run_postmerge_phase`; reviewer judged it redundant but not functionally harmful.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shipstate-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_22: [OUT_OF_SCOPE] Local Python version prevented pytest execution
- **Reviewer(s)**: dyn-shipstate-output.txt
- **Severity**: nit
- **Concern**: One reviewer could not run `python/test_ship.py` locally because the shell had Python 3.11 while `ship.py` requires 3.12; CI remains authoritative.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shipstate-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_26: [OUT_OF_SCOPE] Python-default selector and restore wiring are aligned
- **Reviewer(s)**: dyn-selector-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that the unified invoke fence, Python selector, Step 18 restore gate, stall classifier layering, and conflict-resolution Python re-invoke qualifiers align with the flip intent.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_27: [OUT_OF_SCOPE] Security docs acknowledge accepted Python-default soak exposure
- **Reviewer(s)**: dyn-selector-output.txt, dyn-votesemantics-output.txt, dyn-promptsafe-output.txt
- **Severity**: latent
- **Concern**: Multiple reviewers noted the unresolved Python soak blockers are documented/accepted operational risk rather than an accidental defect in some reviewed surfaces.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_28: [OUT_OF_SCOPE] Minor OOS wording drift in shared subskill docs
- **Reviewer(s)**: dyn-selector-output.txt
- **Severity**: nit
- **Concern**: `skills/shared/subskill-invocation.md` correctly splits bash vs JSON routing, but still says “inside the ship-pr orchestration” for OOS.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-selector-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_31: [OUT_OF_SCOPE] Stall classifier exit-code docs drift from implementation
- **Reviewer(s)**: dyn-bash32-output.txt
- **Severity**: latent
- **Concern**: `stall-recovery-report.md` exit-code table was not updated for new validation paths that can produce exit 3.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_32: [OUT_OF_SCOPE] Minor symlink-canonicalization inconsistency
- **Reviewer(s)**: dyn-bash32-output.txt
- **Severity**: nit
- **Concern**: `plan-block-strip-body.sh` uses `pwd` instead of `pwd -P`, unlike neighboring scripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_33: [OUT_OF_SCOPE] Redundant PR-number validation
- **Reviewer(s)**: dyn-bash32-output.txt
- **Severity**: nit
- **Concern**: `compute-pr-line-counts.sh` duplicates numeric PR validation with slightly different reason tokens.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_35: [OUT_OF_SCOPE] Vote-tally helper has no production caller
- **Reviewer(s)**: dyn-votesemantics-output.txt
- **Severity**: nit
- **Concern**: Reviewer notes `scripts/lib-vote-tally.sh:is_scope_reduction_block()` is test-pinned and not a broken production tally path.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_36: [OUT_OF_SCOPE] Scope-anchor wiring is otherwise internally consistent
- **Reviewer(s)**: dyn-votesemantics-output.txt
- **Severity**: nit
- **Concern**: Reviewer found plan-review scope-anchor wiring, scout dispatch, aggregation withhold/append behavior, and brainstorm boundaries consistent aside from the marker/dedup issues above.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_37: [OUT_OF_SCOPE] Four-layer stall classifier matches intended Python-default finalize gating
- **Reviewer(s)**: dyn-votesemantics-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that classify implements in-memory → `ship-pr-state.sh` → `finalize-state.sh` → `session-env.sh` resolution as intended.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_39: [OUT_OF_SCOPE] Positive prompt-safety coverage for delimiter breakout
- **Reviewer(s)**: dyn-promptsafe-output.txt
- **Severity**: nit
- **Concern**: Reviewer noted solid delimiter-breakout tests and consistent untrusted-data framing for several scope-anchor paths.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_40: [OUT_OF_SCOPE] Positive Python state-write hardening
- **Reviewer(s)**: dyn-promptsafe-output.txt
- **Severity**: nit
- **Concern**: Reviewer noted new Python state-write symlink/temp-file hardening and newline validation that closes state-file spoofing classes.
- **Suggested revisions (informational for voters; coder decides)**:

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_8: [OUT_OF_SCOPE] Branch bundles unrelated design/review changes with the ship flip
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The branch includes #3548 design/review changes and larch-log/doc/harness churn beyond the ship-driver flip plan, making review and rollback scope harder to reason about.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

