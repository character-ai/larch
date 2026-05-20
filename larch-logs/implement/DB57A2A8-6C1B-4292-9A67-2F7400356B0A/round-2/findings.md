### FINDING_1: **Important** `correctness` `scripts/test-launch-review.sh:1003`  
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `scripts/test-launch-review.sh:1003`      The new non-transient observability test expects the legacy header `retries=1`, but `append_launch_failure` now always receives `"$TRANSIENT_ATTEMPT"` and passes `--transient-retry-count` when it is non-empty (`scripts/launch-review.sh:548`, `scripts/launch-review.sh:958`). For a non-transient failure, `TRANSIENT_ATTEMPT=1`, so `append-tool-failure.sh:143-144` will emit `auth-retries=1, transient-retries=1`, making this assertion fail. Decide the contract: either only pass the transient count after an actual transient retry fired, or update this test to expect `auth-retries=1, transient-retries=1`.
- **Suggested revision**: Address the concern above.

### FINDING_2: **correctness** — [`scripts/append-tool-failure.sh:143-147`](scripts/append-tool-failure.sh): If **`--transient-retry-count` is set but `--retry-count` is empty**, the header logic has **no `elif` for transient-only**; the transient value is **silently omitted** (no `fail_usage`). [`scripts/append-tool-failure.md`](scripts/append-tool-failure.md) frames transient count as applying **alongside** `--retry-count`, so this is consistent with that doc, but it is still a **sharp edge** for any direct caller of `append-tool-failure.sh`. **Suggested fix:** document explicitly (“ignored unless `--retry-count` is set”) or reject with `fail_usage` when transient is set without retry, or add a third branch (e.g. `— transient-retries=M` only) if standalone use is desired.
- **Reviewer**: dyn-format-compatibility-output.txt
- **Concern**: - **correctness** — [`scripts/append-tool-failure.sh:143-147`](scripts/append-tool-failure.sh): If **`--transient-retry-count` is set but `--retry-count` is empty**, the header logic has **no `elif` for transient-only**; the transient value is **silently omitted** (no `fail_usage`). [`scripts/append-tool-failure.md`](scripts/append-tool-failure.md) frames transient count as applying **alongside** `--retry-count`, so this is consistent with that doc, but it is still a **sharp edge** for any direct caller of `append-tool-failure.sh`. **Suggested fix:** document explicitly (“ignored unless `--retry-count` is set”) or reject with `fail_usage` when transient is set without retry, or add a third branch (e.g. `— transient-retries=M` only) if standalone use is desired.
- **Suggested revision**: Address the concern above.

### FINDING_3: **correctness** — [`scripts/test-append-tool-failure.sh:110-111,126-131`](scripts/test-append-tool-failure.sh): There is **no test** that invokes `append-tool-failure.sh` with **`--transient-retry-count` without `--retry-count`**, so the transient-only / silent-drop behavior is **unverified**. **Suggested fix:** add a small case asserting either the documented silent omission or an explicit error, matching the chosen contract.
- **Reviewer**: dyn-format-compatibility-output.txt
- **Concern**: - **correctness** — [`scripts/test-append-tool-failure.sh:110-111,126-131`](scripts/test-append-tool-failure.sh): There is **no test** that invokes `append-tool-failure.sh` with **`--transient-retry-count` without `--retry-count`**, so the transient-only / silent-drop behavior is **unverified**. **Suggested fix:** add a small case asserting either the documented silent omission or an explicit error, matching the chosen contract.
- **Suggested revision**: Address the concern above.

