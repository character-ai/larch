### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-write-design-current-env.sh:new Case 14
- **Concern**: Case 14 seeds only CODEX_PRESENT but expects the other reviewer keys to be preserved. Scenario: If implemented literally, the test either fails because CURSOR_PRESENT/CODEX_AVAILABLE/CURSOR_AVAILABLE never existed or drops the preservation assertion, leaving explicit override plus omitted-key preservation untested
- **Proposed resolution**: Seed all four reviewer keys in the first Case 14 write, then rewrite with only --codex-present false and assert CODEX_PRESENT=false while the other three keep their initial values

### FINDING_2:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/write-design-current-env.sh:158-161
- **Concern**: Partial explicit overrides can preserve a stale alias value. Scenario: Case 14's proposed --codex-present false refresh after a true seed can emit CODEX_PRESENT=false while recovering old CODEX_AVAILABLE=true, contradicting the alias contract and letting consumers that read CODEX_AVAILABLE treat Codex as available
- **Proposed resolution**: Either require paired overrides in the plan/test, or track flag presence and mirror an explicit present/available value to its omitted peer instead of recovering the stale peer

### FINDING_3:
- **Reviewer(s)**: Cursor-dyn-test-gap-recovery, Codex-dyn-test-gap-recovery
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:66-68; skills/design/scripts/test-write-design-current-env.sh:266-288
- **Concern**: Case 14 cannot prove the three omitted reviewer keys are preserved because its setup only seeds CODEX_PRESENT before the override write. Scenario: The proposed test passes --codex-present false while omitting CURSOR_PRESENT CODEX_AVAILABLE and CURSOR_AVAILABLE, but those three keys have no prior values in the described first write, so an implementation that drops omitted keys during a partial override could still pass unless the case shares state accidentally with Case 13
- **Proposed resolution**: Seed all four reviewer keys in Case 14's first write, then rewrite the same output with only --codex-present false and assert CODEX_PRESENT is false while CURSOR_PRESENT CODEX_AVAILABLE and CURSOR_AVAILABLE keep their seeded values
