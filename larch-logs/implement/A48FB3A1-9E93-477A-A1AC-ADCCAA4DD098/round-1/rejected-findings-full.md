### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: `--paths-file` trusts arbitrary path lines (collector)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: In `scripts/collect-agent-results.sh` (~228–237), new `--paths-file` ingestion accepts arbitrary path lines without tmpdir prefix checks before wait/read paths; a swapped or attacker-controlled paths-file can batch-steer collector waits and reads toward unintended local paths with less argv friction. Add optional prefix allowlisting or fd-snapshot read after open; document in `SECURITY.md` if the posture stays trust-based only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_18: `awk -F=` parsing of `VOTER_PATHS_FILE` breaks on paths containing `=`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: In `scripts/test-dispatch-code-voters.sh` (cited ~6418–6423), `awk -F=` parsing of `VOTER_PATHS_FILE` breaks if a path contains `=`; rare paths truncate the parsed filename and false-negative `require_voter_paths_file_nonempty`. Use `index`/`substr` KV split or another delimiter-safe parse.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Duplicate `awk` extraction of `VOTER_PATHS_FILE` in code-voters harness
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: In `scripts/test-dispatch-code-voters.sh` (~39–250), `VOTER_PATHS_FILE` is extracted twice after `require_voter_paths_file_nonempty`, adding churn if the KV shape changes and extra noise. Return the path from the helper or write it to a caller-supplied variable to avoid double parsing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

