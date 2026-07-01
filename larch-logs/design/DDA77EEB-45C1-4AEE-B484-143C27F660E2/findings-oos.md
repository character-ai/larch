### OOS_1: [OUT_OF_SCOPE] Testing strategy omits the references header-triplet harness for a Consumer/Contract/When-to-load edit surface
- **Description**: [OUT_OF_SCOPE] Testing strategy omits the references header-triplet harness for a Consumer/Contract/When-to-load edit surface. Scenario: Opening-block compression can remove or break anchored `**Consumer**:` / `**Contract**:` / `**When to load**:` headers while leaving flag tokens intact; `test_design_argv.py` and closure ratchet would still pass. `scripts/test-references-headers.sh` catches this, and run-relevant checks map `skills/*/references/*.md` to that harness, but the plan's Testing strategy never lists `make test-references-headers`
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/references/flags.md:1-9
- **Phase**: design



### OOS_2: [OUT_OF_SCOPE] [SCOPE-REDUCTION] Prefer compressing public-flag bullets before the plan-size/check-size contract block
- **Description**: [OUT_OF_SCOPE] [SCOPE-REDUCTION] Prefer compressing public-flag bullets before the plan-size/check-size contract block. Scenario: ~60% of flags.md tokens sit outside the repetitive public-flag bullets; editing lines 30-69 risks dropping TRIGGER_REASONS order, exit-code 2/3 split, and trailer-placement rules while numeric thresholds remain. Issue goal is density-only with zero behavior change.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/flags.md:30-69
- **Phase**: design



