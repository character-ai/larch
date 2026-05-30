### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:82-83
- **Concern**: Collector dedup pass anchored at line ~852 is before the retry loop (section 3 starts ~854) and before sections 3.5–3.7 that rewrite RESULTS. Scenario: Implementer inserts dedup after the first classification loop; retries/NS-retry/substantive passes still change STATUS afterward, so FD-2 tails can be missing, stale, or emitted for slots that later become OK
- **Proposed resolution**: Place the dedup-emit pass immediately before section 4 (current ~1419), after section 3.7 completes; drop the ~852 anchor and cite the post-3.7 / pre-4 boundary explicitly

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:84-85;scripts/collect-agent-results.sh:1164-1165
- **Concern**: Collector dedup reads `${OUTPUT}.stderr-tail` from REVIEWER_FILE, but retry failure rows keep REVIEWER_FILE at ORIG_OUTPUT while `build_failure_reason` and `run-external-agent.sh` use `${ORIG_OUTPUT%.txt}-retry.txt`. Scenario: After a retried failure, chat can show the first-attempt stderr tail while FAILURE_REASON describes the retry attempt (or skip the retry tail entirely if only `${RETRY_OUTPUT}.stderr-tail` exists)
- **Proposed resolution**: Resolve tail path in the dedup pass: prefer `${REVIEWER_FILE%.txt}-retry.txt.stderr-tail` when present for failed slots, else `${REVIEWER_FILE}.stderr-tail`; extend `test-collect-agent-results.sh` with a retry-failure case

### FINDING_3:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/collect-agent-results.sh:852-1419
- **Concern**: Dedup pass anchored before retry/validation. Scenario: Dedup runs on first-pass RESULTS only; retries and NOT_SUBSTANTIVE/NS updates never get correct dedup or tails
- **Proposed resolution**: Move dedup-emit to immediately before section 4 (~line 1417) after sections 3-3.7

### FINDING_4:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/collect-agent-results.sh:852-1419
- **Concern**: Dedup pass anchor contradicts final-RESULTS requirement. Scenario: Plan cites ~852 (end of the first validation loop) while also requiring dedup after retries and sections 3.5–3.7; placing the pass at ~852 runs before empty-output retry (854+) and NS/substantive rewrites, so tails can reflect pre-retry state or dedup against slots later marked OK
- **Proposed resolution**: Insert the dedup-emit block immediately before `# --- 4. Emit structured results ---` (~1419), iterating final `RESULTS[]` entries only

### FINDING_5:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/collect-agent-results.sh:1123-1165
- **Concern**: Retry writes `.stderr-tail` on `*-retry.txt` but dedup reads `REVIEWER_FILE` path. Scenario: Empty-output retry re-invokes `run-external-agent.sh` with `RETRY_OUTPUT` (stderr redirected away) while a failed retry keeps `REVIEWER_FILE=$ORIG_OUTPUT`; dedup/signatures use `${REVIEWER_FILE}.stderr-tail`, so post-retry failures miss the fresh tail or reuse a stale first-pass sidecar
- **Proposed resolution**: After retry completes, copy or re-render `${RETRY_OUTPUT}.stderr-tail` onto `${ORIG_OUTPUT}.stderr-tail` when retry fails, or teach the dedup pass to resolve the retry output path from `RESULTS`/`FAILURE_REASON`

