### FINDING_1: risk-integration: scripts/test-implement-structure.sh:378-379
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] NEVER #18 structure pin still greps for oos-disposition-gate.sh but SKILL.md now names oos-disposition-checkpoint.sh bash scripts/test-implement-structure.sh fails on the acceptance path even though NEVER #18 semantics were preserved under the new helper Update the grep string (and fail message) to pin oos-disposition-checkpoint.sh; optionally add a separate pin that the checkpoint contract still references oos-disposition-gate.sh
- **Suggested revision**: Address the concern above.


### FINDING_11: risk-integration: skills/implement/scripts/test-oos-disposition-gate.sh:645-670
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Exit 1 case does not assert gate stderr log used for append Failure logging could write checkpoint stderr while rc stays 1; FINDING_3 dual-log contract unenforced Require non-empty oos-disposition-gate.stderr.log on disposition gap exit 1
- **Suggested revision**: Address the concern above.


### FINDING_13: risk-integration: skills/implement/scripts/test-oos-disposition-gate.sh:641-659
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Precondition exit 2 omits checkpoint stderr log assertion Pre-gate fail_validation could stop writing checkpoint stderr while execution-issues still updates Require non-empty oos-disposition-checkpoint.stderr.log like ambiguity case
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: skills/implement/SKILL.md:1191-1202
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No test-implement-structure pin for checkpoint helper name SKILL could drop helper reference without failing structure harness Add assertion in scripts/test-implement-structure.sh for oos-disposition-checkpoint.sh in Step 8+ fence
- **Suggested revision**: Address the concern above.


### FINDING_19: correctness: skills/implement/scripts/oos-disposition-checkpoint.sh:130-137
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Non-empty session-id with missing RUN_ID-keyed ndjson can bind a sole foreign oos-issues.ndjson via find fallback. Gate validates disposition against another run's batch; exit 0 may clear OOS_PENDING and write run-statistics while current-run OOS lacks correct URL/rejection evidence. If RUN_ID is set and the keyed path is missing, fail validation unless the find hit is under larch-logs/implement/$RUN_ID/ (do not accept arbitrary single matches).
- **Suggested revision**: Address the concern above.


### FINDING_20: risk-integration: skills/implement/scripts/test-oos-disposition-gate.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Harness omits stale RUN_ID plus single foreign ndjson discovery. Regression in discovery binding would not be caught by current checkpoint cases. Add a case with non-empty session-id, missing keyed ndjson, one other ndjson dir, and non-security accepted OOS; assert expected exit code and logging.
- **Suggested revision**: Address the concern above.


### FINDING_24: correctness: skills/implement/scripts/oos-disposition-checkpoint.md:36-37
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Contract omits DESIGN_TMPDIR env fallback present in script and plan. Operator or contributor reads only the .md and assumes design-export wins whenever --design-tmpdir is omitted, even if DESIGN_TMPDIR is exported in the shell. Document env-based design path resolution before design-export fallback.
- **Suggested revision**: Address the concern above.


### FINDING_26: **risk-integration** `scripts/test-implement-structure.sh:377-379` — The branch updates NEVER #18 in `skills/implement/SKILL.md:70` to require a passing `oos-disposition-checkpoint.sh` invocation before clearing `OOS_PENDING`, but the structure pin still greps for the removed literal ``NEVER set `OOS_PENDING=false` without a passing `oos-disposition-gate.sh` invocation``. That pin is part of the acceptance gate (`bash scripts/test-implement-structure.sh` / `bash scripts/relevant-checks.sh`), so the refactor can ship with a broken NEVER #18 regression guard and no automated signal if future edits drop the checkpoint-before-clear contract. **Suggested fix:** Update the grep at `scripts/test-implement-structure.sh:378` to match the new NEVER #18 text (checkpoint helper name), or broaden it to accept either helper while documenting that the orchestrator path is checkpoint-only; optionally add a positive pin that Step 8+ references `oos-disposition-checkpoint.sh`.
- **Reviewer**: dyn-oos-audit-output.txt
- **Concern**: - **risk-integration** `scripts/test-implement-structure.sh:377-379` — The branch updates NEVER #18 in `skills/implement/SKILL.md:70` to require a passing `oos-disposition-checkpoint.sh` invocation before clearing `OOS_PENDING`, but the structure pin still greps for the removed literal ``NEVER set `OOS_PENDING=false` without a passing `oos-disposition-gate.sh` invocation``. That pin is part of the acceptance gate (`bash scripts/test-implement-structure.sh` / `bash scripts/relevant-checks.sh`), so the refactor can ship with a broken NEVER #18 regression guard and no automated signal if future edits drop the checkpoint-before-clear contract. **Suggested fix:** Update the grep at `scripts/test-implement-structure.sh:378` to match the new NEVER #18 text (checkpoint helper name), or broaden it to accept either helper while documenting that the orchestrator path is checkpoint-only; optionally add a positive pin that Step 8+ references `oos-disposition-checkpoint.sh`.
- **Suggested revision**: Address the concern above.


### FINDING_3: code-quality: skills/implement/scripts/oos-disposition-checkpoint.md:11-17
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Contract omits DESIGN_TMPDIR env fallback present in the script Direct callers omitting --design-tmpdir but exporting DESIGN_TMPDIR get behavior not described in the sibling doc Document DESIGN_TMPDIR fallback in oos-disposition-checkpoint.md
- **Suggested revision**: Address the concern above.


