# Review Round 1

- Mode: `diff`
- 6 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: DEGRADED_PANEL_WARNING lost across Step 3 loop phases
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-step3-propagation-output.txt, dyn-mixed-manifest-output.txt
- **Severity**: important
- **Concern**: `DEGRADED_PANEL_WARNING` is set in round `values` by `execute_round` when invalid slots are skipped, but the Step 3 loop does not carry it through later phases. On the dominant `LOOP_STATUS=complete` path with accepted findings, `degraded_values` stays empty (it is only populated for `zero-findings-degraded-panel`), mid-loop envelope writes rebuild from empty `degraded_values`, and `complete_values` merges only `PLAN_REVIEW_CONTINUE_REASON`, `ACCEPTED_COUNT`, and `DEGRADED_PANEL` from continuation. The warning is therefore omitted from `.step3-review-result.env` and terminal loop stdout on the common successful-degradation path, and also on the zero-accepted-findings continuation path. Pause/resume or hook recovery between round completion and final emit can read a result env without the warning even though the round already emitted it. `--read-result-env` and other result-env-only consumers miss the signal when persistence fails, though wrapper stdout overlay may still recover it in some paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Carry DEGRADED_PANEL_WARNING from round values through apply/continuation (e.g. into degraded_values after _run_round_body), include it in complete_values, and add a run_step3_review integration test.
  - From cursor-specialist-correctness-output.txt: Persist round warnings to result env immediately after _run_round_body, or retain a round_values dict across phases.
  - From cursor-specialist-correctness-output.txt: Carry the latest round values, or at least DEGRADED_PANEL_WARNING, across all post-round phase transitions and pass them into step3_loop_emit_envelope and step3_loop_persist_envelope.
  - From cursor-specialist-edge-cases-output.txt: Include DEGRADED_PANEL_WARNING in the complete_values merge set or emit from merged result-env before return.
  - From codex-specialist-edge-cases-output.txt: Preserve the last round warning across awaiting-continuation or persist it before that phase, with a loop-level regression test.
  - From codex-specialist-testing-output.txt: Preserve the warning across later Step 3 phases and add a loop-level successful-completion regression test.
  - From dyn-step3-propagation-output.txt: Carry `DEGRADED_PANEL_WARNING` through the apply/continuation phases the same way as other round-scoped warnings (e.g. add it to the `complete_values` merge set, or persist it on the first round completion before entering `awaiting-apply`, or fold it into a round-scoped carrier that survives until terminal emit).
  - From dyn-step3-propagation-output.txt: After `_run_round_body` returns with a non-empty `values["DEGRADED_PANEL_WARNING"]`, stash it in a durable round-scoped carrier (similar to `degraded_values`) and include it in every subsequent `step3_loop_emit_envelope` call until terminal completion or explicit continuation reset.
  - From dyn-step3-propagation-output.txt: Fix result-env persistence in `plan_review.py` (primary), and optionally teach `--read-result-env` to fall back to the last `DEGRADED_PANEL_WARNING=` line from captured loop stdout when the result env omits it.
  - From dyn-mixed-manifest-output.txt: When round `values` contain a non-empty `DEGRADED_PANEL_WARNING`, copy it into `degraded_values` (or add it to the `complete_values` continuation allowlist) before post-apply / final `step3_loop_emit_envelope`, matching the `zero-findings-degraded-panel` handling at `python/plan_review.py:1274-1275`.


### FINDING_2: DROPPED_SLOTS_FILE written outside --no-fallback
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `DROPPED_SLOTS_FILE` is written whenever any drop has a reason, not only under `--no-fallback`, contradicting the plan to keep `DROPPED_SLOTS_FILE` semantics unchanged. Fallback-mode `/review` dispatch with one collector failure now emits `DROPPED_SLOTS_FILE`; on main it would not, changing drop discovery for all non-no-fallback waterfall consumers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Restore if opts.no_fallback gating for _write_drops; keep structurally-invalid rows in the separate pre-launch .invalid-slots sidecar only.


### FINDING_3: Adaptive straggler cutoff bundled out of #4768 scope
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The feature commit bundles adaptive straggler cutoff and always passes `--straggler-cutoff` from `dispatch_panel`, outside #4768 plan scope. A multi-reviewer plan-review panel can SIGTERM slow reviewers after the adaptive deadline, shipping a partially reviewed plan without invalid-slot-style `DEGRADED_PANEL_WARNING`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Split straggler work or gate it behind explicit opt-in; do not enable it as part of the invalid-slot degradation fix without confirmed product intent.


### FINDING_6: Unsanitized slot labels in DEGRADED_PANEL_WARNING
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `DEGRADED_PANEL_WARNING` embeds manifest-derived slot labels without CRLF sanitization or length bounds. A dropped row with a JSON slot value containing newline can produce a multi-line KV value, inject extra KV lines such as `PANEL_PRUNED_EMPTY=true` into panel stdout, alter downstream parsing, and cause `phase_driver_write_result_env` to reject CRLF so Step 3 persist can raise `ValueError` after an otherwise successful degraded dispatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Strip or reject CR/LF in slot labels and the composed warning before emit/persist, matching PLAN_REVIEW_CONTINUE_REASON handling in plan_review.py.
  - From codex-specialist-edge-cases-output.txt: Flatten CR LF TAB before adding labels, cap label length, and fall back to snippet or line number for unsafe labels.


### FINDING_13: DEGRADED_PANEL_WARNING last-writer-wins between invalid-slot and voter-quota degradation
- **Reviewer(s)**: dyn-step3-propagation-output.txt
- **Severity**: important
- **Concern**: `DEGRADED_PANEL_WARNING` is shared between invalid-slot drops (`dispatch_panel`) and voter-quota degradation (`dispatch_voters`). In `execute_round`, voter stdout (which may contain a voter warning) is printed before the `_emit` loop over `values`; when both degradations occur in one round, the panel invalid-slot warning in `values` is the last `DEGRADED_PANEL_WARNING=` emitted and wins in downstream KV parsing, silently hiding voter-quota degradation from the operator.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-step3-propagation-output.txt: Use distinct keys (e.g. `INVALID_SLOT_PANEL_WARNING` vs existing voter warning), or concatenate both messages into one explicit combined warning rather than last-writer-wins on a single key.


### FINDING_15: Invalid manifest rows can overwrite slot_by_output mapping
- **Reviewer(s)**: dyn-mixed-manifest-output.txt
- **Severity**: important
- **Concern**: With `--skip-invalid-slots`, structurally invalid dict rows stay in `plan-review-slots.ndjson` by design, and `_iter_manifest_dict_rows` still yields every dict row. `_compose_findings_from_collector` builds `slot_by_output` from that full set, so a skipped row that still has `slot` and `output` can overwrite an earlier valid mapping when both rows share the same `output` path. That mislabels collector findings for the reviewer that actually ran. This path was unreachable before because load-time fail-closed aborted the panel first.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-mixed-manifest-output.txt: When building `slot_by_output`, include only rows that pass the same structural checks as `_parse_slot_row`, or restrict the map to outputs present in the panel paths file / collector records.


