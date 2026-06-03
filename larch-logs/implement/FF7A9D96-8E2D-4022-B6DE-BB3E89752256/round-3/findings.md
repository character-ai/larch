### FINDING_1: code-quality: skills/implement/scripts/oos-disposition-checkpoint.md:16-22
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Contract doc omits ndjson discovery semantics including round-2 stale-RUN_ID no-fallback rule. A maintainer restores inline find-when-keyed-path-missing behavior believing the doc is complete; foreign ndjson could bind again or tests/harness drift from runtime. Add Ndjson discovery subsection documenting RUN_ID-keyed path find-only-when-session-id-empty ambiguity precondition and stale-RUN_ID exit 2.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/implement/scripts/oos-disposition-checkpoint.sh:125-138
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Find fallback gated on empty RUN_ID diverges from removed inline block that find-fallbacks whenever keyed ndjson path is missing. Present session-id with missing keyed file plus exactly one foreign ndjson: inline would bind foreign file; checkpoint exits 2 via precondition (harness stale RUN_ID case). Document intentional tightening in checkpoint.md or restore inline-equivalent find if byte parity is required.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/implement/scripts/oos-disposition-checkpoint.sh:130
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Redundant compound condition in find branch when RUN_ID is empty. Readability noise; future edits may misread which branch is load-bearing. Collapse to if [ -z "$_RUN_ID" ]; then before find.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/implement/scripts/oos-disposition-checkpoint.sh:33-51,72-76
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] prescan_implement_tmpdir adds complexity for rare CLI ordering edge case. Extra code path to maintain; prescan only handles first --implement-tmpdir in argv. Log validation failures without prescan when IMPLEMENT_TMPDIR unknown unless ordering edge case is production-proven.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: skills/implement/scripts/oos-disposition-checkpoint.sh:184
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Stray set -e after gate with no script-wide set -e. Misleading for readers expecting errexit semantics outside the gate subprocess. Remove set -e or comment it as intentional no-op after set +e gate wrapper.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: skills/implement/scripts/test-oos-disposition-gate.md:11-21
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Harness md case list incomplete vs actual checkpoint tests. Contributors rely on md for coverage; missing stale RUN_ID origin/main-absent and design-export cases. Enumerate all checkpoint cases present in test-oos-disposition-gate.sh.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: skills/implement/scripts/test-oos-disposition-gate.sh:485-874
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] 872-line harness mixes gate and checkpoint fixtures. Harder to navigate and extend; risk of accidental coupling between unrelated cases. Keep single Makefile target; optionally source checkpoint cases from a fragment if file grows further.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] code-quality: skills/implement/scripts/oos-disposition-checkpoint.sh:151-158 / skills/implement/scripts/oos-disposition-gate.sh:26-38
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicated non-security OOS counting between checkpoint precondition and gate. Pre-existing from inline extraction; not amplified beyond prior SKILL fence. Extract shared counter only if repo-wide dedup is undertaken.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] code-quality: skills/implement/scripts/step-7a.sh:41-52 / skills/implement/scripts/oos-disposition-checkpoint.sh:19-30
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] log_checkpoint_failure duplicates step-7a append_failure pattern. Pre-existing sibling-script duplication; not introduced by this branch. Introduce shared append helper only if multiple implement scripts adopt it.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: skills/implement/scripts/oos-disposition-checkpoint.sh:125-138
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Ndjson find fallback is skipped when session-id is set, unlike main inline block. Stale RUN_ID run-missing plus sole foreign-run/oos-issues.ndjson: old find binds foreign ndjson and gate may exit 0; new exits 2 via precondition. Document intentional rule or restore inline find when keyed path missing if 1:1 port is required.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: skills/implement/scripts/oos-disposition-checkpoint.md:16-22
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Contract omits ndjson discovery (RUN_ID-keyed vs find-only-without-session-id). Operators/readers infer 1:1 from former inline; miss stale-RUN_ID behavior. Add Ndjson discovery subsection matching script lines 125-138.
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: skills/implement/scripts/test-oos-disposition-gate.sh:538-539
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Disposition-gap grep uses substring step-8-oos-checkpoint. If negative validation grep is removed, validation-site log lines can false-pass disposition-gap assertion. Grep exact site token or Step step-8-oos-checkpoint — anchor.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: skills/implement/scripts/oos-disposition-checkpoint.sh:130-138
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Find fallback runs only when RUN_ID is empty; inline ran find whenever keyed ndjson path was missing. Stale session-id with one foreign oos-issues.ndjson: inline could pass; helper exits 2 at precondition and blocks OOS_PENDING clear. Restore inline find when keyed path missing or document intentional tightening and add explicit harness for both behaviors.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: skills/implement/scripts/test-oos-disposition-gate.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No test for former inline path: RUN_ID set, keyed ndjson missing, sole foreign ndjson discoverable. Regression reintroducing find-with-RUN_ID would ship without harness signal. Add positive keyed-path case and keep stale-RUN_ID as negative guard.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: skills/implement/scripts/oos-disposition-checkpoint.sh:140
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Exported DESIGN_TMPDIR resolution is untested. Env-only DESIGN_TMPDIR could drift from --design-tmpdir without CI failure. Add harness case with export DESIGN_TMPDIR and no CLI flag.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: skills/implement/scripts/test-oos-disposition-gate.sh:538-539
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Disposition-gap log grep uses substring that matches validation site name. False pass if logging format embeds both site tokens on one line. Use anchored grep on append header e.g. Step step-8-oos-checkpoint —.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: skills/implement/scripts/oos-disposition-checkpoint.md:16-22
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Contract omits ndjson discovery semantics now encoded in script and tests. Operators/readers rely on code or tests for RUN_ID vs find rules. Document ndjson discovery in checkpoint.md.
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] risk-integration: agent-lint.toml
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] OOS disposition harness not in agent-lint sibling inventory. Pre-existing; unrelated to this branch’s new files unless lint scope expands. None required for this PR.
- **Suggested revision**: Address the concern above.

