### OOS_1: [OUT_OF_SCOPE] Harness shell header comment still describes Step 3-only scope
- **Description**: [OUT_OF_SCOPE] Harness shell header comment still describes Step 3-only scope. Scenario: The planned harness behavior moves `STEP3_LITERAL` to the shared anchor and adds five-site `LOAD_LITERAL` checks, but the script header still says both Step 3 fences carry the full literal. Stale header misleads future editors about what the harness guards.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-anti-polling-rule.sh:15-17
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_2: [OUT_OF_SCOPE] Gate B continuation prose uses passive same-contract cross-reference not covered by five-site harness
- **Description**: [OUT_OF_SCOPE] Gate B continuation prose uses passive same-contract cross-reference not covered by five-site harness. Scenario: After hot-path dedup, line 718 still says with the same immediate-background contract as the Step 3 launch without an imperative read-and-apply directive. It is outside the five pinned loci, so the new harness will not catch drift if that sentence is left as a passive pointer while launch/resume blocks migrate.
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:718
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_3: [OUT_OF_SCOPE] Harness shell header comment still describes pre-migration Step 3-only scope
- **Description**: [OUT_OF_SCOPE] Harness shell header comment still describes pre-migration Step 3-only scope. Scenario: The planned harness update retargets assertions and updates `test-implement-anti-polling-rule.md` but does not mention revising the file header (lines 15-17: “both Step 3 immediate-background fences carry the result-file sleep-loop ban”). After migration the Step 3 literal lives in the shared anchor; the header misleads future editors about what the script pins.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-anti-polling-rule.sh:15-17
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