### FINDING_4: **correctness** — [`scripts/test-launch-review.sh:1003-1004`](scripts/test-launch-review.sh) vs [`scripts/launch-review.sh:481-482,545-548`](scripts/launch-review.sh) and [`scripts/append-tool-failure.sh:143-147`](scripts/append-tool-failure.sh): **SL-transient-obs-nontransient** asserts the execution-issues header uses legacy `retries=1` and that the file does **not** contain `transient-retries=`. On this branch, `TRANSIENT_ATTEMPT` is initialized to `1` before the loop and is **not** incremented when the failure is non-transient ([`launch-review.sh:523-536`](scripts/launch-review.sh) guard not met). The failure path always calls `append_launch_failure` with both `"$AUTH_ATTEMPT"` and `"$TRANSIENT_ATTEMPT"` ([`548:548:scripts/launch-review.sh`](scripts/launch-review.sh)), and `append_launch_failure` forwards any non-empty seventh argument as `--transient-retry-count` ([`67:67:scripts/launch-review.sh`](scripts/launch-review.sh)). With `RETRY_COUNT=1` and `TRANSIENT_RETRY_COUNT=1`, `append-tool-failure.sh` takes the first branch and emits **`auth-retries=1, transient-retries=1`**, not `retries=1`. So the new assertions contradict the shipped wiring; **`bash scripts/test-launch-review.sh --tool codex` is expected to fail** on this case unless one side changes. **Suggested fix:** align product and tests—either (1) relax the test to expect `auth-retries=1, transient-retries=1` (and replace `assert_not_regex` with a check that distinguishes “no transient *retry*” e.g. `transient-retries=1` vs `>=2`), or (2) change `append_launch_failure` / call sites so `--transient-retry-count` is only passed when you want the dual header (e.g. when `TRANSIENT_ATTEMPT` &gt; 1), if the intended contract is “omit the field when no transient retry happened.”
- **Reviewer**: dyn-format-compatibility-output.txt
- **Concern**: - **correctness** — [`scripts/test-launch-review.sh:1003-1004`](scripts/test-launch-review.sh) vs [`scripts/launch-review.sh:481-482,545-548`](scripts/launch-review.sh) and [`scripts/append-tool-failure.sh:143-147`](scripts/append-tool-failure.sh): **SL-transient-obs-nontransient** asserts the execution-issues header uses legacy `retries=1` and that the file does **not** contain `transient-retries=`. On this branch, `TRANSIENT_ATTEMPT` is initialized to `1` before the loop and is **not** incremented when the failure is non-transient ([`launch-review.sh:523-536`](scripts/launch-review.sh) guard not met). The failure path always calls `append_launch_failure` with both `"$AUTH_ATTEMPT"` and `"$TRANSIENT_ATTEMPT"` ([`548:548:scripts/launch-review.sh`](scripts/launch-review.sh)), and `append_launch_failure` forwards any non-empty seventh argument as `--transient-retry-count` ([`67:67:scripts/launch-review.sh`](scripts/launch-review.sh)). With `RETRY_COUNT=1` and `TRANSIENT_RETRY_COUNT=1`, `append-tool-failure.sh` takes the first branch and emits **`auth-retries=1, transient-retries=1`**, not `retries=1`. So the new assertions contradict the shipped wiring; **`bash scripts/test-launch-review.sh --tool codex` is expected to fail** on this case unless one side changes. **Suggested fix:** align product and tests—either (1) relax the test to expect `auth-retries=1, transient-retries=1` (and replace `assert_not_regex` with a check that distinguishes “no transient *retry*” e.g. `transient-retries=1` vs `>=2`), or (2) change `append_launch_failure` / call sites so `--transient-retry-count` is only passed when you want the dual header (e.g. when `TRANSIENT_ATTEMPT` &gt; 1), if the intended contract is “omit the field when no transient retry happened.”
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] **risk-integration** — [`scripts/test-launch-review.sh:976-977`](scripts/test-launch-review.sh): The new non-transient stub uses `dd if=/dev/urandom` for payload generation. That is unrelated to header composition but can add **nondeterministic timing or rare CI friction** compared to a fixed-size deterministic write. Only worth tightening if CI shows flakes.
- **Reviewer**: dyn-format-compatibility-output.txt
- **Concern**: - **risk-integration** — [`scripts/test-launch-review.sh:976-977`](scripts/test-launch-review.sh): The new non-transient stub uses `dd if=/dev/urandom` for payload generation. That is unrelated to header composition but can add **nondeterministic timing or rare CI friction** compared to a fixed-size deterministic write. Only worth tightening if CI shows flakes. --- **Scout checklist (concise):** (1) Only `RETRY_COUNT`: preserved as `retries=N`. (2) Both set: `auth-retries=…, transient-retries=…` as intended. (3) Neither: no retry suffix. (4) Transient without retry: **silently dropped** — matches narrow doc (“alongside”) but is a caller foot-gun; see in-scope. (5) Validation: same digit pattern as `RETRY_COUNT`; **`0` is accepted**. (6) **No** `test-append-tool-failure.sh` case for transient-only; see in-scope.
- **Suggested revision**: Address the concern above.