### FINDING_19: **Command injection:** Gate args use quoted expansions; `_oos_range` is derived from `git merge-base` / fixed literals (`HEAD`, `origin/main..HEAD`), not from session file contents. `git log --format=%B "$range"` in the gate keeps the range as a single operand (pre-existing gate behavior).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Command injection:** Gate args use quoted expansions; `_oos_range` is derived from `git merge-base` / fixed literals (`HEAD`, `origin/main..HEAD`), not from session file contents. `git log --format=%B "$range"` in the gate keeps the range as a single operand (pre-existing gate behavior).
- **Suggested revision**: Address the concern above.

### FINDING_20: **Path handling:** `find` is rooted at `$IMPLEMENT_TMPDIR/larch-logs/implement` with `-mindepth 2 -maxdepth 2`. `RUN_ID` comes from `session-id` (typically `uuidgen`); path segments are not validated, but that matches the removed inline block and normal IDs do not contain `/` or `..`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Path handling:** `find` is rooted at `$IMPLEMENT_TMPDIR/larch-logs/implement` with `-mindepth 2 -maxdepth 2`. `RUN_ID` comes from `session-id` (typically `uuidgen`); path segments are not validated, but that matches the removed inline block and normal IDs do not contain `/` or `..`.
- **Suggested revision**: Address the concern above.

### FINDING_21: **AuthZ / bypass:** Fork / `REPO_UNAVAILABLE` skips still come from `ship-pr-state.sh` grep — same trust as before. Non-zero exits still block `OOS_PENDING` clear in `SKILL.md`; gate exit `2` now propagates instead of being collapsed to `1` (fail-closed for validation vs disposition gap).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **AuthZ / bypass:** Fork / `REPO_UNAVAILABLE` skips still come from `ship-pr-state.sh` grep — same trust as before. Non-zero exits still block `OOS_PENDING` clear in `SKILL.md`; gate exit `2` now propagates instead of being collapsed to `1` (fail-closed for validation vs disposition gap).
- **Suggested revision**: Address the concern above.

### FINDING_22: **Secrets:** Failures go through `append-tool-failure.sh` with `--redact`; checkpoint uses `|| true` on append so logging cannot override the saved exit code.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Secrets:** Failures go through `append-tool-failure.sh` with `--redact`; checkpoint uses `|| true` on append so logging cannot override the saved exit code.
- **Suggested revision**: Address the concern above.

