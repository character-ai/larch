### FINDING_1: Duplicate poll-counter logic in task-output vs generic Read paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `handle_task_output_poll` and `handle_generic_read_poll` duplicate window/counter/read/write/emit logic; one path can get a skew or threshold fix and the other silently diverges.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract a shared bump_poll_counter helper parameterized by threshold and window

### FINDING_2: Bash branch normalizes every command before poll prefilter
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The Bash branch always normalizes and segments the full command before rejecting non-poll commands; high-volume `/implement` sessions pay `sed`+loop on every Bash PostToolUse. Prefilter commands lacking `tasks/*.output` before `bash_normalize_cmd`.
- **Suggested revisions (informational for voters; coder decides)**:
  - (none — source provided only generic “Address the concern above.”)

### FINDING_3: Segment splitter is not quote-aware (`;` / `&&`)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-bash-parsing-accuracy-output.txt
- **Severity**: nit
- **Concern**: Splitting on `;` and `&&` without quote awareness can fracture quoted paths (e.g. semicolon inside quotes), miss `cat …/tasks/id.output`, or mis-classify fragments—false negatives for polls and brittle Bash classification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Document limitation or add quote-aware splitting
  - From dyn-bash-parsing-accuracy-output.txt: either strip or mask quoted spans before `;`/`&&` splitting, or rely on the Read branch for quoted paths and document that Bash classification is best-effort for unquoted paths only.

### FINDING_4: Per-task `state-taskout-*` files are never pruned
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Per-task state files under `${TMPDIR}/larch-read-poll/` are never deleted; long sessions accumulate stale `state-taskout-*` files (logical 600s expiry only, not filesystem cleanup).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Prune by mtime on hook entry or consolidate to one TSV keyed by normalized token
  - From cursor-specialist-edge-cases-output.txt: Prune stale state files on window reset or hook init.

### FINDING_5: Repetitive, non-table-driven test harness
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Large repetitive harness for a warn-only hook; classifier tweaks require editing many near-duplicate blocks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Use table-driven Bash poll cases for #3195 shapes

### FINDING_6: [OUT_OF_SCOPE] Pre-existing generic Read polling edge cases
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Generic Read offset string compare and unlocked TSV RMW predate this branch; unchanged generic-read edge cases not introduced by #3195. Fix only if hardening generic Read polling is in scope separately.
- **Suggested revisions (informational for voters; coder decides)**:
  - (none — source provided only generic “Address the concern above.”)

### FINDING_7: `echo`-only skip hides `cat` on same `||` segment
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `bash_segment_is_echo_only` uses `echo*`/`printf*` prefix match on whole `;`/`&&` segments, skipping any trailing read verb in the same segment. Plan-shaped `echo "waiting" || cat …/tasks/id.output` can exit 0 twice with no reminder while embedded `cat` is never classified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Restrict echo-only skip to segments with no read verb/path (or split on `||` before the echo check); add harness case for echo || cat task-output polling.

### FINDING_8: Task-output reminder fires only when `count == 2`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Reminder triggers only when count equals 2, not on later reads in the same 600s window. After turn 2, many further per-turn `cat …/tasks/id.output` reads produce no further reminders until window reset (#3175-style spend continues).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Fire on count -ge threshold (optionally throttle) if repeated nudges are required beyond the first.
  - From cursor-specialist-edge-cases-output.txt: Emit on count >= threshold with a repeat/escalation policy; add harness asserting poll 3+ still warns.

### FINDING_9: [OUT_OF_SCOPE] `tasks/…\.output` regex may match `.output.bak` paths
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `grep -oE tasks/…\.output` can match a prefix inside `tasks/foo.output.bak`; `cat …/tasks/foo.output.bak` could be counted as task-output polling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Tighten token extraction (e.g. require `.output` not followed by alnum) if backup paths are plausible.

### FINDING_10: Harness covers only `cat` for Bash task-output polls
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Harness exercises only `cat` while the hook implements `tail`/`head`/`less`/`more`/`sed -n`; a regex edit removing non-`cat` verbs could ship green while `tail …/tasks/id.output` evades warnings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add minimal two-call Bash cases for at least tail and sed -n on a tasks/<id>.output path.

### FINDING_11: Harness omits `|| echo` (and similar) after `.output` path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Plan-listed `|| echo` suffix after task `.output` path is untested; only pipe/redirect suffixes are covered. Incident-shaped `cat …/tasks/id.output || echo …` could regress if suffix parsing changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a two-invocation Bash case with || echo (or || true) after the .output path.

### FINDING_12: Harness asserts JSON presence, not reminder prose
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Task-output tests assert `additionalContext` presence only, not reminder text; reminder prose could be emptied or wrong while JSON still appears once.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Pin Task-output poll detected or <task-notification> on representative Bash and slow-Read cases.

