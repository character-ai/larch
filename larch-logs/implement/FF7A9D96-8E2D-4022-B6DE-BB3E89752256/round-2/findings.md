### FINDING_1: risk-integration: scripts/test-implement-structure.sh:378-379
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] NEVER #18 structure pin still greps for oos-disposition-gate.sh but SKILL.md now names oos-disposition-checkpoint.sh bash scripts/test-implement-structure.sh fails on the acceptance path even though NEVER #18 semantics were preserved under the new helper Update the grep string (and fail message) to pin oos-disposition-checkpoint.sh; optionally add a separate pin that the checkpoint contract still references oos-disposition-gate.sh
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/implement/scripts/oos-disposition-checkpoint.sh:148-158
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Checkpoint duplicates count_non_security_oos logic already in oos-disposition-gate.sh Future awk/CSV rule changes could be updated in one script and missed in the other, reintroducing precondition vs gate drift Extract shared counting into a small sourced helper used by both scripts
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/implement/scripts/oos-disposition-checkpoint.md:11-17
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Contract omits DESIGN_TMPDIR env fallback present in the script Direct callers omitting --design-tmpdir but exporting DESIGN_TMPDIR get behavior not described in the sibling doc Document DESIGN_TMPDIR fallback in oos-disposition-checkpoint.md
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/implement/scripts/oos-disposition-checkpoint.sh:81-83
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] --help exits 0 while other CLI errors exit 2 with logging Inconsistent CLI contract if an operator or test invokes --help expecting the validation exit family Document exit 0 for --help in the .md or route help through fail_validation if strict uniformity is desired
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: skills/implement/scripts/oos-disposition-checkpoint.sh:184
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Terminal set -e without prior global -e is misleading for maintainers A later line added after the gate block could run under errexit contrary to the tolerant-probe design Remove set -e or comment that only the gate subprocess uses set +e
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] code-quality: scripts/ship-pr.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] ship-pr.sh calls oos-disposition-gate.sh directly outside the new checkpoint Parallel input-resolution paths if ship-pr and Step 8+ diverge Out of scope for this extraction; consider shared checkpoint wiring only if ship-pr inputs match
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] code-quality: scripts/append-tool-failure.sh:100-104
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] append-tool-failure requires output file to exist; execution-issues.md is not created by the checkpoint If the log file were missing, || true would swallow append failure and harness grep assertions would fail silently Pre-existing; checkpoint could : > execution-issues.md like mkitmp if hardening is desired later
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: scripts/test-implement-structure.sh:378-379
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] NEVER #18 structure pin still requires oos-disposition-gate.sh in SKILL.md but the diff retargeted NEVER #18 to oos-disposition-checkpoint.sh test-implement-structure.sh grep fails in CI despite acceptance requiring it to pass Update the pin string (and fail message) to oos-disposition-checkpoint.sh
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: skills/implement/scripts/test-oos-disposition-gate.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No harness asserts origin/main absent yields commit-range HEAD Range fallback bug could pass all new checkpoint tests while production uses wrong range when origin/main is missing Add repo without origin/main; run checkpoint; assert gate stderr commit-range HEAD
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: skills/implement/scripts/test-oos-disposition-gate.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Missing tests for required --implement-tmpdir and unknown CLI args Calling checkpoint without --implement-tmpdir may exit 2 without regression coverage Add assert_rc cases for missing required flag unknown args and bad values with log assertions
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: skills/implement/scripts/test-oos-disposition-gate.sh:645-670
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Exit 1 case does not assert gate stderr log used for append Failure logging could write checkpoint stderr while rc stays 1; FINDING_3 dual-log contract unenforced Require non-empty oos-disposition-gate.stderr.log on disposition gap exit 1
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: skills/implement/SKILL.md:1187 + skills/implement/scripts/oos-disposition-checkpoint.sh:195
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No test for non 0/1/2 checkpoint exits documented in SKILL Unexpected gate rc or 126/127 might log wrong site or exit code without CI detection Add stub or chmod test for passthrough exit and validation-site logging
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: skills/implement/scripts/test-oos-disposition-gate.sh:641-659
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Precondition exit 2 omits checkpoint stderr log assertion Pre-gate fail_validation could stop writing checkpoint stderr while execution-issues still updates Require non-empty oos-disposition-checkpoint.stderr.log like ambiguity case
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: skills/implement/SKILL.md:1191-1202
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No test-implement-structure pin for checkpoint helper name SKILL could drop helper reference without failing structure harness Add assertion in scripts/test-implement-structure.sh for oos-disposition-checkpoint.sh in Step 8+ fence
- **Suggested revision**: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `skills/implement/scripts/oos-disposition-checkpoint.sh:125-128` — `session-id` is embedded into `_oos_ndjson` without rejecting `..` or `/` segments, so a crafted `session-id` could resolve ndjson paths outside `larch-logs/implement/<RUN_ID>/` within or above the implement tmpdir. **Suggested fix:** Reuse the same path-validation pattern as Step 8 main-agent CI-fix (`validate that path is under $IMPLEMENT_TMPDIR`) or constrain `RUN_ID` to `^[A-Za-z0-9_.-]{1,128}$` before path assembly. Pre-existing in the removed inline `SKILL.md` block; not introduced by this extraction.
- **Suggested revision**: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **security** `skills/implement/scripts/oos-disposition-checkpoint.sh:156-158` (also `oos-disposition-gate.sh:150-152`) — The accepted-files loop uses a heredoc fed by `$(printf '%s' "$_oos_accepted_csv" | tr ',' '\n')`, so shell metacharacters in `--design-tmpdir` / path components undergo command substitution when the heredoc is built. **Suggested fix:** Replace command substitution with a here-string or `printf '%s\n' ... | while IFS= read -r` pipe so paths are data-only. Pre-existing pattern carried over 1:1; exploitable only if an untrusted caller supplies CLI path args (harness/CI), not the normal orchestrator path.
- **Suggested revision**: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **security** `skills/implement/scripts/oos-disposition-checkpoint.sh:63-103` — `--implement-tmpdir` and `--design-tmpdir` are not confined to the expected session cache root (contrast with `skills/implement/SKILL.md:1174`, which validates main-agent diagnostic paths stay under `$IMPLEMENT_TMPDIR`). **Suggested fix:** Optionally canonicalize and prefix-check tmpdir arguments against `read-session-env-key` / basename prefix expectations before reads/writes. Pre-existing trust model (session-private tmpdir); not worsened by the helper split.
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 4. **security** `skills/implement/scripts/oos-disposition-checkpoint.sh:108-111` — `FORKED_TARGET` / `REPO_UNAVAILABLE` are taken from `ship-pr-state.sh` without cryptographic binding; any writer to that file in the session tmpdir can force gate skip. **Suggested fix:** Accept only when values are written by `ship-pr.sh` / known writers, or cross-check against `session-env.sh` keys. Inherent to the prior inline design; single-runner / session-tmpdir ownership is the operational control.
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: skills/implement/scripts/oos-disposition-checkpoint.sh:130-137
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Non-empty session-id with missing RUN_ID-keyed ndjson can bind a sole foreign oos-issues.ndjson via find fallback. Gate validates disposition against another run's batch; exit 0 may clear OOS_PENDING and write run-statistics while current-run OOS lacks correct URL/rejection evidence. If RUN_ID is set and the keyed path is missing, fail validation unless the find hit is under larch-logs/implement/$RUN_ID/ (do not accept arbitrary single matches).
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: skills/implement/scripts/test-oos-disposition-gate.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Harness omits stale RUN_ID plus single foreign ndjson discovery. Regression in discovery binding would not be caught by current checkpoint cases. Add a case with non-empty session-id, missing keyed ndjson, one other ndjson dir, and non-security accepted OOS; assert expected exit code and logging.
- **Suggested revision**: Address the concern above.

