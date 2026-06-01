### FINDING_1: code-quality: scripts/test-implement-timing-rehydration.sh:39-76
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Invariant B no longer applies to fences that delegate timing marks to step-telemetry-mark.sh A broken or regressed helper could write marks against the wrong ledger while SKILL.md still passes test-implement-timing-rehydration invariant B Teach the awk to treat step-telemetry-mark.sh fences as timing-rehydrated or add an explicit structural check plus cross-reference to test-step-telemetry-mark
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/test-implement-timing-rehydration.sh:123
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] step_telemetry_mark_count uses grep -Fc substring match unlike exact-line Fxc peers A prose or partial line mentioning the helper prefix could skew tmpdir coupling counts Use grep -Fxc on the full pinned helper invocation line
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/step-telemetry-mark.sh:35-37
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Helper suppresses read-session-env-key stderr with 2>/dev/null Unreadable or missing session-env.sh fails more quietly than the old inline fences Drop 2>/dev/null unless stderr noise was a proven problem
- **Suggested revision**: Address the concern above.

### FINDING_4: risk-integration: skills/implement/SKILL.md:894,1308,1343,1413
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] || true at call sites only masks non-executable helper (126) not helper logic errors Lost executable bit after clone drops four step marks with no structural harness failure beyond test-step-telemetry-mark when CI runs it Rely on make test-step-telemetry-mark in CI; optional note in step-telemetry-mark.md
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] code-quality: skills/implement/SKILL.md
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Nine trio-only inline rehydration sites remain outside this extraction Future editors still copy long boilerplate for most steps Follow-on sweep when safe per plan backlog
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] code-quality: scripts/test-implement-timing-rehydration.md:7-12
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Invariant 2 docs omit helper delegation Readers may assume B still covers converted step-ENTRY fences Update docs when invariant B is extended
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **correctness** `scripts/test-implement-timing-rehydration.sh:39-76` — Invariant B only checks fences that directly invoke `timing-ledger.sh` / `timing-report.sh` in SKILL.md; converted step-ENTRY sites delegate to `step-telemetry-mark.sh`, so a future helper regression that drops `LARCH_TIMING_LEDGER` rehydration would not be caught by invariant B (only by the unit harness happy path, which always sets `LARCH_TIMING_LEDGER` in session-env). **Why out of scope:** pre-existing structural-test limitation amplified, not introduced, by this refactor; current helper code correctly reads and exports all three keys.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] code-quality
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 2. **code-quality** `scripts/test-implement-timing-rehydration.sh:1-20` — The plan called for updating the header comment as well as the `PASS:` line; only the latter was changed. **Why out of scope:** documentation drift vs plan, not a runtime defect.
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: scripts/test-implement-timing-rehydration.sh:123-131
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Harness does not pin exactly four helper calls or the four step-ENTRY mark labels required by acceptance. A follow-up could remove a step-ENTRY telemetry block or change a label without failing cardinality coupling. Add step_telemetry_mark_count == 4 and per-label grep -Fxc assertions (or a SKILL structural pin harness).
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: scripts/test-step-telemetry-mark.sh:53-61
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Never-fatal paths only assert exit 0, not that marks are still emitted. A regression could skip ledger writes on bad/empty inputs while remaining exit 0 and passing CI. Assert both ledger files receive mark rows after bad tmpdir, omitted tmpdir, and missing --label cases.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: scripts/test-step-telemetry-mark.sh:45
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Happy path requires jq without an explicit prerequisite check. CI or dev environments without jq fail with an unclear error. Add command -v jq guard at harness start.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/test-implement-timing-rehydration.sh:39-76
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Invariant B no longer applies to fences that only call step-telemetry-mark.sh. A broken helper could drop per-run timing isolation without failing the structural SKILL timing-fence check. Extend structural tests or add integration coverage that validates helper rehydration matches inline semantics.
- **Suggested revision**: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] correctness: scripts/step-telemetry-mark.sh:35-37
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Helper suppresses read-session-env-key stderr; inline fences did not. Harder to diagnose read failures during live runs; marks likely unchanged. Align stderr handling with inline fences if diagnostic parity matters (optional).
- **Suggested revision**: Address the concern above.

