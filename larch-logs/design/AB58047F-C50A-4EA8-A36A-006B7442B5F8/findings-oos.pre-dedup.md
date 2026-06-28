### OOS_1: `make test-lint-bare-grep-probe` inventory row will drift after harness expansion
- **Description**: `make test-lint-bare-grep-probe` inventory row will drift after harness expansion. Scenario: The bare-grep lint table row is slated for update, but the harness inventory at line 270 still documents only the pre-change bare-grep / wrapper-exit cases. Operators reading that row will not learn about no-path `rg`/`ripgrep`, argv truncation, or `< /dev/null` short-circuit behavior.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: docs/linting.md:270
- **Phase**: design



### OOS_2: No-path probes using explicit stdin operands `-`, `/dev/stdin`, or `/dev/fd/0` still pass a positional-path check
- **Description**: No-path probes using explicit stdin operands `-`, `/dev/stdin`, or `/dev/fd/0` still pass a positional-path check. Scenario: Ripgrep/grep treat those tokens as stdin sources, not filesystem paths. Shapes like `rg -n PATTERN -` or `command grep -q PATTERN /dev/stdin` would satisfy the planned positional-path rule yet can still block on an open background stdin pipe. This is real but outside the incident scope (ad-hoc no-path `rg PATTERN` with no operand). File only if future hangs appear; a pragma remains the minimum fix for intentional stdin search.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/lint-bare-grep-probe.sh
- **Phase**: design



### OOS_3: Harness inventory row will drift after the expanded regression matrix
- **Description**: Harness inventory row will drift after the expanded regression matrix. Scenario: The plan updates the linting table row for bare grep but not the `make test-lint-bare-grep-probe` inventory at line 270. CI still runs the harness; the stale prose just misdocuments coverage. Update when touching docs, not as part of the core hang fix.
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: docs/linting.md:270
- **Phase**: design



### OOS_4: Bare-grep violations keep the wrapper-only diagnostic even when the probe also lacks a path operand
- **Description**: Bare-grep violations keep the wrapper-only diagnostic even when the probe also lacks a path operand. Scenario: The plan keeps the existing bare `grep` branch with `next`, so `grep -n PATTERN` still reports use `command grep` before any stdin diagnostic. Authors who follow that message can write `command grep -n PATTERN` and only then see the no-path failure. Mechanical enforcement still works, but the two-step message adds avoidable churn. Optional follow-up: after bare-grep detection, still evaluate path/`/dev/null` for grep-family tokens and emit one combined diagnostic when both traps apply.
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: scripts/lint-bare-grep-probe.sh:102-103
- **Phase**: design



### OOS_5: [OUT_OF_SCOPE] Stdin path operands `-`, `/dev/stdin`, and `/dev/fd/0` are not rejected
- **Description**: [OUT_OF_SCOPE] Stdin path operands `-`, `/dev/stdin`, and `/dev/fd/0` are not rejected. Scenario: Ripgrep and grep treat these tokens as stdin sources. Shapes like `rg -n PATTERN -` or `command grep -q PATTERN /dev/stdin` would satisfy positional-path detection yet still block forever on an open background stdin pipe. The plan's path-or-`/dev/null` rule does not mention this alias class.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/lint-bare-grep-probe.sh
- **Phase**: design