### FINDING_21: architecture: skills/implement/scripts/oos-disposition-checkpoint.sh:184-195
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Post-gate set -e is unnecessary and could skip logging if gate rc were ever non-numeric. Empty or corrupt _oos_gate_rc could abort at [ -eq ] before append-tool-failure runs. Remove set -e after the gate or normalize non-numeric gate rc to 2 via log_checkpoint_failure before comparisons.
- **Suggested revision**: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] architecture: skills/implement/scripts/oos-disposition-checkpoint.sh:113-123
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Commit range follows process cwd git root, not implement tmpdir. Orchestrator bash cwd outside target repo yields HEAD or wrong range; same as pre-refactor inline fence. Out of scope (unchanged); optional future --repo-root flag if cwd-independent runs are needed.
- **Suggested revision**: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] risk-integration: skills/implement/SKILL.md:1195-1202
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Direct helper invocation requires executable bit; 126 skips checkpoint logging. Lost executable bit yields exit 126 with no Tool Failures row though SKILL describes helper logging. Pre-existing helper pattern; packaging and harness -x check are the mitigation.
- **Suggested revision**: Address the concern above.

### FINDING_24: correctness: skills/implement/scripts/oos-disposition-checkpoint.md:36-37
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Contract omits DESIGN_TMPDIR env fallback present in script and plan. Operator or contributor reads only the .md and assumes design-export wins whenever --design-tmpdir is omitted, even if DESIGN_TMPDIR is exported in the shell. Document env-based design path resolution before design-export fallback.
- **Suggested revision**: Address the concern above.

