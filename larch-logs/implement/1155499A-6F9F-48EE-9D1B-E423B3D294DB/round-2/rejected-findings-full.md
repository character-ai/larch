### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: `docs/configuration-and-permissions.md` vs issue #2683 wording on threshold semantics
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Docs describe leading-zero and base-10 coercion beyond the plan’s single `case` pattern; if the issue alone is treated as normative, docs and SKILL can drift from shipped semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Sync issue plan wording with the shipped env-var semantics or narrow docs to the original case rule.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_14: Branch adds a full `larch-logs/implement/…` tree unrelated to `/design` preview behavior (PR scope / history bloat)
- **Reviewer(s)**: dyn-skill-invocation-output.txt
- **Severity**: important
- **Concern**: The branch adds a full `/implement` run tree (`manifest.json`, tally, large `plan-goals-test.md`, etc.), bloating history and mixing session telemetry with the feature; risk of confusing curated vs incidental run logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-skill-invocation-output.txt: Remove these paths from the PR (or relocate only what `docs/run-logs.md` explicitly requires) so the change set is limited to `skills/design/*`, `docs/configuration-and-permissions.md`, and `CHANGELOG.md`.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_16: `plan-goals-test.md` fenced snippets vs `normalize_summary_threshold` / docs (leading-zero / base-10)
- **Reviewer(s)**: dyn-threshold-divergence-output.txt
- **Severity**: important
- **Concern**: Flushed artifact still shows older inline fenced Bash (simple `case` before `-gt`) that does not reject leading-zero all-digit values the way `emit-design-plan-preview.sh` does, so `0120`-style values can behave differently (e.g. octal interpretation in comparisons); prose in that file can mis-document canonical behavior vs `docs/configuration-and-permissions.md` and the script.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-threshold-divergence-output.txt: Update those fenced blocks (or replace them with “invoke `emit-design-plan-preview.sh` …”) so they match `normalize_summary_threshold` in `emit-design-plan-preview.sh`, or add a clear note that the snippet is historical and non-normative while the script is authoritative.

---


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_4: Adjacent Step 3 fences both `source` `current-design-env.sh` (redundant SKILL text)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Two adjacent Step 3 fences each source `current-design-env.sh`, adding noise; optional dedup with a one-line justification if the shell context is already shared.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_5: `CHANGELOG.md` taxonomy for the new `/design` bullet (`### Changed` vs `### Added`)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The new `/design` visibility line is filed under `### Changed`; reviewers note a possible preference for `### Added` or local convention—cosmetic only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Unquoted or fragile `cat` / `$DESIGN_TMPDIR` examples in docs / SKILL
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Gate C full-plan examples show `cat $DESIGN_TMPDIR/plan.txt`-style usage; a literal paste with spaces or glob characters in `DESIGN_TMPDIR` risks word-splitting or pathname expansion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Standardize on `cat -- "${DESIGN_TMPDIR}/plan.txt"` or Read-tool equivalent in both SKILL.md and approval-gates.md.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Gate C “Other” full-plan emission has no size bound (large `plan.txt` risk)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Documented full-plan emission for Gate C Other has no byte cap; very large `plan.txt` can degrade chat/logging or increase accidental disclosure if secrets were pasted into the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Document operator expectations and/or add optional byte-cap or pager-style guidance in a follow-up change.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Extremely long all-digit `LARCH_DESIGN_PLAN_SUMMARY_THRESHOLD` can exceed bash integer limits after digit-only normalization
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Rare env typo with an enormous digit-only string can exceed bash integer limits after normalization, producing hard failure instead of falling back to 120.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Clamp length or wrap arithmetic in a failure handler that resets to 120.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

