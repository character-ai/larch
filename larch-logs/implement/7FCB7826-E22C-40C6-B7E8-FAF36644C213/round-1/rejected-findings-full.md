### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: `SESSION_ID` validated only for newline/CR in driver
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `design-publish.sh:20-25` validates `SESSION_ID` only for newline/CR, not log slug rules. Malformed `--session-id` could reach helpers before `design-log-publish` rejects it (defense-in-depth only).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Validate non-empty SESSION_ID with larch_log_slug_is_valid (or shared helper) before publish/rename.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Document quiet-driver file-first parse; pin fence must parse on rc=1
- **Reviewer(s)**: dyn-driver-exit-contract-output.txt
- **Severity**: nit
- **Concern**: The rc ∈ {0,1} parse path is structurally sound (file-first parse authoritative when quiet mode leaves `_publish_out` empty), but maintainers need explicit documentation and a structure pin that the fence must not `exit` before parsing when `_publish_rc` is 1.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-driver-exit-contract-output.txt: No change required to the parse loop itself; document in `design-publish.md` / Step 5c prose that file-first parse is authoritative when quiet mode leaves `_publish_out` empty, and add a structure pin that the fence must not `exit` before parsing when `_publish_rc` is 1.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: `FINAL_SUMMARY_PATH` emit not confined to `DESIGN_TMPDIR`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The orchestrator verbatim-emits `FINAL_SUMMARY_PATH` from `.design-publish-result.env` without confining reads to `DESIGN_TMPDIR`. A same-UID attacker could race `FINAL_SUMMARY_PATH=/path/to/secret` before parse; Step 5c item 5 could cat and emit it to chat.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: After parse require FINAL_SUMMARY_PATH empty or canonically under DESIGN_TMPDIR; refuse symlink emit targets.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