### FINDING_23: **Ndjson binding:** When `session-id` is set but the keyed ndjson is missing, find-fallback no longer runs (harness “stale RUN_ID” case). That closes a prior confused-deputy where a sole foreign ndjson could satisfy disposition — a correctness hardening, not a regression.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Ndjson binding:** When `session-id` is set but the keyed ndjson is missing, find-fallback no longer runs (harness “stale RUN_ID” case). That closes a prior confused-deputy where a sole foreign ndjson could satisfy disposition — a correctness hardening, not a regression.
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `skills/implement/scripts/oos-disposition-checkpoint.sh:125-128` — `RUN_ID` is interpolated into `_oos_ndjson` without canonicalization; a tampered `session-id` containing `..` could resolve outside `larch-logs/implement/<run>/` (same as the former inline `SKILL.md` block). **Suggested fix:** If hardening is desired later, validate `session-id` against a narrow charset (as `write-session-env.sh` does for `--token-session-id`) or resolve paths with a root-prefix check before use.
- **Suggested revision**: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **security** `skills/implement/scripts/oos-disposition-checkpoint.sh:61-100` — `--implement-tmpdir` and `--design-tmpdir` accept any directory the invoking user can read; a mistaken or malicious caller could point at arbitrary filesystem locations for accepted-OOS / ndjson reads. **Suggested fix:** Document caller-only invocation from `$IMPLEMENT_TMPDIR` (already the `SKILL.md` contract); optional guard to require tmpdir under the session cache root if standalone CLI use becomes a concern. These are pre-existing trust-boundary assumptions, not introduced or materially widened by this refactor.
- **Suggested revision**: Address the concern above.

### FINDING_26: risk-integration: skills/implement/SKILL.md:1187,1196-1202
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] SKILL promises 126/127 and other non-0/1/2 checkpoint failures are logged under step-8-oos-checkpoint-validation, but direct executable invocation can fail before the helper runs. Missing +x or unset CLAUDE_PLUGIN_ROOT yields 126/127 with no Tool Failures row; OOS_PENDING stays set and Step 8+ stops without the documented audit entry. Invoke via bash on the script path and/or add orchestrator-side append-tool-failure for 126/127 when no checkpoint log line exists; align SKILL prose.
- **Suggested revision**: Address the concern above.

### FINDING_27: risk-integration: skills/implement/scripts/oos-disposition-checkpoint.sh:125-138
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Find fallback for oos-issues.ndjson is disabled whenever session-id is non-empty, unlike the removed inline block that re-discovered when the keyed file was missing. Stale session-id with one valid ndjson under another run dir now exits 2 (precondition) instead of adopting the sole file; run stalls until session-id or paths are repaired manually. Document RUN_ID-keyed-only semantics in checkpoint.md/SKILL; optionally restore single-candidate find when keyed path is missing only.
- **Suggested revision**: Address the concern above.

### FINDING_28: code-quality: skills/implement/scripts/oos-disposition-checkpoint.md:48-50
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] checkpoint.md still states wiring matches the former inline block after ndjson discovery changed in round 2. Future edits may re-port inline find-when-keyed-missing behavior believing docs. Add Ndjson resolution subsection and qualify or remove the matches-inline claim.
- **Suggested revision**: Address the concern above.

### FINDING_29: correctness: skills/implement/scripts/test-oos-disposition-gate.sh:546-548
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Disposition-gap log grep uses a substring that also appears inside step-8-oos-checkpoint-validation. Polluted execution-issues.md with both site strings could false-pass the exit-1 logging test. Grep the full Step header for the checkpoint site only, not a bare substring.
- **Suggested revision**: Address the concern above.

### FINDING_30: correctness: skills/implement/scripts/oos-disposition-checkpoint.sh:130-138
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Find fallback gated on empty RUN_ID breaks 1:1 inline ndjson discovery. session-id points at missing path but one other oos-issues.ndjson exists with valid rejection data: inline could pass checkpoint; helper exits 2 and blocks OOS_PENDING clear. Restore inline find-when-keyed-path-missing logic (keep ambiguity exit 2 only for empty RUN_ID + multiple matches) or update plan/docs/tests to codify intentional stale-RUN_ID strictness.
- **Suggested revision**: Address the concern above.

### FINDING_31: correctness: skills/implement/scripts/oos-disposition-checkpoint.md:48-50
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Gate contract claims wiring still matches former inline block after ndjson behavior change. Readers assume inline-equivalent discovery; mis-triage checkpoint exit 2 vs disposition gap. Document ndjson discovery rules explicitly; qualify or remove matches-inline claim.
- **Suggested revision**: Address the concern above.

