### OOS_1: Aggregated rollup of 3 capped OOS items
- **Description**: Cap 1 (OOS_ISSUES_PER_RUN_CAP) exceeded; the following 3 items were rolled up by the per-run OOS issue cap. Each rolled-up item's full body is preserved verbatim below:
  - **Stall diagnostics still say guidelines warning refresh after outcome flush rename**: [Files: python/larch/implement/ship.py:205-247]
    ### OOS_2: Stall diagnostics still say guidelines warning refresh after outcome flush rename
    - **Description**: Stall diagnostics still say guidelines warning refresh after outcome flush rename. Scenario: After replacing _flush_guidelines_warning_before_pr, failure stalls will still read architectural-guidelines warning run-log refresh skipped, which misleads operators debugging outcome-commit failures
    - **Reviewer**: Cursor-Arch
    - **Severity**: nit
    - **Focus area**: code-quality
    - **Location**: python/larch/implement/ship.py:205-247
    - **Phase**: design
  - **No shared tmpdir filename constant for the outcome sidecar**: [Files: python/larch/core/architectural_guidelines.py:27-36]
    ### OOS_3: No shared tmpdir filename constant for the outcome sidecar
    - **Description**: No shared tmpdir filename constant for the outcome sidecar. Scenario: Other guideline artifacts use named constants in architectural_guidelines.py; the plan only names the committed batch file, which invites path drift between writer, flush staging, and tests
    - **Reviewer**: Cursor-Arch
    - **Severity**: nit
    - **Focus area**: architecture
    - **Location**: python/larch/core/architectural_guidelines.py:27-36
    - **Phase**: design
  - **Stable reason tokens are unspecified**: [Files: python/larch/implement/ship_guidelines.py]
    ### OOS_2: Stable reason tokens are unspecified
    - **Description**: Stable reason tokens are unspecified. Scenario: Outcome JSON carries a `reason` field used for histograms, but the plan does not define a bounded token set or validation beyond audit presence checks. Typos will fragment drop analytics over time.
    - **Reviewer**: Cursor-Innovation
    - **Severity**: latent
    - **Focus area**: code-quality
    - **Location**: python/larch/implement/ship_guidelines.py
    - **Phase**: design
- **Reviewer**: Combined: capped per-run rollup
- **Vote tally**: N/A — capped rollup of 3 entries
- **Phase**: implement
