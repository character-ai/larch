### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: WARN/display emissions are not consistently neutralized
- **Reviewer(s)**: dyn-trailer-spoofing-output.txt
- **Severity**: important
- **Concern**: `_emit_warn_lines` can emit WARN text on FD 3 without the same neutralization applied to WORSE/qualification lines, allowing spoof-like machine lines to appear near validated trailer output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-trailer-spoofing-output.txt: Run every user-visible `emit` through `_neutralize_assessor_display_line` (or a single `_emit_display` helper), including WARN, banner, and paused note.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Classification resolver parses merged stdout and stderr
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `assess-plan-round.sh` resolves classification via `2>&1 | tail -n 1`, so extra stdout/stderr lines could misclassify `SIMPLE` versus `HARD`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_7: Assessor summary rendering may expand model-written shell syntax
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `_emit_worse_display` reads `QUALIFICATIONS_SUMMARY` from a model-written sidecar and renders it with a here-string pattern the reviewer says can expand embedded shell syntax, allowing command execution during WORSE-majority display.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_8: rc=10 trailer parsing uses an unsafe heredoc shape
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-bash-fence-output.txt, dyn-trailer-spoofing-output.txt
- **Severity**: important
- **Concern**: The production `SKILL.md` rc=10 trailer loop feeds `_assessor_trailers` through an unquoted heredoc, diverging from the safer harness mirror and risking expansion or delimiter-injection behavior if trailer/display bytes become attacker-controlled.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-bash-fence-output.txt: Replace the heredoc with the same quoted form as the harness, e.g. `while IFS= read -r _assessor_trailer_line || [ -n "$_assessor_trailer_line" ]; do ... done <<<"$_assessor_trailers"`, or pipe from `printf '%s\n' "$_assessor_trailers"` without expansion.
  - From dyn-trailer-spoofing-output.txt: Replace the heredoc with `done <<<"$_assessor_trailers"` (same as the test handoff).


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