### FINDING_32: correctness: skills/implement/scripts/test-oos-disposition-gate.md:20
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Merge-base case doc says proceeds but harness expects exit 1. Misleading harness sibling doc during maintenance. Say range is origin/main..HEAD with disposition-gap exit 1 in harness.
- **Suggested revision**: Address the concern above.

### FINDING_33: **correctness** `skills/implement/scripts/oos-disposition-checkpoint.sh:125-138` — Ndjson `find` fallback is gated on `[ -z "$_RUN_ID" ]`, but the removed inline block in `skills/implement/SKILL.md` (diff hunk ~171–184) used `if [ -z "$_oos_ndjson" ] || [ ! -f "$_oos_ndjson" ]` with no `RUN_ID` guard, so whenever `session-id` is non-empty and the RUN_ID-keyed file is missing, behavior diverges. **Divergent cases:** (A) `RUN_ID` set, keyed path missing, exactly one other `oos-issues.ndjson` under `larch-logs/implement/` — inline runs `find`, adopts that file, and can pass the gate (e.g. rejection markers in the foreign batch); checkpoint skips `find`, leaves a non-existent keyed path, and with `non_security_oos > 0` hits the precondition at `oos-disposition-checkpoint.sh:160-164` → exit **2** (validation) instead of **0**. (B) Same setup but zero non-security OOS — both tend to exit **0** (checkpoint omits `--oos-issues-ndjson`; inline would still attach the foreign file but the gate still passes). (C) `RUN_ID` empty — keyed path unset/missing, single or multiple `find` hits, ambiguity exit **2** — **equivalent** to inline. (D) `RUN_ID` set, keyed file present — **equivalent**. (E) `RUN_ID` set, keyed missing, multiple ndjson files — inline enters `find` but neither picks nor ambiguous-exits (ambiguity required empty `RUN_ID`); checkpoint does not `find`; both end at precondition exit **2** when non-sec OOS > 0 — **equivalent**. The new behavior is stricter (avoids cross-run ndjson binding) but is **not** the plan’s “1:1 port” / “byte-equivalently” ndjson discovery; acceptance and `oos-disposition-checkpoint.md` only document find-fallback “without `session-id`” (`test-oos-disposition-gate.md:16`), not this RUN_ID-present gap. **Suggested fix:** If parity with inline is required, restore the inline find condition (keep `elif … gt 1 && [ -z "$_RUN_ID" ]` for ambiguity). If the stale-RUN_ID hardening is intentional, document it in `oos-disposition-checkpoint.md` and the plan edge-case list, and call out the acceptance-criteria change explicitly so operators know exit **2** replaces a former silent foreign-batch pickup.
- **Reviewer**: dyn-ndjson-discovery-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/oos-disposition-checkpoint.sh:125-138` — Ndjson `find` fallback is gated on `[ -z "$_RUN_ID" ]`, but the removed inline block in `skills/implement/SKILL.md` (diff hunk ~171–184) used `if [ -z "$_oos_ndjson" ] || [ ! -f "$_oos_ndjson" ]` with no `RUN_ID` guard, so whenever `session-id` is non-empty and the RUN_ID-keyed file is missing, behavior diverges. **Divergent cases:** (A) `RUN_ID` set, keyed path missing, exactly one other `oos-issues.ndjson` under `larch-logs/implement/` — inline runs `find`, adopts that file, and can pass the gate (e.g. rejection markers in the foreign batch); checkpoint skips `find`, leaves a non-existent keyed path, and with `non_security_oos > 0` hits the precondition at `oos-disposition-checkpoint.sh:160-164` → exit **2** (validation) instead of **0**. (B) Same setup but zero non-security OOS — both tend to exit **0** (checkpoint omits `--oos-issues-ndjson`; inline would still attach the foreign file but the gate still passes). (C) `RUN_ID` empty — keyed path unset/missing, single or multiple `find` hits, ambiguity exit **2** — **equivalent** to inline. (D) `RUN_ID` set, keyed file present — **equivalent**. (E) `RUN_ID` set, keyed missing, multiple ndjson files — inline enters `find` but neither picks nor ambiguous-exits (ambiguity required empty `RUN_ID`); checkpoint does not `find`; both end at precondition exit **2** when non-sec OOS > 0 — **equivalent**. The new behavior is stricter (avoids cross-run ndjson binding) but is **not** the plan’s “1:1 port” / “byte-equivalently” ndjson discovery; acceptance and `oos-disposition-checkpoint.md` only document find-fallback “without `session-id`” (`test-oos-disposition-gate.md:16`), not this RUN_ID-present gap. **Suggested fix:** If parity with inline is required, restore the inline find condition (keep `elif … gt 1 && [ -z "$_RUN_ID" ]` for ambiguity). If the stale-RUN_ID hardening is intentional, document it in `oos-disposition-checkpoint.md` and the plan edge-case list, and call out the acceptance-criteria change explicitly so operators know exit **2** replaces a former silent foreign-batch pickup.
- **Suggested revision**: Address the concern above.

### FINDING_34: [OUT_OF_SCOPE] `skills/implement/scripts/test-oos-disposition-gate.sh:604-628` (“checkpoint stale RUN_ID rejects foreign ndjson fallback”) does exercise the inline-vs-checkpoint divergence in case (A): under the removed inline logic the sole `foreign-run/oos-issues.ndjson` with rejection markers would likely yield exit **0**; the harness correctly locks in exit **2**. It does not assert the alternate inline outcome, only the new contract.
- **Reviewer**: dyn-ndjson-discovery-output.txt
- **Concern**: - `skills/implement/scripts/test-oos-disposition-gate.sh:604-628` (“checkpoint stale RUN_ID rejects foreign ndjson fallback”) does exercise the inline-vs-checkpoint divergence in case (A): under the removed inline logic the sole `foreign-run/oos-issues.ndjson` with rejection markers would likely yield exit **0**; the harness correctly locks in exit **2**. It does not assert the alternate inline outcome, only the new contract.
- **Suggested revision**: Address the concern above.

### FINDING_35: [OUT_OF_SCOPE] `oos-disposition-checkpoint.md` has no dedicated ndjson-discovery subsection (RUN_ID-keyed path vs find-fallback vs precondition); that documentation gap is new on this branch but secondary to the behavioral delta above.
- **Reviewer**: dyn-ndjson-discovery-output.txt
- **Concern**: - `oos-disposition-checkpoint.md` has no dedicated ndjson-discovery subsection (RUN_ID-keyed path vs find-fallback vs precondition); that documentation gap is new on this branch but secondary to the behavioral delta above. **Branch commits (since `main`):** `2108e736f` Extract Step 8+ OOS disposition checkpoint helper; `ebde0c5be` chore larch-logs; `7b65059e7` / `fa991f338` review rounds.
- **Suggested revision**: Address the concern above.

### FINDING_36: **architecture** `skills/implement/scripts/oos-disposition-checkpoint.sh:72-76,19-30` — On `--design-tmpdir` CLI errors, if `IMPLEMENT_TMPDIR` is still unset and `prescan_implement_tmpdir` cannot find a later `--implement-tmpdir <dir>` (e.g. `"$CHECKPOINT" --design-tmpdir` alone, or `--design-tmpdir --implement-tmpdir` with no directory operand), `fail_validation` calls `log_checkpoint_failure` while `IMPLEMENT_TMPDIR` remains empty. That makes `append-tool-failure.sh` receive `--log /execution-issues.md` (root-relative), so required logging is best-effort dropped (`|| true`) and diagnostics land on the wrong filesystem path even though `_chk_log` correctly uses `${IMPLEMENT_TMPDIR:-/tmp}/…`. This breaks the contract that every non-zero exit records to `$IMPLEMENT_TMPDIR/execution-issues.md`. **Suggested fix:** Before any `fail_validation` in the parse loop, normalize unset `IMPLEMENT_TMPDIR` the same way as other CLI failures (e.g. `IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:-/nonexistent}"` and set `_chk_log` under it), or derive `--log` from the directory of `_chk_log` when `IMPLEMENT_TMPDIR` is empty so `log_checkpoint_failure` always targets the implement tmpdir being validated.
- **Reviewer**: dyn-shell-safety-output.txt
- **Concern**: - **architecture** `skills/implement/scripts/oos-disposition-checkpoint.sh:72-76,19-30` — On `--design-tmpdir` CLI errors, if `IMPLEMENT_TMPDIR` is still unset and `prescan_implement_tmpdir` cannot find a later `--implement-tmpdir <dir>` (e.g. `"$CHECKPOINT" --design-tmpdir` alone, or `--design-tmpdir --implement-tmpdir` with no directory operand), `fail_validation` calls `log_checkpoint_failure` while `IMPLEMENT_TMPDIR` remains empty. That makes `append-tool-failure.sh` receive `--log /execution-issues.md` (root-relative), so required logging is best-effort dropped (`|| true`) and diagnostics land on the wrong filesystem path even though `_chk_log` correctly uses `${IMPLEMENT_TMPDIR:-/tmp}/…`. This breaks the contract that every non-zero exit records to `$IMPLEMENT_TMPDIR/execution-issues.md`. **Suggested fix:** Before any `fail_validation` in the parse loop, normalize unset `IMPLEMENT_TMPDIR` the same way as other CLI failures (e.g. `IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:-/nonexistent}"` and set `_chk_log` under it), or derive `--log` from the directory of `_chk_log` when `IMPLEMENT_TMPDIR` is empty so `log_checkpoint_failure` always targets the implement tmpdir being validated.
- **Suggested revision**: Address the concern above.

