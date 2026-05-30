### FINDING_1: Dedup-emit runs before retries and NS/substantive passes settle
- **Reviewer(s)**: Cursor-Arch, unknown-slot, Cursor-Pragmatic, Cursor-dyn-fd-routing-integrity
- **Severity**: important
- **Concern**: The planned dedup-emit pass is anchored near ~852 (end of the first classification loop), which runs before section 3 empty-output retry (~854+), sections 3.5–3.7 (NS/substantive rewrites), and final `RESULTS[]` updates. Dedup/tails can reflect pre-retry state, miss retry-final failures, or emit FD-2 tails for slots later upgraded to OK.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Place the dedup-emit pass immediately before section 4 (current ~1419), after section 3.7 completes; drop the ~852 anchor and cite the post-3.7 / pre-4 boundary explicitly
  - From unknown-slot: Move dedup-emit to immediately before section 4 (~line 1417) after sections 3-3.7
  - From unknown-slot: Insert the dedup-emit block immediately before `# --- 4. Emit structured results ---` (~1419), iterating final `RESULTS[]` entries only
  - From unknown-slot: Anchor dedup immediately before §4 emit (current scripts/collect-agent-results.sh:1418-1419), after every RESULTS[] mutation
  - From Cursor-Pragmatic: Insert the dedup pass immediately before `# --- 4. Emit structured results ---` (~1419), after §3.7; drop the ~852 anchor from the plan
  - From Cursor-dyn-fd-routing-integrity: Move dedup immediately before section 4 (`# --- 4. Emit structured results ---`, ~1419); iterate `RESULTS[]`, parse `REVIEWER_FILE` per entry, and gate on final `STATUS`

### FINDING_2: Dedup reads `${REVIEWER_FILE}.stderr-tail` while retry failures write `*-retry.txt.stderr-tail`
- **Reviewer(s)**: Cursor-Arch, unknown-slot, Cursor-Pragmatic
- **Severity**: important
- **Concern**: On empty-output/transient retry failure, `REVIEWER_FILE` stays at `ORIG_OUTPUT` while `run-external-agent.sh` / `build_failure_reason` use `${ORIG_OUTPUT%.txt}-retry.txt`. Dedup/signatures read `${REVIEWER_FILE}.stderr-tail`, so chat can show a stale first-attempt tail, miss the retry tail entirely, or misalign tail content with `FAILURE_REASON` for the retry attempt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Resolve tail path in the dedup pass: prefer `${REVIEWER_FILE%.txt}-retry.txt.stderr-tail` when present for failed slots, else `${REVIEWER_FILE}.stderr-tail`; extend `test-collect-agent-results.sh` with a retry-failure case
  - From unknown-slot: After retry completes, copy or re-render `${RETRY_OUTPUT}.stderr-tail` onto `${ORIG_OUTPUT}.stderr-tail` when retry fails, or teach the dedup pass to resolve the retry output path from `RESULTS`/`FAILURE_REASON`
  - From Cursor-Pragmatic: In dedup (and tests), resolve tail from `REVIEWER_FILE` with fallback to `${REVIEWER_FILE%.txt}-retry.txt.stderr-tail` when present, or copy retry tail onto the canonical output path in the retry-failure branch

### FINDING_3: Stale `${OUTPUT}.stderr-tail` survives pre-launch sidecar cleanup
- **Reviewer(s)**: unknown-slot, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Pre-launch `rm -f` in `run-external-agent.sh` clears `.done`/`.meta`/`.diag` but not `.stderr-tail`. A later success or unrelated failure with empty/missing stderr can leave an old redacted tail that the collector treats as current and re-emits in dedup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Add `"${OUTPUT_FILE}.stderr-tail"` to the stale cleanup list (and mirror in harness assertions)
  - From Cursor-Pragmatic: Add `${OUTPUT_FILE}.stderr-tail` to the stale-artifact cleanup (and unlink in `write_failed_agent_stderr_tail` when render is empty/disabled)

### FINDING_4: Stderr source list does not cover lint-fix-loop / implement launcher paths
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `write_failed_agent_stderr_tail` assumes `${OUTPUT}.sidecar` / `.diag` / output paths that exist for review/collector batches. Lint-fix-loop Codex redirects stderr to `codex.wrapper.log`; implement launchers use caller `--sidecar-log`, not `${TRANSCRIPT}.sidecar`, so the helper often sees only generic `.diag` and chat surfacing may not match the plan’s foreground-lane claim for those lanes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Narrow the plan goal to review/collector batches (where `${OUTPUT}.sidecar` exists) or add a minimal explicit stderr-source hook at the choke point; do not claim lint-fix-loop/implement chat surfacing without launcher-path changes

### FINDING_5: Claude subprocess `.done` can unblock collector before `.stderr-tail` exists
- **Reviewer(s)**: Cursor-dyn-sidecar-lifecycle
- **Severity**: important
- **Concern**: Claude slots write `.done` before the parent finishes post-rc work including `.stderr-tail`. `wait-for-reviewers` can unblock on subprocess `.done` while `launch-claude-review` still runs tail work, so collector dedup may skip a missing sidecar for real failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-sidecar-lifecycle: Write .stderr-tail in launch-claude-subprocess.sh immediately before .done (source ${OUTPUT}.stderr), or defer .done until the parent finishes the tail write
