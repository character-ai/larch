# Review Round 5

- Mode: `diff`
- 7 accepted, 20 rejected (13 exonerated)

## Accepted Findings

### FINDING_12: risk-integration: skills/implement/scripts/test-step-7a.sh:80-348
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No golden or integration assertion for byte-identical larch:diagrams comment content On a run with a real architecture diagram file and sanitizer edge cases, summary body can drift from SKILL.md without CI failure Add fixture/golden tests for summary-diagrams.md and key upsert inputs across skip/fail/architecture paths
- **Suggested revision**: Address the concern above.


### FINDING_20: correctness: skills/implement/scripts/step-7a.sh:366-414
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Sanitizer rejection suppresses larch:diagrams upsert unlike main which always upserted with placeholder. Tracking issue keeps a prior run's diagram comment after sanitizer rejection; reviewers see stale Mermaid. Restore always-upsert placeholder behavior or document contract change and align acceptance/tests.
- **Suggested revision**: Address the concern above.


### FINDING_31: **architecture** `larch-logs/implement/1D8914D7-AEAA-461D-839A-FED904799FBB/plan-goals-test.md:44` — Phase 12 still says `step-7a.sh` “exit stays 0” on rebase failure while the shipped helper does `exit "$rebase_rc"` at `skills/implement/scripts/step-7a.sh:429-432`. That contradicts the authoritative surfaces updated on this branch (`skills/implement/scripts/step-7a.md:31-37`, `skills/implement/SKILL.md:129-147,1436-1437`, `skills/implement/scripts/test-step-7a.sh:476-494`). The runtime behavior is correct for the Rebase Checkpoint Macro (orchestrator must see probe exit 1/3 on the wrapper process, not only stdout KVs), but the stale run-log plan can mislead a follow-up change into “fixing” working exit propagation. **Suggested fix:** Update the committed plan snapshot (and any mirrored design plan text) to state that `step-7a.sh` preserves `rebase-checkpoint-probe.sh` exit codes 1/3 (and other non-zero codes), sets `LOG_FLUSH_STATUS=skipped-rebase-checkpoint`, emits the diagram KV tail, and skips pre-bump flush on non-zero rebase; keep argv as the only `STEP_7A_BAIL_REASON` path (`exit 2`).
- **Reviewer**: dyn-rebase-exit-propagation-output.txt
- **Concern**: - **architecture** `larch-logs/implement/1D8914D7-AEAA-461D-839A-FED904799FBB/plan-goals-test.md:44` — Phase 12 still says `step-7a.sh` “exit stays 0” on rebase failure while the shipped helper does `exit "$rebase_rc"` at `skills/implement/scripts/step-7a.sh:429-432`. That contradicts the authoritative surfaces updated on this branch (`skills/implement/scripts/step-7a.md:31-37`, `skills/implement/SKILL.md:129-147,1436-1437`, `skills/implement/scripts/test-step-7a.sh:476-494`). The runtime behavior is correct for the Rebase Checkpoint Macro (orchestrator must see probe exit 1/3 on the wrapper process, not only stdout KVs), but the stale run-log plan can mislead a follow-up change into “fixing” working exit propagation. **Suggested fix:** Update the committed plan snapshot (and any mirrored design plan text) to state that `step-7a.sh` preserves `rebase-checkpoint-probe.sh` exit codes 1/3 (and other non-zero codes), sets `LOG_FLUSH_STATUS=skipped-rebase-checkpoint`, emits the diagram KV tail, and skips pre-bump flush on non-zero rebase; keep argv as the only `STEP_7A_BAIL_REASON` path (`exit 2`).
- **Suggested revision**: Address the concern above.


### FINDING_32: **architecture** `skills/implement/scripts/step-7a.md:31-38` — The exit table documents `0`, `1`, `3`, and `2` but not the macro’s “other non-zero exit” branch (`skills/implement/SKILL.md:133`, `scripts/rebase-checkpoint-probe.md:24`), even though `step-7a.sh:432` forwards any non-zero `rebase_rc` verbatim. That gap is amplified by this branch because 7a.r is no longer a separate foreground probe call. **Suggested fix:** Add a row such as “other non-zero: preserved probe exit; orchestrator uses the macro’s `unexpected-rc-<n>` / other-non-zero routing” and note that only `REBASE_OUTCOME=ok|skipped` runs the pre-bump flush phase.
- **Reviewer**: dyn-rebase-exit-propagation-output.txt
- **Concern**: - **architecture** `skills/implement/scripts/step-7a.md:31-38` — The exit table documents `0`, `1`, `3`, and `2` but not the macro’s “other non-zero exit” branch (`skills/implement/SKILL.md:133`, `scripts/rebase-checkpoint-probe.md:24`), even though `step-7a.sh:432` forwards any non-zero `rebase_rc` verbatim. That gap is amplified by this branch because 7a.r is no longer a separate foreground probe call. **Suggested fix:** Add a row such as “other non-zero: preserved probe exit; orchestrator uses the macro’s `unexpected-rc-<n>` / other-non-zero routing” and note that only `REBASE_OUTCOME=ok|skipped` runs the pre-bump flush phase.
- **Suggested revision**: Address the concern above.