### FINDING_37: [OUT_OF_SCOPE] **Bash 3.2:** No Bash 4+ constructs (`declare -A`, `mapfile`, namerefs, `${var^^}`) appear in `oos-disposition-checkpoint.sh`; `_gate_extra=()` / `+=` and `${_gate_extra[@]+"${_gate_extra[@]}"}` are Bash 3.2-safe.
- **Reviewer**: dyn-shell-safety-output.txt
- **Concern**: - **Bash 3.2:** No Bash 4+ constructs (`declare -A`, `mapfile`, namerefs, `${var^^}`) appear in `oos-disposition-checkpoint.sh`; `_gate_extra=()` / `+=` and `${_gate_extra[@]+"${_gate_extra[@]}"}` are Bash 3.2-safe.
- **Suggested revision**: Address the concern above.

### FINDING_38: [OUT_OF_SCOPE] **`set -e` / `set +e`:** The script intentionally avoids global `set -e` for input resolution; only the gate subprocess runs under `set +e` (lines 176–183). `set -e` at line 184 affects only the post-gate `if` chain and `log_checkpoint_failure`; `[ … -eq … ]` tests are `if`-guarded so gate rc 3+ still reach line 195. `log_checkpoint_failure` is not invoked under inherited `set +e` from a parent shell because the helper is executed as a child process.
- **Reviewer**: dyn-shell-safety-output.txt
- **Concern**: - **`set -e` / `set +e`:** The script intentionally avoids global `set -e` for input resolution; only the gate subprocess runs under `set +e` (lines 176–183). `set -e` at line 184 affects only the post-gate `if` chain and `log_checkpoint_failure`; `[ … -eq … ]` tests are `if`-guarded so gate rc 3+ still reach line 195. `log_checkpoint_failure` is not invoked under inherited `set +e` from a parent shell because the helper is executed as a child process.
- **Suggested revision**: Address the concern above.