### FINDING_30: **architecture** `scripts/test-implement-structure.sh:377-379` — The NEVER #18 structural pin still requires the literal string ``NEVER set `OOS_PENDING=false` without a passing `oos-disposition-gate.sh` invocation``, but `skills/implement/SKILL.md:70` now names `oos-disposition-checkpoint.sh` as the required gate-before-clear entry point. `bash scripts/test-implement-structure.sh` fails on this pin, so the repo’s mechanical enforcement still documents the pre-refactor orchestrator→gate boundary while runtime SKILL text documents the new orchestrator→checkpoint boundary. **Suggested fix:** Update the grep pin (and failure message) to require `oos-disposition-checkpoint.sh`, or pin both checkpoint invocation and the orchestrator-owned post-pass steps (`run-statistics`, `OOS_PENDING=false`, `--resume-phase pr-create`) if you want broader coverage.
- **Reviewer**: dyn-orchestrator-output.txt
- **Concern**: - **architecture** `scripts/test-implement-structure.sh:377-379` — The NEVER #18 structural pin still requires the literal string ``NEVER set `OOS_PENDING=false` without a passing `oos-disposition-gate.sh` invocation``, but `skills/implement/SKILL.md:70` now names `oos-disposition-checkpoint.sh` as the required gate-before-clear entry point. `bash scripts/test-implement-structure.sh` fails on this pin, so the repo’s mechanical enforcement still documents the pre-refactor orchestrator→gate boundary while runtime SKILL text documents the new orchestrator→checkpoint boundary. **Suggested fix:** Update the grep pin (and failure message) to require `oos-disposition-checkpoint.sh`, or pin both checkpoint invocation and the orchestrator-owned post-pass steps (`run-statistics`, `OOS_PENDING=false`, `--resume-phase pr-create`) if you want broader coverage.
- **Suggested revision**: Address the concern above.


### FINDING_31: **architecture** `skills/implement/scripts/oos-disposition-gate.md:35-37` — The **Consumer** section still says the orchestrator calls the gate directly and must `append-tool-failure.sh` on exits 1/2 and hold `OOS_PENDING` / `run-statistics` until resolved. After this branch, Step 8+ logging and the 0/1/2 exit contract live in `oos-disposition-checkpoint.sh` (`skills/implement/scripts/oos-disposition-checkpoint.md:3-8`, `skills/implement/scripts/oos-disposition-checkpoint.sh:19-30`), while `skills/implement/SKILL.md:1187-1202` only invokes the checkpoint and branches on its rc. That split is correct in the new helper, but the gate contract doc still describes the old boundary and can mislead implementers or future refactors back toward orchestrator-side gate logging. **Suggested fix:** Reword `oos-disposition-gate.md` **Consumer** to state the gate is invoked by `oos-disposition-checkpoint.sh`; point orchestrator readers at `oos-disposition-checkpoint.md` for exit codes, logging sites, and the fact that `run-statistics`, `OOS_PENDING` clearing, and `--resume-phase pr-create` remain orchestrator-owned per `skills/implement/SKILL.md:1187-1187`.
- **Reviewer**: dyn-orchestrator-output.txt
- **Concern**: - **architecture** `skills/implement/scripts/oos-disposition-gate.md:35-37` — The **Consumer** section still says the orchestrator calls the gate directly and must `append-tool-failure.sh` on exits 1/2 and hold `OOS_PENDING` / `run-statistics` until resolved. After this branch, Step 8+ logging and the 0/1/2 exit contract live in `oos-disposition-checkpoint.sh` (`skills/implement/scripts/oos-disposition-checkpoint.md:3-8`, `skills/implement/scripts/oos-disposition-checkpoint.sh:19-30`), while `skills/implement/SKILL.md:1187-1202` only invokes the checkpoint and branches on its rc. That split is correct in the new helper, but the gate contract doc still describes the old boundary and can mislead implementers or future refactors back toward orchestrator-side gate logging. **Suggested fix:** Reword `oos-disposition-gate.md` **Consumer** to state the gate is invoked by `oos-disposition-checkpoint.sh`; point orchestrator readers at `oos-disposition-checkpoint.md` for exit codes, logging sites, and the fact that `run-statistics`, `OOS_PENDING` clearing, and `--resume-phase pr-create` remain orchestrator-owned per `skills/implement/SKILL.md:1187-1187`.
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: scripts/test-implement-structure.sh:378-379
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] NEVER #18 structure pin still requires oos-disposition-gate.sh in SKILL.md but the diff retargeted NEVER #18 to oos-disposition-checkpoint.sh test-implement-structure.sh grep fails in CI despite acceptance requiring it to pass Update the pin string (and fail message) to oos-disposition-checkpoint.sh
- **Suggested revision**: Address the concern above.


### FINDING_9: risk-integration: skills/implement/scripts/test-oos-disposition-gate.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No harness asserts origin/main absent yields commit-range HEAD Range fallback bug could pass all new checkpoint tests while production uses wrong range when origin/main is missing Add repo without origin/main; run checkpoint; assert gate stderr commit-range HEAD
- **Suggested revision**: Address the concern above.


