### OOS_1: [OUT_OF_SCOPE] No exhausted repair-loop integration test for step5-self-review or step5-mav
- **Description**: [OUT_OF_SCOPE] No exhausted repair-loop integration test for step5-self-review or step5-mav. Scenario: The plan routes exhaustion to the same supported sites as `no-changes-stale`, including Step 5 paths, but new coverage targets only step3 and step6. A regression in Step 5 exhaustion handoff would not be caught by the planned tests.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/tests/implement/test_checks.py
- **Phase**: design



### OOS_2: Inner repeat loop lacks explicit handling when re-invoked repair-loop returns main-agent-edit again
- **Description**: Inner repeat loop lacks explicit handling when re-invoked repair-loop returns main-agent-edit again. Scenario: After the first exhausted handoff, the main-agent-edit path can re-invoke repair-loop and get another main-agent-edit. Line 85 terminates only on continue or stall, so nested second exhaustion behavior stays undocumented. This is outside the primary bug path once the first exhaustion routes correctly.
- **Reviewer**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/implement/references/checks-repair-loop.md:85
- **Phase**: design



