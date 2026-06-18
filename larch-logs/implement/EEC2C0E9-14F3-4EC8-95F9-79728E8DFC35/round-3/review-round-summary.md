# Review Round 3

- Mode: `diff`
- 3 accepted, 4 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Foreground probe docs omit DESIGN_TMPDIR inline prefix
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Foreground terminal-sentinel recovery docs omit the `DESIGN_TMPDIR=<abs>;` prefix that the background waiter documents. After a premature notification with a killed recovery waiter, the orchestrator may run an unprefixed `[ -f "$DESIGN_TMPDIR/.completed/step-3-terminal" ]` probe; `$DESIGN_TMPDIR` is empty in the Bash subshell, the probe always prints WAIT, and `ps` polling returns despite a written sentinel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add the same prefix guidance for foreground probes in `skills/design/SKILL.md`, `AGENTS.md`, and `skills/shared/orchestrator-never.md`; optionally pin it in `scripts/test-implement-anti-polling-rule.sh`.


### FINDING_15: Stale `step-3` milestone can authorize premature Step 3b routing
- **Reviewer(s)**: dyn-sentinel-contract-output.txt
- **Severity**: important
- **Concern**: The post-loop branch matrix treats a present `.completed/step-3` as sufficient to proceed to Step 3b, and only requires `.completed/step-3-terminal` when `step-3` is absent. That inverts the sentinel split: on terminal paths `review-design-step3-loop.sh` calls `step3_loop_write_completed_step3()` before `step3_loop_emit_envelope()` / `step3_loop_persist_envelope()`, so `step-3` can exist while the current-pass envelope and `step-3-terminal` do not. Resume launches clear stale `step-3-terminal` / `.step3-terminal-persisted-this-run` but, when `STEP3_REVIEW_HAS_RESUME_STATE=true`, do not clear `.completed/step-3` or `.step3-review-result.env`. The EXIT trap's `_step3_review_should_guarantee_step3()` can mint `.completed/step-3` from stale readable `.step3-review-result.env` without checking the current-pass persist sidecar. Combined, an orchestrator can advance toward Step 3b on a milestone sentinel without a durable terminal sentinel or fresh envelope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sentinel-contract-output.txt: Require `.completed/step-3-terminal` (and readable current-pass `.step3-review-result.env`) before any post-notification envelope parsing for all terminal statuses; require `.completed/step-3` only as the additional Step 3b routing gate. Mirror the same two-step rule in the duplicated Step 3 boundary blocks (~598, ~655) and add a harness case for "`step-3` present, `step-3-terminal` absent, guard inactive".
  - From dyn-sentinel-contract-output.txt: On `--starting-round` / phase-resume entry, clear `.completed/step-3` when the resume is mid-loop (or always clear `step-3` alongside the terminal-sentinel cleanup unless pause/Gate B semantics forbid it), and gate `_step3_review_should_guarantee_step3()` on the same `.step3-terminal-persisted-this-run` sidecar used for terminal-sentinel minting.


### FINDING_18: `[[` file-test forms bypass foreground-probe whitelist and deny heuristics
- **Reviewer(s)**: dyn-guard-whitelist-output.txt
- **Severity**: important
- **Concern**: `bash_is_terminal_sentinel_foreground_probe()` whitelist only accepts single-bracket `[ -f … ]` and `test -f …` forms, while `bash_has_bracket_file_test` also matches only single `[`, not `[[`. Because the foreground-probe helper exits 0 before the generic deny loop, commands like `[[ -f "$DESIGN_TMPDIR/.completed/step-3.5" ]] && echo DONE || echo WAIT` or `[[ -f "$DESIGN_TMPDIR/.completed/step-3-terminal" ]] && echo DONE || echo WAIT` bypass both the allow matcher and downstream deny rules (`[[` is not in `_PROBE_VERB_RE`; non-terminal deny `case` blocks `.completed/step-3` / `.completed/step-5c` but not `.completed/step-3.5`). That reopens polling of pause/Gate B milestones and sidesteps symlink check, live-dir binding, and documented recovery contract for terminal probes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-guard-whitelist-output.txt: Treat `[[ … -f … ]]` the same as `[ … -f … ]` in deny logic (extend `bash_has_bracket_file_test` to match `[[`), and extend the foreground-probe pre-check `case` to reject any `.completed/step-3.5` reference; optionally add a harness deny case for `[[ -f …step-3.5… ]]` under a live `design-step3-review` marker.
  - From dyn-guard-whitelist-output.txt: Either explicitly allow `[[ -f … ]]` in the same anchored patterns (with the same sentinel list, echo tail, assignment prefix, live-dir binding, and symlink denial), or deny `[[` file tests on `$DESIGN_TMPDIR` paths whenever a live marker exists; add regression tests for both terminal and non-terminal targets.


