### FINDING_18: [OUT_OF_SCOPE] risk-integration: agent-lint.toml
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] OOS disposition harness not in agent-lint sibling inventory. Pre-existing; unrelated to this branch’s new files unless lint scope expands. None required for this PR.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_24: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `skills/implement/scripts/oos-disposition-checkpoint.sh:125-128` — `RUN_ID` is interpolated into `_oos_ndjson` without canonicalization; a tampered `session-id` containing `..` could resolve outside `larch-logs/implement/<run>/` (same as the former inline `SKILL.md` block). **Suggested fix:** If hardening is desired later, validate `session-id` against a narrow charset (as `write-session-env.sh` does for `--token-session-id`) or resolve paths with a root-prefix check before use.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_25: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **security** `skills/implement/scripts/oos-disposition-checkpoint.sh:61-100` — `--implement-tmpdir` and `--design-tmpdir` accept any directory the invoking user can read; a mistaken or malicious caller could point at arbitrary filesystem locations for accepted-OOS / ndjson reads. **Suggested fix:** Document caller-only invocation from `$IMPLEMENT_TMPDIR` (already the `SKILL.md` contract); optional guard to require tmpdir under the session cache root if standalone CLI use becomes a concern. These are pre-existing trust-boundary assumptions, not introduced or materially widened by this refactor.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_34: [OUT_OF_SCOPE] `skills/implement/scripts/test-oos-disposition-gate.sh:604-628` (“checkpoint stale RUN_ID rejects foreign ndjson fallback”) does exercise the inline-vs-checkpoint divergence in case (A): under the removed inline logic the sole `foreign-run/oos-issues.ndjson` with rejection markers would likely yield exit **0**; the harness correctly locks in exit **2**. It does not assert the alternate inline outcome, only the new contract.
- **Reviewer**: dyn-ndjson-discovery-output.txt
- **Concern**: - `skills/implement/scripts/test-oos-disposition-gate.sh:604-628` (“checkpoint stale RUN_ID rejects foreign ndjson fallback”) does exercise the inline-vs-checkpoint divergence in case (A): under the removed inline logic the sole `foreign-run/oos-issues.ndjson` with rejection markers would likely yield exit **0**; the harness correctly locks in exit **2**. It does not assert the alternate inline outcome, only the new contract.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_35: [OUT_OF_SCOPE] `oos-disposition-checkpoint.md` has no dedicated ndjson-discovery subsection (RUN_ID-keyed path vs find-fallback vs precondition); that documentation gap is new on this branch but secondary to the behavioral delta above.
- **Reviewer**: dyn-ndjson-discovery-output.txt
- **Concern**: - `oos-disposition-checkpoint.md` has no dedicated ndjson-discovery subsection (RUN_ID-keyed path vs find-fallback vs precondition); that documentation gap is new on this branch but secondary to the behavioral delta above. **Branch commits (since `main`):** `2108e736f` Extract Step 8+ OOS disposition checkpoint helper; `ebde0c5be` chore larch-logs; `7b65059e7` / `fa991f338` review rounds.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_37: [OUT_OF_SCOPE] **Bash 3.2:** No Bash 4+ constructs (`declare -A`, `mapfile`, namerefs, `${var^^}`) appear in `oos-disposition-checkpoint.sh`; `_gate_extra=()` / `+=` and `${_gate_extra[@]+"${_gate_extra[@]}"}` are Bash 3.2-safe.
- **Reviewer**: dyn-shell-safety-output.txt
- **Concern**: - **Bash 3.2:** No Bash 4+ constructs (`declare -A`, `mapfile`, namerefs, `${var^^}`) appear in `oos-disposition-checkpoint.sh`; `_gate_extra=()` / `+=` and `${_gate_extra[@]+"${_gate_extra[@]}"}` are Bash 3.2-safe.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_38: [OUT_OF_SCOPE] **`set -e` / `set +e`:** The script intentionally avoids global `set -e` for input resolution; only the gate subprocess runs under `set +e` (lines 176–183). `set -e` at line 184 affects only the post-gate `if` chain and `log_checkpoint_failure`; `[ … -eq … ]` tests are `if`-guarded so gate rc 3+ still reach line 195. `log_checkpoint_failure` is not invoked under inherited `set +e` from a parent shell because the helper is executed as a child process.
- **Reviewer**: dyn-shell-safety-output.txt
- **Concern**: - **`set -e` / `set +e`:** The script intentionally avoids global `set -e` for input resolution; only the gate subprocess runs under `set +e` (lines 176–183). `set -e` at line 184 affects only the post-gate `if` chain and `log_checkpoint_failure`; `[ … -eq … ]` tests are `if`-guarded so gate rc 3+ still reach line 195. `log_checkpoint_failure` is not invoked under inherited `set +e` from a parent shell because the helper is executed as a child process.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_39: [OUT_OF_SCOPE] **Ndjson discovery:** The branch tightens find-fallback to `RUN_ID` empty only (lines 130–137), diverging from main’s inline `if [ -z "$_oos_ndjson" ] || [ ! -f "$_oos_ndjson" ]` but matching new harness cases (stale `session-id` → exit 2). That is an intentional behavioral hardening, not a shell-option defect.
- **Reviewer**: dyn-shell-safety-output.txt
- **Concern**: - **Ndjson discovery:** The branch tightens find-fallback to `RUN_ID` empty only (lines 130–137), diverging from main’s inline `if [ -z "$_oos_ndjson" ] || [ ! -f "$_oos_ndjson" ]` but matching new harness cases (stale `session-id` → exit 2). That is an intentional behavioral hardening, not a shell-option defect.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_40: [OUT_OF_SCOPE] **Commits on branch:** `2108e736f` Extract Step 8+ OOS disposition checkpoint helper; `fa991f338` / `7b65059e7` review rounds; plus a run-log flush commit.
- **Reviewer**: dyn-shell-safety-output.txt
- **Concern**: - **Commits on branch:** `2108e736f` Extract Step 8+ OOS disposition checkpoint helper; `fa991f338` / `7b65059e7` review rounds; plus a run-log flush commit.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_8: [OUT_OF_SCOPE] code-quality: skills/implement/scripts/oos-disposition-checkpoint.sh:151-158 / skills/implement/scripts/oos-disposition-gate.sh:26-38
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicated non-security OOS counting between checkpoint precondition and gate. Pre-existing from inline extraction; not amplified beyond prior SKILL fence. Extract shared counter only if repo-wide dedup is undertaken.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_9: [OUT_OF_SCOPE] code-quality: skills/implement/scripts/step-7a.sh:41-52 / skills/implement/scripts/oos-disposition-checkpoint.sh:19-30
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] log_checkpoint_failure duplicates step-7a append_failure pattern. Pre-existing sibling-script duplication; not introduced by this branch. Introduce shared append helper only if multiple implement scripts adopt it.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