### FINDING_25: correctness: skills/implement/scripts/oos-disposition-checkpoint.sh:95-99
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Missing --implement-tmpdir logs validation text but not usage() into checkpoint stderr log. Step 8+ failure triage via execution-issues redacted output may lack the full usage line, slowing CLI/setup remediation. Tee or append usage() output to _chk_log before fail_validation on missing required flag.
- **Suggested revision**: Address the concern above.

### FINDING_26: **risk-integration** `scripts/test-implement-structure.sh:377-379` — The branch updates NEVER #18 in `skills/implement/SKILL.md:70` to require a passing `oos-disposition-checkpoint.sh` invocation before clearing `OOS_PENDING`, but the structure pin still greps for the removed literal ``NEVER set `OOS_PENDING=false` without a passing `oos-disposition-gate.sh` invocation``. That pin is part of the acceptance gate (`bash scripts/test-implement-structure.sh` / `bash scripts/relevant-checks.sh`), so the refactor can ship with a broken NEVER #18 regression guard and no automated signal if future edits drop the checkpoint-before-clear contract. **Suggested fix:** Update the grep at `scripts/test-implement-structure.sh:378` to match the new NEVER #18 text (checkpoint helper name), or broaden it to accept either helper while documenting that the orchestrator path is checkpoint-only; optionally add a positive pin that Step 8+ references `oos-disposition-checkpoint.sh`.
- **Reviewer**: dyn-oos-audit-output.txt
- **Concern**: - **risk-integration** `scripts/test-implement-structure.sh:377-379` — The branch updates NEVER #18 in `skills/implement/SKILL.md:70` to require a passing `oos-disposition-checkpoint.sh` invocation before clearing `OOS_PENDING`, but the structure pin still greps for the removed literal ``NEVER set `OOS_PENDING=false` without a passing `oos-disposition-gate.sh` invocation``. That pin is part of the acceptance gate (`bash scripts/test-implement-structure.sh` / `bash scripts/relevant-checks.sh`), so the refactor can ship with a broken NEVER #18 regression guard and no automated signal if future edits drop the checkpoint-before-clear contract. **Suggested fix:** Update the grep at `scripts/test-implement-structure.sh:378` to match the new NEVER #18 text (checkpoint helper name), or broaden it to accept either helper while documenting that the orchestrator path is checkpoint-only; optionally add a positive pin that Step 8+ references `oos-disposition-checkpoint.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] The checkpoint helper at `skills/implement/scripts/oos-disposition-checkpoint.sh:106-195` is a faithful port of the former inline block: same accepted-file CSV, `--filed-urls-file` / `--filed-urls-strict-file` wiring, ndjson discovery/precondition, fork/repo carve-outs, and gate exit-code passthrough (0/1/2). For the OOS-item path, `scripts/ship-pr.sh:1549-1552` sets `OOS_PENDING=true` and exits before its internal gate; `--resume-phase pr-create` (`scripts/ship-pr.sh:3767,3794`) jumps straight to `run_pr_create_phase`, so the checkpoint remains the sole disposition enforcement surface before orchestrator-owned `run-statistics` / `OOS_PENDING=false` clearing — no new bypass was introduced.
- **Reviewer**: dyn-oos-audit-output.txt
- **Concern**: - The checkpoint helper at `skills/implement/scripts/oos-disposition-checkpoint.sh:106-195` is a faithful port of the former inline block: same accepted-file CSV, `--filed-urls-file` / `--filed-urls-strict-file` wiring, ndjson discovery/precondition, fork/repo carve-outs, and gate exit-code passthrough (0/1/2). For the OOS-item path, `scripts/ship-pr.sh:1549-1552` sets `OOS_PENDING=true` and exits before its internal gate; `--resume-phase pr-create` (`scripts/ship-pr.sh:3767,3794`) jumps straight to `run_pr_create_phase`, so the checkpoint remains the sole disposition enforcement surface before orchestrator-owned `run-statistics` / `OOS_PENDING=false` clearing — no new bypass was introduced.
- **Suggested revision**: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] Gate exit 2 now propagates as checkpoint exit 2 (instead of the old inline collapse to orchestrator exit 1), which improves risk integration: validation/setup failures stay distinct from disposition gaps and pre-gate exit-2 paths now get `Tool Failures` logging they previously lacked.
- **Reviewer**: dyn-oos-audit-output.txt
- **Concern**: - Gate exit 2 now propagates as checkpoint exit 2 (instead of the old inline collapse to orchestrator exit 1), which improves risk integration: validation/setup failures stay distinct from disposition gaps and pre-gate exit-2 paths now get `Tool Failures` logging they previously lacked.
- **Suggested revision**: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] Pre-existing dual-path drift remains in `scripts/ship-pr.sh:1002-1054` (`run_oos_disposition_gate_if_required_before_oos_pending_false` omits `--filed-urls-strict-file` and checkpoint-style precondition logging); it is not exercised on the accepted-OOS-item path above and was not changed by this branch.
- **Reviewer**: dyn-oos-audit-output.txt
- **Concern**: - Pre-existing dual-path drift remains in `scripts/ship-pr.sh:1002-1054` (`run_oos_disposition_gate_if_required_before_oos_pending_false` omits `--filed-urls-strict-file` and checkpoint-style precondition logging); it is not exercised on the accepted-OOS-item path above and was not changed by this branch.
- **Suggested revision**: Address the concern above.