### FINDING_14: **`--implement-tmpdir` and `--label`** are passed only through double-quoted expansions into `read-session-env-key.sh` and `mark` subcommands — no `eval`, no unquoted interpolation.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`--implement-tmpdir` and `--label`** are passed only through double-quoted expansions into `read-session-env-key.sh` and `mark` subcommands — no `eval`, no unquoted interpolation.
- **Suggested revision**: Address the concern above.

### FINDING_15: **Labels** at `/implement` call sites are fixed literals in `SKILL.md`, not user input.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Labels** at `/implement` call sites are fixed literals in `SKILL.md`, not user input.
- **Suggested revision**: Address the concern above.

### FINDING_16: **`read-session-env-key.sh`** still uses awk extraction (no `source` of `session-env.sh`); keys are constants in the helper.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`read-session-env-key.sh`** still uses awk extraction (no `source` of `session-env.sh`); keys are constants in the helper.
- **Suggested revision**: Address the concern above.

### FINDING_17: **`token-ledger.sh mark`** builds JSON with `jq --arg step "$step"`; **`timing-ledger.sh mark`** runs labels through `sanitize_field` before TSV append.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`token-ledger.sh mark`** builds JSON with `jq --arg step "$step"`; **`timing-ledger.sh mark`** runs labels through `sanitize_field` before TSV append.
- **Suggested revision**: Address the concern above.

### FINDING_18: **Ledger path resolution** still goes through existing `validate_under_tmp` / `validate_env_ledger` / `timing_allowed_roots` logic; the helper exports `IMPLEMENT_TMPDIR` the same way the old inline fence did so timing fallback behavior is preserved.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Ledger path resolution** still goes through existing `validate_under_tmp` / `validate_env_ledger` / `timing_allowed_roots` logic; the helper exports `IMPLEMENT_TMPDIR` the same way the old inline fence did so timing fallback behavior is preserved.
- **Suggested revision**: Address the concern above.

### FINDING_19: **Subprocess isolation**: ledger-key `export`s inside the helper do not persist to the orchestrator shell, but marks run inside the helper with freshly read values; downstream scripts like `run-step5-review.sh` re-read `session-env` themselves. That is a behavioral/env-scope change, not a new trust-boundary bypass for marks themselves.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Subprocess isolation**: ledger-key `export`s inside the helper do not persist to the orchestrator shell, but marks run inside the helper with freshly read values; downstream scripts like `run-step5-review.sh` re-read `session-env` themselves. That is a behavioral/env-scope change, not a new trust-boundary bypass for marks themselves. ---
- **Suggested revision**: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `scripts/step-telemetry-mark.sh:32-42` — The helper trusts `session-env.sh` under `--implement-tmpdir` for `LARCH_TOKEN_SESSION_ID`, `LARCH_CLAUDE_SOURCE_FILE`, and `LARCH_TIMING_LEDGER` without extra validation; a hostile or corrupted `session-env.sh` could steer ledger paths or session IDs within the constraints of existing ledger validators. **Why out of scope:** identical trust model to the removed inline trio; not introduced or amplified by this refactor.
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **risk-integration** `skills/implement/SKILL.md:894,1308,1343,1413` — `|| true` plus a non-executable helper (exit 126) still fails open for telemetry (marks dropped, step continues). The new harness `[ -x ]` mitigates the exec-bit regression in CI, not at runtime against a broken install. **Why out of scope:** deliberate never-fatal telemetry policy from the plan; integrity/availability, not a new exploit path.
- **Suggested revision**: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **risk-integration** `skills/implement/SKILL.md:1343-1350` — Step 17 no longer re-exports ledger keys into the orchestrator shell before `write-final-report.sh`; that script’s optional `token-report.sh` fallback uses `${LARCH_TOKEN_SESSION_ID:-}` from the parent environment (often Step 0’s export). **Why out of scope:** pre-existing pattern for scripts that read `session-env` via `--implement-tmpdir` vs those that inherit env; session ID is stable for a normal run and the fallback path is unchanged in substance from prior step-boundary exports.
- **Suggested revision**: Address the concern above.