### FINDING_33: **architecture** `skills/implement/scripts/test-step-7a.sh` — Rebase exit propagation is covered for conflict (`exit 1`) and failed (`exit 3`), but there is no case where the stub probe exits with an unexpected code (e.g. `5` with `REBASE_ERROR=unexpected-rc-5`) to pin the third macro branch after consolidation. **Suggested fix:** Add a `rebase-unexpected-rc` harness case asserting `rc=5`, relayed `REBASE_OUTCOME=failed` / `REBASE_ERROR=unexpected-rc-5`, `LOG_FLUSH_STATUS=skipped-rebase-checkpoint`, and no flush helpers in `calls.log`.
- **Reviewer**: dyn-rebase-exit-propagation-output.txt
- **Concern**: - **architecture** `skills/implement/scripts/test-step-7a.sh` — Rebase exit propagation is covered for conflict (`exit 1`) and failed (`exit 3`), but there is no case where the stub probe exits with an unexpected code (e.g. `5` with `REBASE_ERROR=unexpected-rc-5`) to pin the third macro branch after consolidation. **Suggested fix:** Add a `rebase-unexpected-rc` harness case asserting `rc=5`, relayed `REBASE_OUTCOME=failed` / `REBASE_ERROR=unexpected-rc-5`, `LOG_FLUSH_STATUS=skipped-rebase-checkpoint`, and no flush helpers in `calls.log`.
- **Suggested revision**: Address the concern above.


### FINDING_36: **architecture** `skills/implement/scripts/step-7a.sh:351-355` — After `larch_quiet_init` (line 10), the small/non-runtime skip path uses raw `printf` for `⏩ 7a: diagrams status=skip reason=small-non-runtime-change …`. Under production `/implement`, that writes to the quiet log (redirected FD 1), not the caller-visible contract stream (FD 3). On `main`, the same line was orchestrator-visible because the classifier lived in an ordinary Bash fence without quiet redirection. `SKILL.md` Verbosity Control (lines 113–115) explicitly preserves non-rebase `⏩` skip lines; hiding them is a regression. The harness masks this: `test-step-7a.sh` exports `LARCH_QUIET_DISABLE=1` (line 6), so `diagram-skip` sees the line in captured `2>&1` output even though production would not. **Suggested fix:** Emit the skip line through the contract API (`emit '⏩ 7a: diagrams status=skip reason=small-non-runtime-change elapsed=…'` or an appropriate `emit_breadcrumb --category=progress …`) so it lands on FD 3 in quiet mode; add a `run_helper_quiet` assertion for that line (mirroring `quiet-rebase-contract`).
- **Reviewer**: dyn-kv-fd3-contract-output.txt
- **Concern**: - **architecture** `skills/implement/scripts/step-7a.sh:351-355` — After `larch_quiet_init` (line 10), the small/non-runtime skip path uses raw `printf` for `⏩ 7a: diagrams status=skip reason=small-non-runtime-change …`. Under production `/implement`, that writes to the quiet log (redirected FD 1), not the caller-visible contract stream (FD 3). On `main`, the same line was orchestrator-visible because the classifier lived in an ordinary Bash fence without quiet redirection. `SKILL.md` Verbosity Control (lines 113–115) explicitly preserves non-rebase `⏩` skip lines; hiding them is a regression. The harness masks this: `test-step-7a.sh` exports `LARCH_QUIET_DISABLE=1` (line 6), so `diagram-skip` sees the line in captured `2>&1` output even though production would not. **Suggested fix:** Emit the skip line through the contract API (`emit '⏩ 7a: diagrams status=skip reason=small-non-runtime-change elapsed=…'` or an appropriate `emit_breadcrumb --category=progress …`) so it lands on FD 3 in quiet mode; add a `run_helper_quiet` assertion for that line (mirroring `quiet-rebase-contract`).
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: skills/implement/scripts/step-7a.sh:366-379
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Sanitizer STATUS=skipped suppresses larch:diagrams upsert; main SKILL always posted placeholder comment. Sanitizer rejection leaves stale or missing tracking-issue diagrams comment vs pre-change runs. Align acceptance with skip behavior or restore upsert-with-placeholder for sanitizer path.
- **Suggested revision**: Address the concern above.


