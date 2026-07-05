### OOS_1: Aggregated rollup of 2 capped OOS items
- **Description**: Cap 1 (OOS_ISSUES_PER_RUN_CAP) exceeded; the following 2 items were rolled up by the per-run OOS issue cap. Each rolled-up item's full body is preserved verbatim below:
  - **[OUT_OF_SCOPE] Short-circuit structural ruff failures before external lint-fix dispatch**: [Files: C901/PLR0911/PLR0912/PLC0415. python/larch/implement/checks_lint_fix.py:1141-1169]
    ### OOS_1: [OUT_OF_SCOPE] Short-circuit structural ruff failures before external lint-fix dispatch
    - **Description**: [OUT_OF_SCOPE] Short-circuit structural ruff failures before external lint-fix dispatch. Scenario: The reported stall spent ~22 minutes in lint-fix that could not change C901/PLR0911/PLR0912/PLC0415. The repair-loop fallback fixes terminal routing, but every occurrence still pays the full automated loop first.
    - **Reviewer**: Cursor-Innovation
    - **Severity**: latent
    - **Focus area**: architecture
    - **Location**: python/larch/implement/checks_lint_fix.py:1141-1169
    - **Phase**: design
  - **[OUT_OF_SCOPE] The allowlist for no-changes-stale fallback is broader than the Step 6 bug requires. It adds step3 and step5 sites even though the issue scope is Step 6.**: [Files: skills/implement/references/checks-repair-loop.md:28-31 python/larch/implement/checks_lint_fix.py:234-356]
    ### OOS_5: [OUT_OF_SCOPE] The allowlist for no-changes-stale fallback is broader than the Step 6 bug requires. It adds step3 and step5 sites even though the issue scope is Step 6.
    - **Description**: [OUT_OF_SCOPE] The allowlist for no-changes-stale fallback is broader than the Step 6 bug requires. It adds step3 and step5 sites even though the issue scope is Step 6.. Scenario: Step3 and Step5 already have existing main-agent fallback contracts in `skills/implement/references/checks-repair-loop.md:28-31,64-85`, so broadening them here increases contract surface without fixing the reported Step 6 stall.
    - **Reviewer**: Codex-dyn-Repair Loop Contract
    - **Severity**: nit
    - **Focus area**: architecture
    - **Location**: python/larch/implement/checks_lint_fix.py:234-356
    - **Phase**: design
- **Reviewer**: Combined: capped per-run rollup
- **Vote tally**: N/A — capped rollup of 2 entries
- **Phase**: implement