### FINDING_6: architecture: scripts/append-tool-failure.sh:143-147;scripts/append-tool-failure.md
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Transient-only flag combination drops suffix silently. Callers might think --transient-retry-count alone logs observability. Document no-op or add elif branch for transient-only suffix.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: scripts/test-launch-review.sh (cursor observability block)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Scope beyond the written plan codex-only test list. None by itself; slightly widens review and maintenance surface. Document in PR or trim if strict plan adherence matters.
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: scripts/test-launch-review.sh:86-98 1083-1093
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate assert_regex and assert_not_regex helpers in the codex and cursor subsuites. Future edits risk updating one copy and not the other. Hoist helpers to shared scope or source a shared test fragment.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: implementation_plan Edge cases vs SL-transient-obs-nontransient (c)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Internal plan tension between documenting transient-retries=1 semantics and forbidding transient-retries= substring on non-transient failures. Product contract unclear for operators and reviewers. Choose one contract and align doc tests and append_launch_failure forwarding rules.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/append-tool-failure.sh:143-147
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Transient-only CLI: --transient-retry-count without --retry-count produces no retry suffix despite valid flag Caller passes only --transient-retry-count expecting a transient header fragment; header omits both retry dimensions Add elif for transient-only suffix or reject unsupported flag combination in fail_usage
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: scripts/launch-review.sh:60-67 scripts/append-tool-failure.sh:143-147 scripts/test-launch-review.sh (SL-transient-obs-nontransient)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Non-transient failure test expects legacy retries= header without transient-retries= but launcher always passes TRANSIENT_ATTEMPT=1 and append-tool-failure dual-branch emits auth-retries=1 transient-retries=1. test-launch-review codex suite should fail SL-transient-obs-nontransient regex and assert_not_regex against current code or production logs will not match the test contract. Update tests and plan assertion (c) to expect auth-retries=1 transient-retries=1 or gate passing --transient-retry-count and document the resulting loss of M=1 visibility.
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: scripts/launch-review.sh:60-72,548 scripts/append-tool-failure.sh:143-147 scripts/test-launch-review.sh:1003-1004
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Review launcher always supplies auth and transient counts on failure; append-tool-failure dual-suffix triggers whenever both are set, so TRANSIENT_ATTEMPT=1 still prints transient-retries=1; SL-transient-obs-nontransient expects legacy retries=1 and forbids transient-retries= Non-transient first-attempt failure: execution-issues line contains auth-retries=1, transient-retries=1, breaking assert_regex for retries=1 and assert_not_regex for transient-retries=; contradicts plan case (c) vs documented M=1 semantics Align tests and plan case (c) with dual-suffix semantics, or gate when --transient-retry-count is forwarded / how the suffix is composed
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: scripts/test-launch-review.sh:1003-1004
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] SL-transient-obs-nontransient expects legacy retries=1 header and forbids transient-retries=, but launcher always passes TRANSIENT_ATTEMPT=1 and append-tool-failure emits auth-retries=1, transient-retries=1 when both flags are set. bash scripts/test-launch-review.sh --tool codex fails SL-transient-obs-nontransient while docs define transient-retries=1 as no transient retry. Update assertions to auth-retries=1, transient-retries=1 (and document meaning), or change launcher contract if legacy suffix is required.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: scripts/test-launch-review.sh:913-914
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] New grep -c 'codex-review' entry counting can over-count if body echoes the substring. False test failure if future output includes codex-review outside the header. Match anchored header lines or a tighter pattern.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: implementation_plan Verification section
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan verification and file list omit test-append-tool-failure.sh and extra cursor observability test. No breakage; checklist is incomplete vs branch. Update plan or accept as intentional scope expansion.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: scripts/append-tool-failure.sh:143-147
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Validated --transient-retry-count is omitted from the header unless --retry-count is also set. Caller passes only transient-retry-count; log shows no retry suffix despite valid flag. Add transient-only elif or fail_usage when retry-count missing.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: scripts/append-tool-failure.sh:143-147;scripts/launch-review.sh:545-548
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Legacy retries= token absent on new launch-review failures. Downstream greps or dashboards keyed on retries= miss new Step 2 lines. Update parsers docs and alerts to auth-retries and transient-retries.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: scripts/test-launch-review.sh:912-914;scripts/test-launch-review.sh:1000-1002;scripts/test-launch-review.sh:2219-2223
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Entry counting uses grep -c on tool substring. If captured body text contains codex-review or cursor-review count exceeds 1 and test flakes or mis-passes. Count header lines or stable section markers instead of bare tool name.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: scripts/test-launch-review.sh:976-777
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Stub uses dd /dev/urandom piped to base64 with a weak size fallback. CI/sandbox differences change output size or emptiness vs developer machines. Use deterministic 5KB generation.
- **Suggested revision**: Address the concern above.