### FINDING_30: **architecture** `scripts/test-implement-structure.sh:377-379` — The NEVER #18 structural pin still requires the literal string ``NEVER set `OOS_PENDING=false` without a passing `oos-disposition-gate.sh` invocation``, but `skills/implement/SKILL.md:70` now names `oos-disposition-checkpoint.sh` as the required gate-before-clear entry point. `bash scripts/test-implement-structure.sh` fails on this pin, so the repo’s mechanical enforcement still documents the pre-refactor orchestrator→gate boundary while runtime SKILL text documents the new orchestrator→checkpoint boundary. **Suggested fix:** Update the grep pin (and failure message) to require `oos-disposition-checkpoint.sh`, or pin both checkpoint invocation and the orchestrator-owned post-pass steps (`run-statistics`, `OOS_PENDING=false`, `--resume-phase pr-create`) if you want broader coverage.
- **Reviewer**: dyn-orchestrator-output.txt
- **Concern**: - **architecture** `scripts/test-implement-structure.sh:377-379` — The NEVER #18 structural pin still requires the literal string ``NEVER set `OOS_PENDING=false` without a passing `oos-disposition-gate.sh` invocation``, but `skills/implement/SKILL.md:70` now names `oos-disposition-checkpoint.sh` as the required gate-before-clear entry point. `bash scripts/test-implement-structure.sh` fails on this pin, so the repo’s mechanical enforcement still documents the pre-refactor orchestrator→gate boundary while runtime SKILL text documents the new orchestrator→checkpoint boundary. **Suggested fix:** Update the grep pin (and failure message) to require `oos-disposition-checkpoint.sh`, or pin both checkpoint invocation and the orchestrator-owned post-pass steps (`run-statistics`, `OOS_PENDING=false`, `--resume-phase pr-create`) if you want broader coverage.
- **Suggested revision**: Address the concern above.

