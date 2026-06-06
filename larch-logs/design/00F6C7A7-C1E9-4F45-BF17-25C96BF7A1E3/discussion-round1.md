## Decision 1: Overall intent
- **Question**: #3563 is an auto-filed, sanitized stall report with no recoverable root-cause evidence. What should /design produce?
- **Resolution**: Harden the stall-recovery *reporting* surface so future stall issues are actionable — NOT a root-cause fix for the specific #3550 dispatch failure (evidence is gone) and NOT operational recovery of #3550.
- **Source**: user

## Decision 2: Breadth
- **Question**: Exit-code-representation fix only, or also surface more already-sanitized diagnostics?
- **Resolution**: Two changes: (a) uncaptured/non-numeric exit codes must render as `unknown` instead of the misleading `0`; (b) add the already-sanitized `bail_reason` to the report body so dispatch-failures show which envelope check failed (`orchestrator-envelope-invalid` / `wrapper-validation-failure`).
- **Source**: user

## Decision 3: Surfaces in scope
- **Question**: Which render surfaces must change?
- **Resolution**: All three report surfaces that render these fields — `bug-body`, `bug-comment` (both via `compose_body_content`), and `chat-print` (separate code path) — for consistency between the live chat print and the filed issue/comment.
- **Source**: codebase (consistency requirement)

## Decision 4: Where the exit-code distinction is preserved
- **Question**: Can the renderer alone distinguish a real 0 from an uncaptured exit code?
- **Resolution**: No. `classify` already coerces empty/non-numeric `EXIT_CODE -> 0` (`stall-recovery-report.sh:671-673`) before the renderer sees it, and `compose_body_content` coerces again (`:879`). The fix MUST preserve the unknown distinction starting at `classify`'s emission, then render it. Mirror the existing `safe_step_value` / `safe_phase_value` -> `unknown` pattern with a `safe_exit_code_value`.
- **Source**: codebase

## Decision 5: bail_reason enum doc reconciliation
- **Question**: Is the bail_reason enum consistently documented?
- **Resolution**: `stall-recovery-report.md` describes a narrow `BAIL_REASON` enum (`adopted-issue-closed`, `tracking-init-failed`, plus empty -> else `redacted`), but `safe_bail_reason_value` (`:528`) actually allowlists a broader set including `orchestrator-envelope-invalid` and `wrapper-validation-failure`. Since the body will now display `bail_reason`, this doc drift must be reconciled (doc made accurate to the code's allowlist).
- **Source**: codebase

## Decision 6: Hard constraints (must not break)
- **Question**: What existing behavior/invariants must be preserved?
- **Resolution**:
  - Allowlist parity: the `lint` subcommand asserts TSV == helper code surface == doc table at the `surface + field_key` level. Any new field/transform must be added to all three in lockstep.
  - SECURITY.md "Stall recovery sanitization": no raw evidence leakage; only allowlisted enums/hashes/integers/fixed prose; every body/comment still piped through `redact-secrets.sh`. `bail_reason` is already a sanitized closed enum, so adding it stays within the model.
  - `test-stall-recovery-report.sh` must stay green; new behavior (exit_code `unknown`, bail_reason row) needs added assertions.
  - The machine `EXIT_CODE` KV emitted by `classify` is consumed downstream — changing its value for the uncaptured case from `0` to a non-numeric `unknown` must be checked for backward-compat with any numeric consumers before adopting that representation.

## Non-goals (explicitly out of scope)
- Fixing the actual Step-2 dispatch failure mechanism / classifier phase derivation (the odd `phase: checks at step 2` labeling). User did NOT pick dispatch hardening.
- Operational recovery of the stuck #3550 `[IMPLEMENTING]` run.
- Broadening sanitization to expose raw dispatch evidence.
