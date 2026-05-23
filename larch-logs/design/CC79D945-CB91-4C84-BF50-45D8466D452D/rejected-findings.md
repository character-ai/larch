### [Plan Review] FINDING_17

### FINDING_17: Tier success path lists commit push but omits append-token-record.sh refresh-run

- **Severity**: important
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:142-144 vs scripts/ship-pr.sh:1988-2034
- **Concern**: Tier success path lists commit push but omits append-token-record.sh refresh-run-logs.sh git-push sequence used by run_ci_fix_vendor
- **Scenario/breakage**: Waterfall success may skip token ledger and run-log refresh breaking timing and downstream expectations
- **Suggested fix**: Move argv parsing, initial state creation, validation, RESUME_PHASE handling, and main loop inside the BASH_SOURCE guard or introduce an explicit test-source mode
- **Reviewer**: Codex-Requirements, Cursor-Requirements


### [Plan Review] FINDING_24

### FINDING_24: CI local-reproduction invariant is described as enforced, but the plan relies on

- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:5,178-185; scripts/ship-pr.sh:1254-1306
- **Concern**: CI local-reproduction invariant is described as enforced, but the plan relies on prompt text plus post-fix relevant checks
- **Scenario/breakage**: An agent can skip reproducing the failed job; the gate proves only that checks now pass, not that the original failure was reproduced or that the fix targets it
- **Suggested fix**: Bring the proof KV envelope into scope: require REPRO_CMD, REPRO_FAILED_BEFORE, VERIFY_CMD, VERIFY_PASSED_AFTER, and have ship-pr.sh reject missing or false proof before commit/push
- **Reviewer**: Codex-Arch, Codex-Innovation


### [Plan Review] FINDING_25

### FINDING_25: Plan duplicates baseline, dirty-path delta, rollback, and HEAD-assertion mechani

- **Severity**: latent
- **Focus area**: code-quality
- **Location**: plan.txt:69-88; scripts/lint-fix-loop.sh:99-140,272-285; scripts/ship-pr.sh:43-55
- **Concern**: Plan duplicates baseline, dirty-path delta, rollback, and HEAD-assertion mechanics already present around lint-fix-loop dispatch
- **Scenario/breakage**: Future fixes to dispatch worktree safety can drift between lint-fix-loop and the new waterfall implementation
- **Suggested fix**: Extract a small shared worktree-dispatch helper/library and have both lint-fix-loop and ship-pr waterfall use it
- **Reviewer**: Codex-Arch