### FINDING_31: **architecture** `skills/implement/scripts/oos-disposition-gate.md:35-37` — The **Consumer** section still says the orchestrator calls the gate directly and must `append-tool-failure.sh` on exits 1/2 and hold `OOS_PENDING` / `run-statistics` until resolved. After this branch, Step 8+ logging and the 0/1/2 exit contract live in `oos-disposition-checkpoint.sh` (`skills/implement/scripts/oos-disposition-checkpoint.md:3-8`, `skills/implement/scripts/oos-disposition-checkpoint.sh:19-30`), while `skills/implement/SKILL.md:1187-1202` only invokes the checkpoint and branches on its rc. That split is correct in the new helper, but the gate contract doc still describes the old boundary and can mislead implementers or future refactors back toward orchestrator-side gate logging. **Suggested fix:** Reword `oos-disposition-gate.md` **Consumer** to state the gate is invoked by `oos-disposition-checkpoint.sh`; point orchestrator readers at `oos-disposition-checkpoint.md` for exit codes, logging sites, and the fact that `run-statistics`, `OOS_PENDING` clearing, and `--resume-phase pr-create` remain orchestrator-owned per `skills/implement/SKILL.md:1187-1187`.
- **Reviewer**: dyn-orchestrator-output.txt
- **Concern**: - **architecture** `skills/implement/scripts/oos-disposition-gate.md:35-37` — The **Consumer** section still says the orchestrator calls the gate directly and must `append-tool-failure.sh` on exits 1/2 and hold `OOS_PENDING` / `run-statistics` until resolved. After this branch, Step 8+ logging and the 0/1/2 exit contract live in `oos-disposition-checkpoint.sh` (`skills/implement/scripts/oos-disposition-checkpoint.md:3-8`, `skills/implement/scripts/oos-disposition-checkpoint.sh:19-30`), while `skills/implement/SKILL.md:1187-1202` only invokes the checkpoint and branches on its rc. That split is correct in the new helper, but the gate contract doc still describes the old boundary and can mislead implementers or future refactors back toward orchestrator-side gate logging. **Suggested fix:** Reword `oos-disposition-gate.md` **Consumer** to state the gate is invoked by `oos-disposition-checkpoint.sh`; point orchestrator readers at `oos-disposition-checkpoint.md` for exit codes, logging sites, and the fact that `run-statistics`, `OOS_PENDING` clearing, and `--resume-phase pr-create` remain orchestrator-owned per `skills/implement/SKILL.md:1187-1187`.
- **Suggested revision**: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] **Dual disposition paths (pre-existing, amplified):** `scripts/ship-pr.sh:1002-1055` still embeds a full copy of Step 8+ input plumbing and calls `oos-disposition-gate.sh` directly (without `--filed-urls-strict-file` or the non-security ndjson precondition in `oos-disposition-checkpoint.sh:160-166`, `179-181`), and can clear `OOS_PENDING` at `scripts/ship-pr.sh:1574-1581` without going through the checkpoint. That predates this branch and was explicitly out of plan scope, but it now sits alongside the canonical checkpoint path the orchestrator uses after Step 9a.1.
- **Reviewer**: dyn-orchestrator-output.txt
- **Concern**: - **Dual disposition paths (pre-existing, amplified):** `scripts/ship-pr.sh:1002-1055` still embeds a full copy of Step 8+ input plumbing and calls `oos-disposition-gate.sh` directly (without `--filed-urls-strict-file` or the non-security ndjson precondition in `oos-disposition-checkpoint.sh:160-166`, `179-181`), and can clear `OOS_PENDING` at `scripts/ship-pr.sh:1574-1581` without going through the checkpoint. That predates this branch and was explicitly out of plan scope, but it now sits alongside the canonical checkpoint path the orchestrator uses after Step 9a.1.
- **Suggested revision**: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] **Orchestrator-owned post-pass steps remain prose-only:** On checkpoint exit 0, `run-statistics`, `OOS_PENDING=false`, and `--resume-phase pr-create` are specified only in `skills/implement/SKILL.md:1187` (not in the thin bash fence at `1193-1202`). That matches the prior inline-gate design and is consistent with NEVER #17/#18 intent, but it is still prompt-enforced rather than script-enforced.
- **Reviewer**: dyn-orchestrator-output.txt
- **Concern**: - **Orchestrator-owned post-pass steps remain prose-only:** On checkpoint exit 0, `run-statistics`, `OOS_PENDING=false`, and `--resume-phase pr-create` are specified only in `skills/implement/SKILL.md:1187` (not in the thin bash fence at `1193-1202`). That matches the prior inline-gate design and is consistent with NEVER #17/#18 intent, but it is still prompt-enforced rather than script-enforced.
- **Suggested revision**: Address the concern above.

### FINDING_34: [OUT_OF_SCOPE] **`skills/implement/SKILL.md:605`** still cites `oos-disposition-gate.sh` in the terminal-disposition invariant alongside NEVER #17–18; consider also naming `oos-disposition-checkpoint.sh` as the Step 8+ entry point for consistency with `skills/implement/SKILL.md:68-70`.
- **Reviewer**: dyn-orchestrator-output.txt
- **Concern**: - **`skills/implement/SKILL.md:605`** still cites `oos-disposition-gate.sh` in the terminal-disposition invariant alongside NEVER #17–18; consider also naming `oos-disposition-checkpoint.sh` as the Step 8+ entry point for consistency with `skills/implement/SKILL.md:68-70`.
- **Suggested revision**: Address the concern above.

