### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: correctness: skills/implement/scripts/test-step-7a.sh:342
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Green-path bail-reason assert is substring-based could false-pass if argv tail leaked into output Use grep -Fx or exact-line match for empty STEP_7A_BAIL_REASON
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: risk-integration: skills/implement/scripts/test-step-7a.sh:80-91
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Green-path harness never sets ARCHITECTURE_DIAGRAM_FILE so architecture half of larch:diagrams comment is untested A refactor breaking cat of ARCHITECTURE_DIAGRAM_FILE ships with PASS=16 Add a fixture case with ARCHITECTURE_DIAGRAM_FILE set and assert summary-diagrams.md leading content
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: risk-integration: skills/implement/scripts/test-step-7a.sh:1290-1304
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No case stubs failing larch-log.sh write while expecting LOG_FLUSH_STATUS=ok Regression could mark flush degraded on write-best-effort failures contrary to plan Add stub write failure and assert LOG_FLUSH_STATUS=ok plus Tool Failures entry
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: risk-integration: skills/implement/scripts/test-step-7a.sh:373-374
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] COMMENT_URL assertions use substring COMMENT_URL= only Stale non-empty COMMENT_URL could pass diagram-rejected and upsert-failure cases Assert exact COMMENT_URL= empty line on those paths
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: correctness: skills/implement/scripts/step-7a.sh:10,183-198
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Outer larch_quiet_init hides capture-session-transcript SESSION_TRANSCRIPT_STATUS from Bash tool stdout. After consolidation the orchestrator no longer sees SESSION_TRANSCRIPT_STATUS on combined stdout; debugging and any prompt-side parsing of that line break vs main inline Step 7a. Run capture with LARCH_QUIET_DISABLE=1 or re-emit SESSION_TRANSCRIPT_STATUS to FD 3; add harness coverage.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_20: risk-integration: skills/implement/scripts/step-7a.sh:40-50,195-198
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] append-tool-failure.sh output is discarded so execution-issues.md may stay empty on failures. Flush or diagram failures can leave no Tool Failures or Warnings entries while KV tail shows degraded or exit 0. Stop redirecting append-tool-failure to /dev/null; record append failures in KV or stderr.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: correctness: skills/implement/scripts/step-7a.sh:195-198
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] capture-session-transcript rc check is dead because the helper always exits 0. Future capture behavior changes will not flip LOG_FLUSH_STATUS via rc; maintainers may assume rc-based handling exists. Remove dead rc branch or degrade based on SESSION_TRANSCRIPT_STATUS parsing.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: correctness: skills/implement/scripts/step-7a.sh:58-63
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] *reject* glob in should_skip_diagram_upsert is overly broad. A future SKIP_REASON containing reject could suppress larch:diagrams upsert without posting any comment. Use explicit REASON_TOKEN list instead of *reject* substring match.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_27: correctness: skills/implement/scripts/step-7a.sh:407-418
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Rebase failure exits 1/3 and skips pre-bump flush contrary to plan section 12 exit 0 After rebase conflict callers following issue plan expect flush to run; step-7a exits early and LOG_FLUSH_STATUS=skipped-rebase-checkpoint Update larch:plan to match step-7a.md/SKILL.md or change script to exit 0 and handle conflict only in macro prose
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_28

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_28: architecture: skills/implement/scripts/step-7a.sh:407-414
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Rebase probe stdout captured to file and re-emitted instead of FD3 inheritance per plan Probe diagnostics emitted only on FD3 could be lost before orchestrator macro routing Document capture-relay as canonical or stop redirecting probe stdout
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: skills/implement/scripts/step-7a.sh:143-232
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] run_log_flush inlines the full pre-bump batch table instead of reusing a shared helper. Future batch slug or ordering changes require editing step-7a.sh and refresh paths separately, increasing drift risk. Extract a shared pre-bump-log-flush.sh after landing and keep step-7a.sh as thin orchestration.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_31

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_31: **correctness** `skills/implement/scripts/step-7a.sh:129-137,151-157,173-176,184-194,201-210,218-224,346-349,386-392` — Every guarded block uses `set +e` before the command and `set +e` again after `rc=$?` instead of the repo’s usual `set +e` / `set -e` pair (see `skills/implement/scripts/oos-disposition-gate.sh:48-51` and `skills/implement/scripts/test-step-7a.sh:333-336`). In Bash, `set` inside a function mutates the caller’s option state; these blocks never re-enable errexit. That is mostly harmless while the script stays without `-e`, but it amplifies the bug above once line 410 enables `-e`, and it is a footgun for any later edit that adds top-level `-e`. **Suggested fix:** Replace the second `set +e` in each pair with `set -e` when restoring a prior `-e` session, or remove the toggles entirely and rely on `rc=$?` plus `|| true` / explicit failure routing, matching `flush-execution-issues.sh`’s top-level style without introducing mid-script `-e`.
- **Reviewer**: dyn-shell-mode-flags-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/step-7a.sh:129-137,151-157,173-176,184-194,201-210,218-224,346-349,386-392` — Every guarded block uses `set +e` before the command and `set +e` again after `rc=$?` instead of the repo’s usual `set +e` / `set -e` pair (see `skills/implement/scripts/oos-disposition-gate.sh:48-51` and `skills/implement/scripts/test-step-7a.sh:333-336`). In Bash, `set` inside a function mutates the caller’s option state; these blocks never re-enable errexit. That is mostly harmless while the script stays without `-e`, but it amplifies the bug above once line 410 enables `-e`, and it is a footgun for any later edit that adds top-level `-e`. **Suggested fix:** Replace the second `set +e` in each pair with `set -e` when restoring a prior `-e` session, or remove the toggles entirely and rely on `rc=$?` plus `|| true` / explicit failure routing, matching `flush-execution-issues.sh`’s top-level style without introducing mid-script `-e`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_36

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_36: **architecture** `skills/implement/scripts/step-7a.sh:415-418` vs embedded plan in `larch-logs/` — The implementation intentionally diverges from the issue plan’s “exit 0 except argv” contract by propagating rebase probe exits (`exit "$rebase_rc"`) and emitting `LOG_FLUSH_STATUS=skipped-rebase-checkpoint` before early exit; `step-7a.md:30-37` and `SKILL.md:1434` document that behavior, which matches pre-consolidation semantics (standalone probe returned 1/3 to the orchestrator). This is not a runtime regression, but the stale plan/acceptance text still claims exit-0-always and omits `skipped-rebase-checkpoint`, which can mislead reviewers and implementers into “fixing” the propagation back to exit 0. **Suggested fix:** Treat propagation as canonical; update the issue plan / `larch:plan` acceptance bullets to document exits `1`/`3`, `LOG_FLUSH_STATUS=skipped-rebase-checkpoint`, and that macro routing consumes `step-7a.sh`’s process exit code—not a wrapper that always returns 0.
- **Reviewer**: dyn-rebase-exit-propagation-output.txt
- **Concern**: - **architecture** `skills/implement/scripts/step-7a.sh:415-418` vs embedded plan in `larch-logs/` — The implementation intentionally diverges from the issue plan’s “exit 0 except argv” contract by propagating rebase probe exits (`exit "$rebase_rc"`) and emitting `LOG_FLUSH_STATUS=skipped-rebase-checkpoint` before early exit; `step-7a.md:30-37` and `SKILL.md:1434` document that behavior, which matches pre-consolidation semantics (standalone probe returned 1/3 to the orchestrator). This is not a runtime regression, but the stale plan/acceptance text still claims exit-0-always and omits `skipped-rebase-checkpoint`, which can mislead reviewers and implementers into “fixing” the propagation back to exit 0. **Suggested fix:** Treat propagation as canonical; update the issue plan / `larch:plan` acceptance bullets to document exits `1`/`3`, `LOG_FLUSH_STATUS=skipped-rebase-checkpoint`, and that macro routing consumes `step-7a.sh`’s process exit code—not a wrapper that always returns 0.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_39

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_39: **architecture** `skills/implement/scripts/step-7a.sh:407-414` — Redirecting `rebase-checkpoint-probe.sh` stdout to `$rebase_out` and re-emitting with `emit "$line"` is the correct relay under `larch_quiet_init`, not a regression versus “natural FD 3 inheritance.” After quiet init, the probe child’s `emit`/`emit_kv` calls go to the child’s stdout (because `LARCH_QUIET_PID` is the parent’s PID, not the child’s `$$` per `scripts/lib-quiet.sh:112-117`); without capture, those KVs would land on the parent’s redirected FD 1 (quiet log) and would not reach the orchestrator’s contract stream (FD 3). Re-emission via `emit` routes relayed lines back to FD 3 the same way `scripts/test-lib-quiet.sh:40-45` proves contract output remains visible under command substitution. **Suggested fix:** Keep capture+re-emit; update any remaining plan prose that still claims FD 3 inheritance (the embedded plan in the issue block still says that) so maintainers do not “simplify” this away. Optionally filter re-emission to `KEY=value` lines only if breadcrumb prose on the contract stream is undesirable—today `LARCH_QUIET_BREADCRUMBS=1` without `LARCH_QUIET_BREADCRUMB_FD` will also forward `→ rebase-probe: …` lines, matching direct probe fences.
- **Reviewer**: dyn-quiet-stream-contract-output.txt
- **Concern**: - **architecture** `skills/implement/scripts/step-7a.sh:407-414` — Redirecting `rebase-checkpoint-probe.sh` stdout to `$rebase_out` and re-emitting with `emit "$line"` is the correct relay under `larch_quiet_init`, not a regression versus “natural FD 3 inheritance.” After quiet init, the probe child’s `emit`/`emit_kv` calls go to the child’s stdout (because `LARCH_QUIET_PID` is the parent’s PID, not the child’s `$$` per `scripts/lib-quiet.sh:112-117`); without capture, those KVs would land on the parent’s redirected FD 1 (quiet log) and would not reach the orchestrator’s contract stream (FD 3). Re-emission via `emit` routes relayed lines back to FD 3 the same way `scripts/test-lib-quiet.sh:40-45` proves contract output remains visible under command substitution. **Suggested fix:** Keep capture+re-emit; update any remaining plan prose that still claims FD 3 inheritance (the embedded plan in the issue block still says that) so maintainers do not “simplify” this away. Optionally filter re-emission to `KEY=value` lines only if breadcrumb prose on the contract stream is undesirable—today `LARCH_QUIET_BREADCRUMBS=1` without `LARCH_QUIET_BREADCRUMB_FD` will also forward `→ rebase-probe: …` lines, matching direct probe fences.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_40

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_40: **architecture** `skills/implement/scripts/test-step-7a.sh:486-493` — `quiet-rebase-contract` is the only case that unsets `LARCH_QUIET_DISABLE` (production quiet path via `run_helper_quiet:295-305`), but it still stubs `rebase-checkpoint-probe.sh` with bare `printf` lines (`test-step-7a.sh:161-177`) instead of exercising the real probe’s `emit_kv` + `phantom_probe_with_warn` tail (`PHANTOM_*` keys documented in `scripts/rebase-checkpoint-probe.md:33-33`). The case therefore validates quiet re-emission mechanics for `REBASE_OUTCOME=ok` only, not the full production envelope the Rebase Checkpoint Macro must parse after Step 7a consolidation. **Suggested fix:** Add a harness case (or extend `quiet-rebase-contract`) that invokes the real `scripts/rebase-checkpoint-probe.sh` against the existing `test-rebase-checkpoint-probe.sh` stub tree under quiet mode, and assert `REBASE_OUTCOME`, at least one `PHANTOM_*` line, and ordering (probe KVs before `DIAGRAM_STATUS=` tail) on the captured contract stream.
- **Reviewer**: dyn-quiet-stream-contract-output.txt
- **Concern**: - **architecture** `skills/implement/scripts/test-step-7a.sh:486-493` — `quiet-rebase-contract` is the only case that unsets `LARCH_QUIET_DISABLE` (production quiet path via `run_helper_quiet:295-305`), but it still stubs `rebase-checkpoint-probe.sh` with bare `printf` lines (`test-step-7a.sh:161-177`) instead of exercising the real probe’s `emit_kv` + `phantom_probe_with_warn` tail (`PHANTOM_*` keys documented in `scripts/rebase-checkpoint-probe.md:33-33`). The case therefore validates quiet re-emission mechanics for `REBASE_OUTCOME=ok` only, not the full production envelope the Rebase Checkpoint Macro must parse after Step 7a consolidation. **Suggested fix:** Add a harness case (or extend `quiet-rebase-contract`) that invokes the real `scripts/rebase-checkpoint-probe.sh` against the existing `test-rebase-checkpoint-probe.sh` stub tree under quiet mode, and assert `REBASE_OUTCOME`, at least one `PHANTOM_*` line, and ordering (probe KVs before `DIAGRAM_STATUS=` tail) on the captured contract stream.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_45

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_45: **correctness** `skills/implement/scripts/step-7a.sh:60` — The `*reject*` case-arm matches any `SKIP_REASON` containing the substring `reject`, not only sanitizer failures. Current generator failure tokens (`generation-failed`, `empty-generation`, etc. in `generate-code-flow-diagram.sh:43-84`) do not hit this today, but a future reason like `model-rejected-output` on `STATUS=failed` would suppress upsert while still taking the `failed` branch and appending a Warning—silently diverging from the “post placeholder comment on generation failure” contract. **Suggested fix:** Drop the broad `*reject*` glob; key off `STATUS=skipped` from the diagram generator and/or the closed `REASON_TOKEN` set from `sanitize-mermaid-fragment.sh` instead of substring heuristics.
- **Reviewer**: dyn-sanitizer-rejection-semantics-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/step-7a.sh:60` — The `*reject*` case-arm matches any `SKIP_REASON` containing the substring `reject`, not only sanitizer failures. Current generator failure tokens (`generation-failed`, `empty-generation`, etc. in `generate-code-flow-diagram.sh:43-84`) do not hit this today, but a future reason like `model-rejected-output` on `STATUS=failed` would suppress upsert while still taking the `failed` branch and appending a Warning—silently diverging from the “post placeholder comment on generation failure” contract. **Suggested fix:** Drop the broad `*reject*` glob; key off `STATUS=skipped` from the diagram generator and/or the closed `REASON_TOKEN` set from `sanitize-mermaid-fragment.sh` instead of substring heuristics.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: code-quality: skills/implement/scripts/step-7a.sh:183-198
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Non-zero capture-session-transcript handling appears dead under the documented always-exit-0 contract. Maintainers may assume LOG_FLUSH_STATUS=degraded can trigger from transcript capture when it cannot. Remove the rc check or align helper docs and tests if non-zero exits become possible.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