### FINDING_13: [OUT_OF_SCOPE] `SECURITY.md` does not document new Bash branch
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Existing Read-poll reminder bullet covers path non-reflection but not Bash command parsing on every Bash PostToolUse or session/task-id state files; doc drift, not a vulnerability (warn-only, command bodies not persisted).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Per `AGENTS.md`, a short SECURITY.md addendum noting “Bash commands are classified in-memory only; never persisted or echoed” would close the gap.

### FINDING_14: [OUT_OF_SCOPE] Generic Read state still stores full `sanitized_path` in TSV
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Pre-existing generic Read polling stores full `sanitized_path` in `state-<cwd_hash>.tsv`; paths with sensitive tokens in directory names can land in `/tmp` with mode `600` within same-UID trust model.
- **Suggested revisions (informational for voters; coder decides)**:
  - (none — source provided only generic “Address the concern above.”)

### FINDING_15: Bash multiline/compound uses first matching `tasks/…output` segment
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Parsing always takes the first matching `tasks/<id>.output` segment; a script mentioning task A then polling task B may track A and never fire for B-only polling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Prefer rightmost match or track all task ids per command.

### FINDING_16: Missing `session_id`/`conversation_id` collapses to shared `nosession` bucket
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-state-file-isolation-output.txt
- **Severity**: latent
- **Concern**: When both IDs are absent, all callers hash constant `nosession` per `cwd`+`task_id`; concurrent or sequential sessions can share counters (incorrect early warnings or missed second-read reminder).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document payload requirement or add stronger fallback identity; test missing session fields.
  - From dyn-state-file-isolation-output.txt: Prefer a per-process discriminator when IDs are missing (e.g. `PPID`, a hook-provided `transcript_id` if available, or a random bucket created once per hook parent) instead of a global `nosession` literal; document the fallback; add a harness case that two payloads with no `session_id`/`conversation_id` do not share counters unless that coupling is intentional.

### FINDING_17: Doc overstates session isolation for task-output counters
- **Reviewer(s)**: dyn-state-file-isolation-output.txt
- **Severity**: latent
- **Concern**: `hook-anti-read-poll.md` claims distinct Claude sessions do not share counts within 600s TTL, but that holds only when `session_id` or `conversation_id` is present; `nosession` path contradicts the contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-file-isolation-output.txt: Narrow the sentence to “sessions with distinct `session_id`/`conversation_id` hashes” and explicitly document that missing metadata collapses to a shared `nosession` bucket (with the cross-session bleed behavior above).

### FINDING_18: Non-atomic read-modify-write on task-output state TSV
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-state-file-isolation-output.txt
- **Severity**: latent
- **Concern**: Overlapping hook invocations can both read the same `count` and write `count+1`, losing an increment and delaying threshold=2 behavior (more impactful with lower threshold on primary #3175 path).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Use flock or append-only counting if concurrent delivery is possible.
  - From dyn-state-file-isolation-output.txt: For a warn-only hook, document the best-effort semantics; if stronger guarantees are needed, use an atomic update (`flock` around read/write, or append-only event log) without changing the fail-open exit behavior.

### FINDING_19: [OUT_OF_SCOPE] `test-hook-anti-read-poll.md` stub vs grown harness
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-hook-anti-read-poll.md` remains a one-line stub while harness grew; `script-md-siblings` prefers stubs pointing at primary contract; plan did not require updating test sibling.
- **Suggested revisions (informational for voters; coder decides)**:
  - (none — informational only; source provided only generic “Address the concern above.”)

### FINDING_20: [OUT_OF_SCOPE] `chore(larch-logs)` commits on branch
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Intentional run-log flushes per project convention; not plan scope for #3195.
- **Suggested revisions (informational for voters; coder decides)**:
  - (none — informational only)

### FINDING_21: `||` chains not split; guard pattern can false-positive
- **Reviewer(s)**: dyn-bash-parsing-accuracy-output.txt
- **Severity**: latent
- **Concern**: `bash_line_task_output_poll_token` splits on `;` and `&&` but not `||`. `test -f "$LOCK" || cat …/tasks/<id>.output` stays one segment; when the test succeeds Bash never runs `cat`, but classifier still advances counter (warn-only false positive).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parsing-accuracy-output.txt: extend splitting to treat `||` like `&&` (iterate segments and only treat a segment as a poll-read when it both matches read-verb + task-output path and is not provably dead code on the RHS of `||` when a preceding segment is a simple success test), or document `||` guards as unsupported and accept the false-positive rate for a warn-only hook.

### FINDING_22: `&&` chains lack short-circuit model (dead RHS still counted)
- **Reviewer(s)**: dyn-bash-parsing-accuracy-output.txt
- **Severity**: latent
- **Concern**: After `&&` splitting, each RHS segment is classified independently; `false && cat …/tasks/<id>.output` still counts `cat` though Bash will not execute it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parsing-accuracy-output.txt: when walking `&&`-split segments left-to-right, skip segments after an earlier segment that is a known false literal (`false`, `:`) or add a conservative “only count the rightmost segment that both has a read verb and task-output token” rule for `&&` chains.

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
