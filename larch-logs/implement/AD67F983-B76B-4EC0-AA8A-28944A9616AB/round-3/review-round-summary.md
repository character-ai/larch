# Review Round 3

- Mode: `diff`
- 3 accepted, 3 rejected (1 neutral)

## Accepted Findings

### FINDING_1: In-flight Gantt trusts symlink-followed `round-start-s`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `_render_inflight_gantt` trusts symlink-followed `round-start-s` reads, bypassing the round N>1 N-1-end fallback when the symlink points at an early epoch. A pre-created round-2 `round-start-s` symlink to a file containing the Step 5 phase-start epoch forces window `[phase-start, now]` on round 2 in-flight chart; prior-round vendor rows leak back under the Round 2 heading.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Treat symlinked `round-start-s` as absent in `_read_epoch_file` (or at the call site) so round N>1 uses `_prior_immediate_round_end_s` / dir mtime.


### FINDING_4: `_round_dir_is_fresh` treats any `round-start-s` as fresh forever
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `_round_dir_is_fresh` treats any `round-start-s` as fresh forever. This branch now writes `round-start-s` for normal `/design` rounds at `skills/design/scripts/review-design-step3-loop.sh:647-649`, so after Step 3 completes and a later design timing mark is written, `_render_design` can still route to the plan-review renderer and show the completed round as “in progress” instead of reporting the current later step.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Only treat `round-start-s` as fresh when `mark_ts` is absent or the recorded start is newer than the latest timing mark. Otherwise fall through to the existing child-mtime freshness check.


### FINDING_5: `persist_design_round_start_s` writes outside allowlisted design tmpdir
- **Reviewer(s)**: dyn-round-start-safety-output.txt
- **Severity**: important
- **Concern**: The new `persist_design_round_start_s` / `plan-review persist-round-start-s` CLI writes under an arbitrary `--design-tmpdir` without calling `validate_design_tmpdir()` or rejecting a symlinked design-tmpdir leaf. Sibling writers in the same module (`drift_baseline_write_once`, `step3_record_report_evidence`, `emit_design_plan_preview`) enforce the session cache allowlist before touching files. This new surface can `mkdir` and create `plan-review/round-N/round-start-s` under any writable absolute path when the CLI is invoked with attacker-controlled arguments. Payload is only a timestamp, but it is still an unscoped write primitive outside the intended tmpdir boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-round-start-safety-output.txt: At the top of `persist_design_round_start_s`, call `validate_design_tmpdir(str(design_tmpdir))` and return non-zero from the CLI on failure; also reject `Path(design_tmpdir).is_symlink()` like `drift_baseline_write_once`. Add a regression test (e.g. disallowed `/etc` or non-allowlisted path) mirroring `test_record_report_evidence_requires_design_tmpdir`.


