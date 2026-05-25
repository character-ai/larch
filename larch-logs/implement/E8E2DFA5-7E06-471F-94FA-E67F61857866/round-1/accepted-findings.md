### FINDING_1: code-quality: skills/design/references/flags.md:20
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] --partition bullet claims hard triggers route to Split-path automatically. Hard plans still show AskUserQuestion Split/Cancel before Split-path; only partition-flag skips the prompt. Reword: hard → Split/Cancel prompt first; partition → direct Split-path when HARD_TRIGGER_FIRED=false.
- **Suggested revision**: Address the concern above.


### FINDING_13: correctness: README.md:61
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] README still describes --partition as forcing a partition prompt path. Operators expect an intermediate AskUserQuestion partition prompt that Step 2b.5 no longer performs. Update README /design row to state --partition routes directly to Split-path when no hard trigger per flags.md.
- **Suggested revision**: Address the concern above.


### FINDING_3: risk-integration: README.md:61
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Stale --partition prose still describes a Step 2b.5 partition prompt path. Users reading README expect an AskUserQuestion soft/partition prompt; runtime now jumps straight to Split-path without Continue. Rewrite the README /design row to say --partition routes directly to the decomposition panel when no hard trigger fires.
- **Suggested revision**: Address the concern above.