### FINDING_39: [OUT_OF_SCOPE] **Ndjson discovery:** The branch tightens find-fallback to `RUN_ID` empty only (lines 130–137), diverging from main’s inline `if [ -z "$_oos_ndjson" ] || [ ! -f "$_oos_ndjson" ]` but matching new harness cases (stale `session-id` → exit 2). That is an intentional behavioral hardening, not a shell-option defect.
- **Reviewer**: dyn-shell-safety-output.txt
- **Concern**: - **Ndjson discovery:** The branch tightens find-fallback to `RUN_ID` empty only (lines 130–137), diverging from main’s inline `if [ -z "$_oos_ndjson" ] || [ ! -f "$_oos_ndjson" ]` but matching new harness cases (stale `session-id` → exit 2). That is an intentional behavioral hardening, not a shell-option defect.
- **Suggested revision**: Address the concern above.

### FINDING_40: [OUT_OF_SCOPE] **Commits on branch:** `2108e736f` Extract Step 8+ OOS disposition checkpoint helper; `fa991f338` / `7b65059e7` review rounds; plus a run-log flush commit.
- **Reviewer**: dyn-shell-safety-output.txt
- **Concern**: - **Commits on branch:** `2108e736f` Extract Step 8+ OOS disposition checkpoint helper; `fa991f338` / `7b65059e7` review rounds; plus a run-log flush commit.
- **Suggested revision**: Address the concern above.

