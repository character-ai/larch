### OOS_1: [OUT_OF_SCOPE] Portable `sed` read-verb detection uses `\b` in grep ERE
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `sed -n` detection uses `\b`; portable `sed`-as-read-verb behavior may vary by platform `grep`; does not affect primary `cat` path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Replace \b with explicit character-class anchors like cat/tail matchers


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] Task-output state files accumulate without deletion
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Pre-existing generic-state pattern; long runs leave stale `state-taskout-*` files under `larch-read-poll` until tmp cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Optional periodic prune or reuse single keyed TSV per cwd
  - From cursor-specialist-edge-cases-output.txt: Unlink on window expiry or cap files per session_hash+cwd_hash.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_3: [OUT_OF_SCOPE] `jq` absence disables all hook warnings
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Pre-existing: no `jq` on PATH makes Read|Bash anti-poll a no-op for every session.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document in installation prerequisites; already noted for other hooks.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### OOS_4: [OUT_OF_SCOPE] PostToolUse concurrency documented for audit log only
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: General platform concern that parallel hooks can interleave; state-file hooks inherit the class; not introduced solely by this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_5: [OUT_OF_SCOPE] `session_id` hashing for task-output state was not in plan
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Round-1 addition; if hook events lack `session_id`, unrelated sessions share `nosession` counters. Out of scope for #3195 plan; verify production payloads if needed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_6: [OUT_OF_SCOPE] Affirmation — token/verb short-circuit chain is correct
- **Reviewer(s)**: dyn-bash-classification-output.txt
- **Severity**: nit
- **Concern**: `extract_task_output_token` / `bash_line_is_task_output_poll` return chain correctly short-circuits on missing token before verb checks; exit status follows `bash_has_read_verb`. No change requested.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_7: [OUT_OF_SCOPE] Affirmation — `sed -n` per-line branch is reasonable
- **Reviewer(s)**: dyn-bash-classification-output.txt
- **Severity**: nit
- **Concern**: `[^|;&]*` before `\-n\b|--quiet` avoids false read-verb on later pipeline segments; harness `sed -i.bak …; grep -rn` decoy stays silent. No change requested.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_8: [OUT_OF_SCOPE] Affirmation — task ID charset matches transcripts
- **Reviewer(s)**: dyn-bash-classification-output.txt
- **Severity**: nit
- **Concern**: Real task IDs match `[A-Za-z0-9._-]+`; classifier limit is consistent with plan and #3175 shapes. No change requested.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_9: [OUT_OF_SCOPE] Affirmation — incident logs mostly unquoted same-line paths; gaps documented
- **Reviewer(s)**: dyn-bash-classification-output.txt
- **Severity**: nit
- **Concern**: #3175-style Bash bodies in `larch-logs` overwhelmingly use unquoted absolute `cat`/`tail` on same line; quoted/variable-only paths remain documented warn-only gaps in `hook-anti-read-poll.md` and plan “Hook false negatives”. No change requested beyond in-scope quoted-path fixes.
- **Suggested revisions (informational for voters; coder decides)**:

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

