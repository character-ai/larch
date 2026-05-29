### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: No automated CI guard for live-surface `--simple` completeness
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Plan acceptance requires zero live `--simple` mentions, but enforcement is manual grep only. `plugin.json` regressed while `make lint` and named harnesses still pass. Retired `--simple` rejection in `SKILL.md` is prose-only with no mechanical guard—future edits or misbehaving agents can reintroduce `--simple` without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Driver test lacks negative guard for removed `--simple` table row
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/test-design-driver.sh` removed the `--simple` row assertion without an absent check. Re-adding a `| \`--simple\` |` table row would not fail the driver test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: `flags.md` tier section untested by structure harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The tier-section rewrite in `skills/design/references/flags.md` has no structure-test needles; `flags.md` can drift from the SKILL default / `--hard`-only contract without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

