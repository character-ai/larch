### FINDING_1: [OUT_OF_SCOPE] architecture: scripts/test-dispatch-code-voters.sh:223-221
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Parse-rate retry tests always run even when --section selects a subset. Using --section does not limit wall-clock to the named scenarios; pre-existing structure. Document in harness header or nest retries inside sections if that is the desired contract.
- **Suggested revision**: Address the concern above.

### FINDING_2: architecture: scripts/dispatch-code-voters.sh:155-180
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Path guard early-return skips entire log branch including larch_err not only append-tool-failure. Harness or oddly named tmpdir hits guard: execution-issues suppression is intended but stderr larch_err banner is also omitted vs production behavior. Restrict guard to append-tool-failure only or invoke larch_err before guarded return.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: .github/workflows/release-tag.yaml:71-72
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Release workflow env lacks rationale comment present in ci.yaml. Operators may remove or duplicate the knob without understanding runner Node deprecation context. Add short comment matching ci.yaml intent.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/dispatch-code-voters.md:119
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Doc claims only append-tool-failure is suppressed; code also skips larch_err on early return. Readers expect stderr warning parity with production for harness runs. Update doc or move larch_err if stderr should still fire.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/test-dispatch-code-voters.sh:249-400
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Codex/cursor issues-log label assertions removed from retry-fail; prod-shape only checks claude grep. Wrong parse_rate_check_tool_label for codex/cursor might pass CI until exercised in production. Add a production-shape assertion for a codex or cursor voter path.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/test-dispatch-code-voters.sh:28-32
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Plan/feature asked for env-isolated subshells per case; implementation uses one-time unset at harness start. Minor plan/spec structural mismatch; future tests that export these vars globally could weaken isolation. Use subshells per plan or update the plan to match the simpler unset strategy.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: scripts/test-dispatch-code-voters.sh:344-381
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Regression 1 and 2 largely duplicate the same parse-rate + empty-log scenario. Harder to see which invariant broke when a future change fails both tests together. Merge or specialize each regression to a distinct env or file invariant.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: scripts/dispatch-code-voters.sh:155-156
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Broad path substring guard may match non-harness voter paths. Real voter_path under a directory segment named test-collect-* etc. gets no execution-issues entry for true parse-rate degradation. Tighten patterns or add explicit harness env gate.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/dispatch-code-voters.sh:155-159
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Path guard globs assume a slash-prefixed segment; relative voter_path edge case may not match. Rare relative review tmpdir could still append parse-rate warnings to parent execution-issues. Match after realpath/absolute voter_path or document require absolute paths.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/test-dispatch-code-voters.sh:27-32
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Feature text asked for per-case subshell env isolation; implementation uses startup unset only. Strict plan-to-feature_description wording mismatch though behavior matches implementation_plan. Align docs/feature text with chosen pattern or add subshell wrappers if subshells are mandatory.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: scripts/test-dispatch-code-voters.sh:344-381
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Regression 1 and 2 overlap in scenario (explicit log path + guarded tmpdir + no log write). Slightly redundant coverage vs three meaningfully distinct assertions. Merge tests or split concerns so each regression asserts a unique failure mode.
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: scripts/test-dispatch-code-voters.sh:385-386
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Regression 3 replaces the script EXIT trap and drops cleanup of the main harness TMPDIR. On successful exit only prod_tmp is removed; the original test-dispatch-code-voters.* directory and stub tree under TMP leak on every run (CI disk growth; leftover fixture paths). Compose trap to remove both prod_tmp and TMP chain prior handler or rm prod_tmp explicitly and keep single EXIT trap.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: scripts/test-dispatch-code-voters.sh:385-386
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Second EXIT trap replaces the harness TMP cleanup trap. On successful exit only prod_tmp is removed; the main test-dispatch-code-voters.* directory under TMPDIR leaks. Chain traps, delete prod_tmp inline, or run regression 3 in a subshell so the original EXIT trap remains.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: scripts/test-dispatch-code-voters.sh:385-386
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Second EXIT trap replaces the harness trap that deletes $TMP. Normal pass leaves $TMP (stubs large tree) on disk under /tmp; original trap no longer runs. Chain cleanup in one trap or rm prod_tmp inline and keep single EXIT trap; or keep prod shape under $TMP.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/dispatch-code-voters.sh:155-160
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Broad path substring guards on voter_path. A legitimate review tmpdir whose path contains test-collect-/test-check-/test-tally- could suppress execution-issues logging for parse-rate degradation. Tighten patterns or document naming avoidance.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: scripts/test-dispatch-code-voters.sh:28-32
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Feature text asked per-case subshell isolation; implementation uses global unset. None if global unset is sufficient; minor spec/doc mismatch. Subshell per invoke or align requirement wording.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: scripts/test-dispatch-code-voters.sh:309-324
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Codex parse-rate retry-failure no longer asserts execution-issues log content. A future bug breaks Codex-specific parse-rate warning labels or append-tool-failure output while Claude path stays valid; regression 3 only greps claude site string so CI stays green. Add production-shape Codex (or cursor) parse-rate failure assertion against an isolated LARCH_EXECUTION_ISSUES_LOG outside test-tmpdir patterns.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: scripts/test-dispatch-code-voters.sh:309-401
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Codex issues-log label assertions removed; prod-shape regression only covers claude voter. parse_rate_check_tool_label or codex append payload can regress without failing CI. Add production-shape codex parse-rate fail case asserting launch-review codex label in issues log.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: scripts/test-dispatch-code-voters.sh:344-381
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Regression 1 and 2 overlap heavily (both LARCH + test tmpdir). Slightly redundant harness runtime. Merge or differentiate scenarios.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: scripts/test-dispatch-code-voters.sh:385-386
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Second EXIT trap replaces the harness trap that removes $TMP. On successful exit only prod_tmp is removed; the main test-dispatch-code-voters.* mktemp tree under $TMP is left on disk. Chain rm -rf in one trap or run regression 3 in a subshell so the original EXIT cleanup for $TMP remains in effect.
- **Suggested revision**: Address the concern above.

