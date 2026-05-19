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


### FINDING_17: risk-integration: scripts/test-dispatch-code-voters.sh:309-324
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Codex parse-rate retry-failure no longer asserts execution-issues log content. A future bug breaks Codex-specific parse-rate warning labels or append-tool-failure output while Claude path stays valid; regression 3 only greps claude site string so CI stays green. Add production-shape Codex (or cursor) parse-rate failure assertion against an isolated LARCH_EXECUTION_ISSUES_LOG outside test-tmpdir patterns.
- **Suggested revision**: Address the concern above.


### FINDING_18: risk-integration: scripts/test-dispatch-code-voters.sh:309-401
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Codex issues-log label assertions removed; prod-shape regression only covers claude voter. parse_rate_check_tool_label or codex append payload can regress without failing CI. Add production-shape codex parse-rate fail case asserting launch-review codex label in issues log.
- **Suggested revision**: Address the concern above.


### FINDING_2: architecture: scripts/dispatch-code-voters.sh:155-180
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Path guard early-return skips entire log branch including larch_err not only append-tool-failure. Harness or oddly named tmpdir hits guard: execution-issues suppression is intended but stderr larch_err banner is also omitted vs production behavior. Restrict guard to append-tool-failure only or invoke larch_err before guarded return.
- **Suggested revision**: Address the concern above.


### FINDING_20: risk-integration: scripts/test-dispatch-code-voters.sh:385-386
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Second EXIT trap replaces the harness trap that removes $TMP. On successful exit only prod_tmp is removed; the main test-dispatch-code-voters.* mktemp tree under $TMP is left on disk. Chain rm -rf in one trap or run regression 3 in a subshell so the original EXIT cleanup for $TMP remains in effect.
- **Suggested revision**: Address the concern above.


### FINDING_4: code-quality: scripts/dispatch-code-voters.md:119
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Doc claims only append-tool-failure is suppressed; code also skips larch_err on early return. Readers expect stderr warning parity with production for harness runs. Update doc or move larch_err if stderr should still fire.
- **Suggested revision**: Address the concern above.


### FINDING_5: code-quality: scripts/test-dispatch-code-voters.sh:249-400
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Codex/cursor issues-log label assertions removed from retry-fail; prod-shape only checks claude grep. Wrong parse_rate_check_tool_label for codex/cursor might pass CI until exercised in production. Add a production-shape assertion for a codex or cursor voter path.
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: scripts/dispatch-code-voters.sh:155-156
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Broad path substring guard may match non-harness voter paths. Real voter_path under a directory segment named test-collect-* etc. gets no execution-issues entry for true parse-rate degradation. Tighten patterns or add explicit harness env gate.
- **Suggested revision**: Address the concern above.


