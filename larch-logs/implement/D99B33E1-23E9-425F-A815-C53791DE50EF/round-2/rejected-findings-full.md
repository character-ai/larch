### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Non-atomic read-modify-write on task-output state files
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Parallel PostToolUse can lose increments; threshold-2 reminder may not fire during fast per-turn polling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Use flock or atomic append-per-event counting; optional parallel harness.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Harness omits multiline incident-shaped Bash fixtures
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: No archived multiline echo-then-cat layout from implement transcripts; regression could re-break that shape without CI failure while single-line cases pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add multiline fixture mirroring larch-logs implement transcripts.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: System-reminder fires only when count equals 2
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: After turn 2, further per-turn polls in the same 600s window get no additional system-reminder because the hook only emits when count equals 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Fire on count ge threshold with cooldown, or document one-shot nudge per window in hook-anti-read-poll.md


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: 600s window may warn on legitimate second post-completion read
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Orchestrator may read task output once after notification and again within 10 minutes for debugging; hook still emits reminder on the second read.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document as expected warn-only noise or raise threshold / add reset signal.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Duplicated windowed counter logic in two handlers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `handle_task_output_poll` and `handle_generic_read_poll` duplicate bump/window logic; threshold or window tweaks in one handler may diverge warn behavior between task-output and generic Read paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract a shared bump-and-maybe-emit helper; keep only classifiers in each handler


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: No cheap prefilter before full Bash command parsing
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Every Bash tool use pays quote-strip/line-grep cost during heavy `/implement` runs even when the command cannot reference task output paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add early exit when command lacks tasks/ or .output before bash_is_task_output_poll


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

