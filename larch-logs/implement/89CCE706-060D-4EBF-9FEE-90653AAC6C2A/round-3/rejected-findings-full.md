### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: Static archetype slug source of truth is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Static archetype slugs are hardcoded in multiple places, so adding or renaming an archetype can make dispatch, coverage, and tests disagree about the required static panel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Scout dynamic-archetype tests do not enforce reserved slugs
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The scout prompt reserves historical static slugs, but the harness does not assert that dynamic scouts cannot emit those reserved slugs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: `launched-slots` is wired equal to `intended-slots`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Review-core always passes launched static slots equal to intended static slots, so missing emitted slots may not be counted through the threshold script’s never-launched path and rely only on coverage as a backstop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: Static manifest slot IDs are duplicated across vendors
- **Reviewer(s)**: dyn-waterfall-output.txt
- **Severity**: latent
- **Concern**: Cursor and Codex static rows share archetype slug values as `slot` and differ only by `tool`/`output`, so future consumers keying only on `slot` could misattribute drops or successes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-waterfall-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Static reviewer basename normalization is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Static output basename normalization is duplicated between threshold and review-core logic, risking divergent retry/phase suffix handling and inconsistent threshold versus coverage results.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: Public docs use ambiguous “per vendor” panel wording
- **Reviewer(s)**: dyn-topology-sync-output.txt
- **Severity**: latent
- **Concern**: Documentation and sync markers say “4 specialists per vendor (Cursor + Codex)” without consistently qualifying that rows are emitted per available vendor, which can be read as a fixed eight-row requirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-topology-sync-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_25: New topology row is not linked from consumer docs
- **Reviewer(s)**: dyn-topology-sync-output.txt
- **Severity**: nit
- **Concern**: The new `implement.review_and_fix.panel_hard` topology projection exists, but consumer docs repeat the panel phrase inline instead of linking to the generated topology anchor, weakening drift prevention.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-topology-sync-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_26: Diagram sync checks are not covered by self-test
- **Reviewer(s)**: dyn-topology-sync-output.txt
- **Severity**: nit
- **Concern**: Diagram phrase greps were added to the default docs-sync harness, but `--self-test` does not exercise those positive/negative diagram assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-topology-sync-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_27: Review runtime docs are not included in panel sync harness
- **Reviewer(s)**: dyn-topology-sync-output.txt
- **Severity**: nit
- **Concern**: `skills/review/SKILL.md` and `dispatch-panel.md` are runtime/authority surfaces for the review panel but are not included in the public-doc sync checks, so review-panel drift could escape CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-topology-sync-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_28

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_28: Docs-sync harness removed prior Step 5 anchors
- **Reviewer(s)**: dyn-topology-sync-output.txt
- **Severity**: nit
- **Concern**: The docs-sync harness no longer checks prior `5 rounds` and `--panel hard` anchors, so Step 5 round-cap and delegated-panel wording can drift unless the removal is explicitly documented as intentional.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-topology-sync-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Misleading `claude_output` variable covers Codex/Cursor files too
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: A loop variable named `claude_output` also processes external Codex/Cursor files, which could lead future maintainers to incorrectly narrow the pass to Claude-only outputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Dropped-static collection repeatedly rescans the manifest
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `collect_dropped_static_outputs` rescans the full manifest for each dropped row, which is avoidable work if slot counts grow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Dispatch status KVs and docs no longer reflect composite panel fate
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-waterfall-output.txt
- **Severity**: latent
- **Concern**: `DISPATCH_OK` / `STATIC_DISPATCH_OK` are no longer authoritative hard-stop signals, but dispatch output and documentation can still imply panel failure or success in ways that disagree with threshold plus coverage semantics. Operators and automation may misread partial static drops or degraded dynamic dispatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-waterfall-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