### FINDING_23: architecture: scripts/test-implement-timing-rehydration.sh:39-76,skills/implement/SKILL.md:894,1308,1343,1413
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Invariant B no longer guards converted step-ENTRY fences because they no longer call timing-ledger.sh directly in SKILL.md. A future edit removes timing-ledger.sh mark from step-telemetry-mark.sh or breaks the helper silently; structural harness stays green while Step 5/16/17/18-cleanup timing marks disappear. Add helper-specific structural pins (awk/grep) and/or a unit assertion that timing-ledger.sh mark is invoked on the happy path.
- **Suggested revision**: Address the concern above.

### FINDING_24: risk-integration: scripts/step-telemetry-mark.sh:39-42,skills/implement/SKILL.md:1343-1348,skills/implement/scripts/write-final-report.sh:187-188
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Helper subprocess exports do not persist LARCH_* to the orchestrator shell across Bash tool calls. Step 17 write-final-report token-report fallback uses empty LARCH_TOKEN_SESSION_ID and resolves via session-id; if session-env and session-id ever diverge token ledgers could differ from pre-refactor behavior. Re-read LARCH_TOKEN_SESSION_ID in the Step 17 write-final-report fence or harness the session-id-only fallback explicitly.
- **Suggested revision**: Address the concern above.

### FINDING_25: architecture: scripts/step-telemetry-mark.sh:14-29
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Arg parser silently ignores unknown flags and leaves LABEL empty when --label is trailing/misspelled. Orchestrator typo like --lable drops both marks with exit 0 and no stderr signal. Warn on unknown flags and empty LABEL after parse while preserving exit 0.
- **Suggested revision**: Address the concern above.

### FINDING_26: risk-integration: scripts/step-telemetry-mark.sh:35-37
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] read-session-env-key.sh stderr is redirected to /dev/null. Unexpected read failures are harder to diagnose during live runs than with the old inline reads. Remove blanket 2>/dev/null or limit suppression to expected unreadable-file cases.
- **Suggested revision**: Address the concern above.

### FINDING_27: code-quality: scripts/test-step-telemetry-mark.sh:53-61
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Negative-path tests only check exit 0 not ledger side effects. A regression writing marks to pwd-hash fallback on bad tmpdir would pass CI. Assert ledger files unchanged on never-fatal paths.
- **Suggested revision**: Address the concern above.

### FINDING_28: code-quality: scripts/test-implement-timing-rehydration.sh:123
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] step_telemetry_mark_count uses grep -Fc substring match unlike sibling exact-line counts. A comment/prose line containing the helper prefix could false-inflate the count and fail CI confusingly. Use grep -Fxc with the full canonical line template.
- **Suggested revision**: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] architecture: skills/implement/SKILL.md:513
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Prose mandates trio rehydration in later fences but Step 17 write-final-report fence omits it (pre-existing). Maintainers may assume rehydration happens where it does not. Update prose or add inline read (predates this branch).
- **Suggested revision**: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] architecture: skills/implement/SKILL.md:659-677
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Step 2 conditional token mark vs unconditional timing mark asymmetry remains. Future blanket helper conversion could break token-budget ordering on external coder paths. Keep Step 2 out of helper scope (already documented).
- **Suggested revision**: Address the concern above.

### FINDING_31: correctness: scripts/test-implement-timing-rehydration.sh:1-20
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan required updating the harness header comment plus PASS line; only PASS was updated. Contributors reading the .sh header will not see the helper-aware tmpdir coupling documented in the .md sibling; drift risk if counts change again. Extend the top-of-file or cardinality comment block to document step_telemetry_mark_count and tmpdir == token_read + step_telemetry_mark_count.
- **Suggested revision**: Address the concern above.

