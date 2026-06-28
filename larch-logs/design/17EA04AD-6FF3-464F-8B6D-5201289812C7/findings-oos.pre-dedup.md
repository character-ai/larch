### OOS_1: Wrapper contract doc still claims marker bodies stream between `LARCH_FINAL_SUMMARY_BEGIN/END`.
- **Description**: Wrapper contract doc still claims marker bodies stream between `LARCH_FINAL_SUMMARY_BEGIN/END`.. Scenario: `skills/design/SKILL.md` cites `design-step5c.md` as the Step 5c contract; invariant line 22 still describes body emission into the contract stream after the helper change.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/scripts/design-step5c.md:22
- **Phase**: design



### OOS_2: Companion harness doc still describes `/design` marker-first row enforcement.
- **Description**: Companion harness doc still describes `/design` marker-first row enforcement.. Scenario: The `.sh` harness is updated in-plan, but the paired `.md` still tells maintainers to pin marker-first design bindings, inviting reintroduction of retired greps.
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: scripts/test-render-cost-line-callsites.md:9-18
- **Phase**: design



### OOS_3: [OUT_OF_SCOPE] Wrapper contract still says final-summary body is emitted between LARCH_FINAL_SUMMARY markers though SKILL.md cites design-step5c.md as the Step 5c contract
- **Description**: [OUT_OF_SCOPE] Wrapper contract still says final-summary body is emitted between LARCH_FINAL_SUMMARY markers though SKILL.md cites design-step5c.md as the Step 5c contract. Scenario: Maintainers or agents loading the wrapper doc after the helper change will believe marker bodies still traverse task stdout and may debug the wrong surface
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/scripts/design-step5c.md:22
- **Phase**: design



### OOS_4: Wrapper contract still documents full marker-body emission between LARCH_FINAL_SUMMARY_BEGIN/END
- **Description**: Wrapper contract still documents full marker-body emission between LARCH_FINAL_SUMMARY_BEGIN/END. Scenario: Maintainers loading design-step5c.md on Step 5c paths may reintroduce marker-body extraction after Python emits empty readiness markers only
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: skills/design/scripts/design-step5c.md:22
- **Phase**: design