### FINDING_6:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/run-external-agent.sh:140-141
- **Concern**: Stale `${OUTPUT}.stderr-tail` not cleared with other sidecars. Scenario: Pre-launch `rm -f` drops `.done`/`.meta`/`.diag` but not `.stderr-tail`; a later success or unrelated failure can leave an old redacted tail that the collector treats as current
- **Proposed resolution**: Add `"${OUTPUT_FILE}.stderr-tail"` to the stale cleanup list (and mirror in harness assertions)

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic, unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/collect-agent-results.sh:852-1419
- **Concern**: Dedup-emit anchor contradicts “after retries settle”. Scenario: Placing the pass near ~852 runs before §3 empty-output retry, §3.5–3.7 NS retry, and final `RESULTS[]` updates, so tails/dedup can reflect pre-retry state or miss retry-final failures
- **Proposed resolution**: Insert the dedup pass immediately before `# --- 4. Emit structured results ---` (~1419), after §3.7; drop the ~852 anchor from the plan

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/collect-agent-results.sh:1140-1166
- **Concern**: Retry failure keeps `REVIEWER_FILE=$ORIG_OUTPUT` but `run-external-agent.sh` writes `${RETRY_OUTPUT}.stderr-tail`. Scenario: Empty-output / transient retry that fails on `*-retry.txt` leaves agent stderr only on the retry basename; collector dedup reading `${REVIEWER_FILE}.stderr-tail` sees nothing or a stale first-pass tail
- **Proposed resolution**: In dedup (and tests), resolve tail from `REVIEWER_FILE` with fallback to `${REVIEWER_FILE%.txt}-retry.txt.stderr-tail` when present, or copy retry tail onto the canonical output path in the retry-failure branch

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/run-external-agent.sh:63-75; scripts/lint-fix-loop.sh:231-237; scripts/launch-codex-implement.sh:324-338
- **Concern**: Stderr source list assumes `${OUTPUT}.sidecar` / `.diag` / output. Scenario: Lint-fix-loop Codex uses `2>"$run_dir/codex.wrapper.log"`; implement launchers use caller `--sidecar-log`, not `${TRANSCRIPT}.sidecar`, so `write_failed_agent_stderr_tail` often sees only generic `.diag` and `emit_failed_agent_stderr_tail_raw` goes to the redirected log, not chat—contrary to the plan’s foreground-lane claim
- **Proposed resolution**: Narrow the plan goal to review/collector batches (where `${OUTPUT}.sidecar` exists) or add a minimal explicit stderr-source hook at the choke point; do not claim lint-fix-loop/implement chat surfacing without launcher-path changes

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/run-external-agent.sh:140-141
- **Concern**: Stale `${OUTPUT}.stderr-tail` not cleared in pre-launch `rm -f`. Scenario: A later failure with empty/missing stderr can leave a prior `.stderr-tail`; collector dedup may re-emit an old redacted tail
- **Proposed resolution**: Add `${OUTPUT_FILE}.stderr-tail` to the stale-artifact cleanup (and unlink in `write_failed_agent_stderr_tail` when render is empty/disabled)

### FINDING_11:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:82-83
- **Concern**: Dedup-emit anchor line ~852 contradicts after-all-retries requirement. Scenario: Placing the pass at ~852 runs before §3 retry (~854-1173) and §3.7 NS-retry (~1265-1417): stale FAILED tails, missing retry tails, or stderr spam for slots later upgraded to OK
- **Proposed resolution**: Anchor dedup immediately before §4 emit (current scripts/collect-agent-results.sh:1418-1419), after every RESULTS[] mutation

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-fd-routing-integrity
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:82-85 / scripts/collect-agent-results.sh:852-1418
- **Concern**: Dedup-emit pass anchored at ~852 before retries/NS settle. Scenario: Inserting dedup after the section-2 loop (~852) runs before section 3 empty-output retry and sections 3.5–3.7 NS retries; emits tails for slots later upgraded to OK and uses non-final STATUS
- **Proposed resolution**: Move dedup immediately before section 4 (`# --- 4. Emit structured results ---`, ~1419); iterate `RESULTS[]`, parse `REVIEWER_FILE` per entry, and gate on final `STATUS`

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-sidecar-lifecycle
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-claude-subprocess.sh:222 scripts/launch-claude-review.sh:180-182
- **Concern**: Claude slot writes .done before parent can write .stderr-tail. Scenario: wait-for-reviewers unblocks on subprocess .done while launch-claude-review still runs post-rc work; collector dedup can skip a missing sidecar for real failures
- **Proposed resolution**: Write .stderr-tail in launch-claude-subprocess.sh immediately before .done (source ${OUTPUT}.stderr), or defer .done until the parent finishes the tail write

### OOS_1:
- **Description**: `${OUTPUT}.sidecar` source order misses custom stderr sinks. Scenario: Launchers that redirect CLI stderr elsewhere (`launch-codex-implement.sh`/`launch-cursor-implement.sh` `--sidecar-log`, `lint-fix-loop.sh` `codex.wrapper.log`) never populate `${OUTPUT}.sidecar`; the planned first-existing source is often `.diag` wrapper text, not agent stderr—undercutting “all lanes” foreground coverage outside `launch-review.sh`/`launch-codex-ci.sh`
- **Reviewer**: unknown-slot
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/run-external-agent.sh:67-71
- **Phase**: design
