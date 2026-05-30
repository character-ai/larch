### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: Duplicate poll-counter logic in task-output vs generic Read paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `handle_task_output_poll` and `handle_generic_read_poll` duplicate window/counter/read/write/emit logic; one path can get a skew or threshold fix and the other silently diverges.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract a shared bump_poll_counter helper parameterized by threshold and window


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Harness asserts JSON presence, not reminder prose
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Task-output tests assert `additionalContext` presence only, not reminder text; reminder prose could be emptied or wrong while JSON still appears once.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Pin Task-output poll detected or <task-notification> on representative Bash and slow-Read cases.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: Bash multiline/compound uses first matching `tasks/…output` segment
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Parsing always takes the first matching `tasks/<id>.output` segment; a script mentioning task A then polling task B may track A and never fire for B-only polling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Prefer rightmost match or track all task ids per command.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: Missing `session_id`/`conversation_id` collapses to shared `nosession` bucket
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-state-file-isolation-output.txt
- **Severity**: latent
- **Concern**: When both IDs are absent, all callers hash constant `nosession` per `cwd`+`task_id`; concurrent or sequential sessions can share counters (incorrect early warnings or missed second-read reminder).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document payload requirement or add stronger fallback identity; test missing session fields.
  - From dyn-state-file-isolation-output.txt: Prefer a per-process discriminator when IDs are missing (e.g. `PPID`, a hook-provided `transcript_id` if available, or a random bucket created once per hook parent) instead of a global `nosession` literal; document the fallback; add a harness case that two payloads with no `session_id`/`conversation_id` do not share counters unless that coupling is intentional.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: Non-atomic read-modify-write on task-output state TSV
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-state-file-isolation-output.txt
- **Severity**: latent
- **Concern**: Overlapping hook invocations can both read the same `count` and write `count+1`, losing an increment and delaying threshold=2 behavior (more impactful with lower threshold on primary #3175 path).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Use flock or append-only counting if concurrent delivery is possible.
  - From dyn-state-file-isolation-output.txt: For a warn-only hook, document the best-effort semantics; if stronger guarantees are needed, use an atomic update (`flock` around read/write, or append-only event log) without changing the fail-open exit behavior.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Bash branch normalizes every command before poll prefilter
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The Bash branch always normalizes and segments the full command before rejecting non-poll commands; high-volume `/implement` sessions pay `sed`+loop on every Bash PostToolUse. Prefilter commands lacking `tasks/*.output` before `bash_normalize_cmd`.
- **Suggested revisions (informational for voters; coder decides)**:
  - (none — source provided only generic “Address the concern above.”)


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: `||` chains not split; guard pattern can false-positive
- **Reviewer(s)**: dyn-bash-parsing-accuracy-output.txt
- **Severity**: latent
- **Concern**: `bash_line_task_output_poll_token` splits on `;` and `&&` but not `||`. `test -f "$LOCK" || cat …/tasks/<id>.output` stays one segment; when the test succeeds Bash never runs `cat`, but classifier still advances counter (warn-only false positive).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parsing-accuracy-output.txt: extend splitting to treat `||` like `&&` (iterate segments and only treat a segment as a poll-read when it both matches read-verb + task-output path and is not provably dead code on the RHS of `||` when a preceding segment is a simple success test), or document `||` guards as unsupported and accept the false-positive rate for a warn-only hook.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: `&&` chains lack short-circuit model (dead RHS still counted)
- **Reviewer(s)**: dyn-bash-parsing-accuracy-output.txt
- **Severity**: latent
- **Concern**: After `&&` splitting, each RHS segment is classified independently; `false && cat …/tasks/<id>.output` still counts `cat` though Bash will not execute it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parsing-accuracy-output.txt: when walking `&&`-split segments left-to-right, skip segments after an earlier segment that is a known false literal (`false`, `:`) or add a conservative “only count the rightmost segment that both has a read verb and task-output token” rule for `&&` chains.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_23: `bash_has_read_verb` can match `cat` inside identifiers like `cat_output`
- **Reviewer(s)**: dyn-bash-parsing-accuracy-output.txt
- **Severity**: nit
- **Concern**: Read-verb regex allows `cat` with following `_` boundary; combined with `tasks/…output` substring, hook can warn when no `cat`/`tail`/… utility ran.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parsing-accuracy-output.txt: tighten the pattern to require `cat` as a standalone token (e.g. `\<cat\>` with grep `-w` for the simple verbs, or require whitespace/`$` after `cat` and disallow immediate `_`).

---

**Aggregation notes (not part of machine output):**

- **Subsumed (not emitted):** `cursor-specialist-security-output.txt` FINDING_13–17 are positive trust-boundary attestations, not defects. Informational OOS from `dyn-bash-parsing-accuracy-output.txt` (32–35) and `dyn-state-file-isolation-output.txt` (39–43) record intentional/acceptable behavior with no requested change.
- **Merged:** duplicate prune concern (structure 4 + edge 25 + security OOS 20); quote splitting (structure 3 + dyn 30); threshold-only-on-2 (correctness 8 + edge 21); `nosession` bleed (edge 22 + dyn 36); non-atomic RMW (edge 24 + dyn 38).

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Segment splitter is not quote-aware (`;` / `&&`)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-bash-parsing-accuracy-output.txt
- **Severity**: nit
- **Concern**: Splitting on `;` and `&&` without quote awareness can fracture quoted paths (e.g. semicolon inside quotes), miss `cat …/tasks/id.output`, or mis-classify fragments—false negatives for polls and brittle Bash classification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Document limitation or add quote-aware splitting
  - From dyn-bash-parsing-accuracy-output.txt: either strip or mask quoted spans before `;`/`&&` splitting, or rely on the Read branch for quoted paths and document that Bash classification is best-effort for unquoted paths only.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Per-task `state-taskout-*` files are never pruned
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Per-task state files under `${TMPDIR}/larch-read-poll/` are never deleted; long sessions accumulate stale `state-taskout-*` files (logical 600s expiry only, not filesystem cleanup).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Prune by mtime on hook entry or consolidate to one TSV keyed by normalized token
  - From cursor-specialist-edge-cases-output.txt: Prune stale state files on window reset or hook init.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Repetitive, non-table-driven test harness
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Large repetitive harness for a warn-only hook; classifier tweaks require editing many near-duplicate blocks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Use table-driven Bash poll cases for #3195 shapes


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Task-output reminder fires only when `count == 2`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Reminder triggers only when count equals 2, not on later reads in the same 600s window. After turn 2, many further per-turn `cat …/tasks/id.output` reads produce no further reminders until window reset (#3175-style spend continues).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Fire on count -ge threshold (optionally throttle) if repeated nudges are required beyond the first.
  - From cursor-specialist-edge-cases-output.txt: Emit on count >= threshold with a repeat/escalation policy; add harness asserting poll 3+ still warns.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

