### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: `plan_block_present` logic untested beyond marker strings
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `plan_block_present` in `design-route.sh` is untested beyond `MARK_START`/`MARK_END` presence; malformed bodies could mis-route already-planned vs proceed; `test-plan-block.sh` does not cover the driver copy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: No hermetic Step 0b orchestrator-fence harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No hermetic Step 0b orchestrator-fence harness (unlike `test-step3-orchestrator-fence.sh`); fence regressions (file-only WARN/ERROR, exit guards) can ship without offline reproduction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Structure checks no longer pin driver predicate ordering
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Checks 20/24 no longer pin driver-internal title/reentry/verdict ordering; predicate reorder inside `design-route.sh` (e.g. archival before lifecycle) would not fail structure tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Tier/jq-warning pins weakened to SKILL OR driver
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Tier/jq-warning pins weakened to SKILL OR driver; both copies could drift together with CI still green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: Route/init drivers write result env without tmpdir validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `design-route.sh` writes `.design-route-result.env` without `larch_design_tmpdir_validate` on paths that skip `design-pause-load.sh`. A buggy `--design-tmpdir` outside `~/.cache/larch/sessions`, `$TMPDIR`, or `/tmp` could write route result files to an unintended writable directory before any validating child runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: Init bash fence not gated on `ROUTE=proceed`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Init bash fence in `skills/design/SKILL.md` is not gated on `ROUTE=proceed` (prose-only guard). Orchestrator can run `design-init-runparams` on clarify/already-planned, renaming issue and writing run-params on the wrong branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

---

**Merge notes (brief):** 27 raw slots → **19** aggregated findings. Merged groups: duplicate WARN/ERROR (1/10/23/26), jq/`printf` quiet contract (3/9/24), structure-test abort greps (11/25), init exit-1/env-refresh contract (18/19), pause-load masking (20/27). Kept separate: re-entry WARN breadcrumb (5) vs KV parse bug (8); all `[OUT_OF_SCOPE]` items (6/7) retain the tag. No `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` line (non-empty merge).

Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Duplicated scalar/repo validators across design drivers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `validate_plain_scalar` and `validate_repo` are duplicated in `design-route.sh` and `design-init-runparams.sh`; future `--repo` rule changes require two edits and risk drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Duplicated large Step 3–shaped handoff fences in SKILL.md
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Dual large Step 3–shaped handoff fences (~120 lines) in `skills/design/SKILL.md` (Step 3 vs Step 0b route/init); Step 3 tweaks may not mirror Step 0b fences.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Re-entry helper exit 2 stdout not surfaced as WARN
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Re-entry helper exit 2 stdout is no longer surfaced as WARN in `design-route.sh`. Unset `HOME` or invalid-input paths can continue design without the old Step 2.6 `MARKER_HIT=false REASON=invalid-input` breadcrumb.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

