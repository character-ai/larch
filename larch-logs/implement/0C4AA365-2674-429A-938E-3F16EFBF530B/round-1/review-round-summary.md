# Review Round 1

- Mode: `diff`
- 8 accepted, 4 rejected (3 neutral)

## Accepted Findings

### FINDING_11: MAV tally-error harness lacks byte-compatible persist-retally assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-mav-harness-output.txt
- **Severity**: important
- **Concern**: Plan-required persist-retally harness extension and byte-compatible tally-error env assertions are missing. `D_ERR` only checks one review-env KV. MAV post tally-error could stop omitting stale `SCOPE_ANCHOR_FILE` or zeroing accepted counts without CI failure because assertions are weaker than `test-persist-retally-step3-env.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add MAV fixture with seeded `SCOPE_ANCHOR_FILE` and partial accepted artifacts; assert both env files match persist-retally tally-error invariants; optionally extend `test-persist-retally-step3-env.sh` for wrapper integration.
  - From dyn-mav-harness-output.txt: Extend `D_ERR` (or add a sibling fixture) with assertions mirroring `test-persist-retally-step3-env.sh` tally-error checks on both env files, anchor omission, and zeroed counts.


### FINDING_12: approval-gates.md still documents removed inline MAV mechanics
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Prose guards no longer cover `approval-gates.md`, which still documents removed `_RETALLY_SCOPE_ANCHOR_IN` prompt-side mechanics. Gate B re-entry can follow `approval-gates.md` and reintroduce inline MAV steps alongside `design-step3-mav.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Update `approval-gates.md` to delegate to `design-step3-mav.sh` pre/post; extend prose regression probes to include `approval-gates.md`.


### FINDING_17: relevant-checks routes orchestrator-fence edits only to test-design-step3-mav
- **Reviewer(s)**: dyn-mav-harness-output.txt
- **Severity**: important
- **Concern**: Edits to `skills/design/scripts/test-step3-orchestrator-fence.sh` route only to `test-design-step3-mav`, not to `test-step3-orchestrator-fence`. The orchestrator-fence harness still owns distinct Step 3 handoff checks. A change confined to that file can break fence coverage while incremental `relevant-checks` stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-mav-harness-output.txt: In the same `case` arm, also `append_target_once test-step3-orchestrator-fence`, or split orchestrator-fence edits into their own mapping that runs both harnesses.


### FINDING_19: SKILL.md MAV invocation lacks launcher bash fences for post
- **Reviewer(s)**: dyn-mav-harness-output.txt
- **Severity**: important
- **Concern**: MAV pre/post invocation lives in numbered prose only; there is no fenced `"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step3-mav.sh ...` block like other Step 3 wrappers. Step 1 names the launcher for pre; step 5 does not. `test-design-step3-mav.sh` invokes the subject directly, and `test-step3-orchestrator-fence.sh` prose-pins the launcher only for pre, not post. Launcher transport, session rehydration, and pause-check wiring are unenforced for half of the migrated boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-mav-harness-output.txt: Add explicit launcher bash fences for both MAV phases in `SKILL.md`, extend orchestrator-fence prose pins to require launcher transport for post, and add a harness case that exercises MAV through a minimal fake `design-run` launcher stub rather than direct subject invocation.


### FINDING_6: Broken symlink result envs treated as absent instead of rejected
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Broken symlink result envs are treated as absent instead of rejected. `.step3-review-result.env -> /tmp/missing` skips `read-result-env.sh` and falls back to stale session or secondary state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Treat `-L` as present and reject or pass through `read-result-env.sh`; add a broken-symlink test.


### FINDING_7: MainAgent warning sentinel is global instead of per artifact round
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The MainAgent / 0-judge warning sentinel is session-global (tmpdir-wide) instead of per artifact round. If round 2 and round 3 both use MainAgent adjudication, round 3 gets no Warnings entry and the 0-judge execution-issues warning is skipped, regressing per-adjudication logging from the old inline flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Key the sentinel by `artifact_round` and pass that round into `append_mav_warning_once`.
  - From cursor-specialist-edge-cases-output.txt: Key sentinel by artifact round; extend harness for multi-round warning behavior.
  - From codex-specialist-edge-cases-output.txt: Include the artifact round in the sentinel and warning filename, and mark only that round as appended.
  - From codex-specialist-testing-output.txt: Include the round in the sentinel/log names, pass `artifact_round` into the helper, and add a two-round warning test.


### FINDING_8: Missing-voter tally-error path bypasses canonical findings-classification.tsv
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The missing-voter tally-error path bypasses canonical tally output and omits or leaves stale `plan-review/round-N/findings-classification.tsv`. If post runs before `voter-main-agent.txt` exists, the classification file is missing or stale while env status says `tally-error`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Always invoke `tally-plan-review.sh` with `--findings-classification-out`, or write the canonical header stub in the manual branch.
  - From codex-specialist-edge-cases-output.txt: Let `tally-plan-review.sh` handle unreadable voters with `--findings-classification-out`, or write the same header/stub before persisting `tally-error`.
  - From codex-specialist-testing-output.txt: Let `tally-plan-review` handle unreadable voter with `--findings-classification-out`, or write the same header-only TSV in the manual branch and test it.


### FINDING_9: SKILL step 5 aborts MAV post only on exit 2, not exit 1
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: SKILL step 5 aborts MAV post only on exit 2, not exit 1. The orchestrator continues after post exit 1 (bad result env or invalid resume round), leaving stale phase files and skipping tally-error or resume routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Align step 5 with step 1: abort on any non-zero post exit; add harness for loop mode with invalid resume round.


