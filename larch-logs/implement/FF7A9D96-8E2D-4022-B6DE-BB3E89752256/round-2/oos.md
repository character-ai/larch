### FINDING_15: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `skills/implement/scripts/oos-disposition-checkpoint.sh:125-128` — `session-id` is embedded into `_oos_ndjson` without rejecting `..` or `/` segments, so a crafted `session-id` could resolve ndjson paths outside `larch-logs/implement/<RUN_ID>/` within or above the implement tmpdir. **Suggested fix:** Reuse the same path-validation pattern as Step 8 main-agent CI-fix (`validate that path is under $IMPLEMENT_TMPDIR`) or constrain `RUN_ID` to `^[A-Za-z0-9_.-]{1,128}$` before path assembly. Pre-existing in the removed inline `SKILL.md` block; not introduced by this extraction.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_16: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **security** `skills/implement/scripts/oos-disposition-checkpoint.sh:156-158` (also `oos-disposition-gate.sh:150-152`) — The accepted-files loop uses a heredoc fed by `$(printf '%s' "$_oos_accepted_csv" | tr ',' '\n')`, so shell metacharacters in `--design-tmpdir` / path components undergo command substitution when the heredoc is built. **Suggested fix:** Replace command substitution with a here-string or `printf '%s\n' ... | while IFS= read -r` pipe so paths are data-only. Pre-existing pattern carried over 1:1; exploitable only if an untrusted caller supplies CLI path args (harness/CI), not the normal orchestrator path.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_17: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **security** `skills/implement/scripts/oos-disposition-checkpoint.sh:63-103` — `--implement-tmpdir` and `--design-tmpdir` are not confined to the expected session cache root (contrast with `skills/implement/SKILL.md:1174`, which validates main-agent diagnostic paths stay under `$IMPLEMENT_TMPDIR`). **Suggested fix:** Optionally canonicalize and prefix-check tmpdir arguments against `read-session-env-key` / basename prefix expectations before reads/writes. Pre-existing trust model (session-private tmpdir); not worsened by the helper split.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_18: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 4. **security** `skills/implement/scripts/oos-disposition-checkpoint.sh:108-111` — `FORKED_TARGET` / `REPO_UNAVAILABLE` are taken from `ship-pr-state.sh` without cryptographic binding; any writer to that file in the session tmpdir can force gate skip. **Suggested fix:** Accept only when values are written by `ship-pr.sh` / known writers, or cross-check against `session-env.sh` keys. Inherent to the prior inline design; single-runner / session-tmpdir ownership is the operational control.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_22: [OUT_OF_SCOPE] architecture: skills/implement/scripts/oos-disposition-checkpoint.sh:113-123
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Commit range follows process cwd git root, not implement tmpdir. Orchestrator bash cwd outside target repo yields HEAD or wrong range; same as pre-refactor inline fence. Out of scope (unchanged); optional future --repo-root flag if cwd-independent runs are needed.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_23: [OUT_OF_SCOPE] risk-integration: skills/implement/SKILL.md:1195-1202
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Direct helper invocation requires executable bit; 126 skips checkpoint logging. Lost executable bit yields exit 126 with no Tool Failures row though SKILL describes helper logging. Pre-existing helper pattern; packaging and harness -x check are the mitigation.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_27: [OUT_OF_SCOPE] The checkpoint helper at `skills/implement/scripts/oos-disposition-checkpoint.sh:106-195` is a faithful port of the former inline block: same accepted-file CSV, `--filed-urls-file` / `--filed-urls-strict-file` wiring, ndjson discovery/precondition, fork/repo carve-outs, and gate exit-code passthrough (0/1/2). For the OOS-item path, `scripts/ship-pr.sh:1549-1552` sets `OOS_PENDING=true` and exits before its internal gate; `--resume-phase pr-create` (`scripts/ship-pr.sh:3767,3794`) jumps straight to `run_pr_create_phase`, so the checkpoint remains the sole disposition enforcement surface before orchestrator-owned `run-statistics` / `OOS_PENDING=false` clearing — no new bypass was introduced.
- **Reviewer**: dyn-oos-audit-output.txt
- **Concern**: - The checkpoint helper at `skills/implement/scripts/oos-disposition-checkpoint.sh:106-195` is a faithful port of the former inline block: same accepted-file CSV, `--filed-urls-file` / `--filed-urls-strict-file` wiring, ndjson discovery/precondition, fork/repo carve-outs, and gate exit-code passthrough (0/1/2). For the OOS-item path, `scripts/ship-pr.sh:1549-1552` sets `OOS_PENDING=true` and exits before its internal gate; `--resume-phase pr-create` (`scripts/ship-pr.sh:3767,3794`) jumps straight to `run_pr_create_phase`, so the checkpoint remains the sole disposition enforcement surface before orchestrator-owned `run-statistics` / `OOS_PENDING=false` clearing — no new bypass was introduced.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_28: [OUT_OF_SCOPE] Gate exit 2 now propagates as checkpoint exit 2 (instead of the old inline collapse to orchestrator exit 1), which improves risk integration: validation/setup failures stay distinct from disposition gaps and pre-gate exit-2 paths now get `Tool Failures` logging they previously lacked.
- **Reviewer**: dyn-oos-audit-output.txt
- **Concern**: - Gate exit 2 now propagates as checkpoint exit 2 (instead of the old inline collapse to orchestrator exit 1), which improves risk integration: validation/setup failures stay distinct from disposition gaps and pre-gate exit-2 paths now get `Tool Failures` logging they previously lacked.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_29: [OUT_OF_SCOPE] Pre-existing dual-path drift remains in `scripts/ship-pr.sh:1002-1054` (`run_oos_disposition_gate_if_required_before_oos_pending_false` omits `--filed-urls-strict-file` and checkpoint-style precondition logging); it is not exercised on the accepted-OOS-item path above and was not changed by this branch.
- **Reviewer**: dyn-oos-audit-output.txt
- **Concern**: - Pre-existing dual-path drift remains in `scripts/ship-pr.sh:1002-1054` (`run_oos_disposition_gate_if_required_before_oos_pending_false` omits `--filed-urls-strict-file` and checkpoint-style precondition logging); it is not exercised on the accepted-OOS-item path above and was not changed by this branch.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_32: [OUT_OF_SCOPE] **Dual disposition paths (pre-existing, amplified):** `scripts/ship-pr.sh:1002-1055` still embeds a full copy of Step 8+ input plumbing and calls `oos-disposition-gate.sh` directly (without `--filed-urls-strict-file` or the non-security ndjson precondition in `oos-disposition-checkpoint.sh:160-166`, `179-181`), and can clear `OOS_PENDING` at `scripts/ship-pr.sh:1574-1581` without going through the checkpoint. That predates this branch and was explicitly out of plan scope, but it now sits alongside the canonical checkpoint path the orchestrator uses after Step 9a.1.
- **Reviewer**: dyn-orchestrator-output.txt
- **Concern**: - **Dual disposition paths (pre-existing, amplified):** `scripts/ship-pr.sh:1002-1055` still embeds a full copy of Step 8+ input plumbing and calls `oos-disposition-gate.sh` directly (without `--filed-urls-strict-file` or the non-security ndjson precondition in `oos-disposition-checkpoint.sh:160-166`, `179-181`), and can clear `OOS_PENDING` at `scripts/ship-pr.sh:1574-1581` without going through the checkpoint. That predates this branch and was explicitly out of plan scope, but it now sits alongside the canonical checkpoint path the orchestrator uses after Step 9a.1.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_33: [OUT_OF_SCOPE] **Orchestrator-owned post-pass steps remain prose-only:** On checkpoint exit 0, `run-statistics`, `OOS_PENDING=false`, and `--resume-phase pr-create` are specified only in `skills/implement/SKILL.md:1187` (not in the thin bash fence at `1193-1202`). That matches the prior inline-gate design and is consistent with NEVER #17/#18 intent, but it is still prompt-enforced rather than script-enforced.
- **Reviewer**: dyn-orchestrator-output.txt
- **Concern**: - **Orchestrator-owned post-pass steps remain prose-only:** On checkpoint exit 0, `run-statistics`, `OOS_PENDING=false`, and `--resume-phase pr-create` are specified only in `skills/implement/SKILL.md:1187` (not in the thin bash fence at `1193-1202`). That matches the prior inline-gate design and is consistent with NEVER #17/#18 intent, but it is still prompt-enforced rather than script-enforced.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_34: [OUT_OF_SCOPE] **`skills/implement/SKILL.md:605`** still cites `oos-disposition-gate.sh` in the terminal-disposition invariant alongside NEVER #17–18; consider also naming `oos-disposition-checkpoint.sh` as the Step 8+ entry point for consistency with `skills/implement/SKILL.md:68-70`.
- **Reviewer**: dyn-orchestrator-output.txt
- **Concern**: - **`skills/implement/SKILL.md:605`** still cites `oos-disposition-gate.sh` in the terminal-disposition invariant alongside NEVER #17–18; consider also naming `oos-disposition-checkpoint.sh` as the Step 8+ entry point for consistency with `skills/implement/SKILL.md:68-70`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_6: [OUT_OF_SCOPE] code-quality: scripts/ship-pr.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] ship-pr.sh calls oos-disposition-gate.sh directly outside the new checkpoint Parallel input-resolution paths if ship-pr and Step 8+ diverge Out of scope for this extraction; consider shared checkpoint wiring only if ship-pr inputs match
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_7: [OUT_OF_SCOPE] code-quality: scripts/append-tool-failure.sh:100-104
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] append-tool-failure requires output file to exist; execution-issues.md is not created by the checkpoint If the log file were missing, || true would swallow append failure and harness grep assertions would fail silently Pre-existing; checkpoint could : > execution-issues.md like mkitmp if hardening is desired later
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

