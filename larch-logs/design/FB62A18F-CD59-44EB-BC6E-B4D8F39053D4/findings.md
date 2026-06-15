### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation, Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step-prelude.sh:24-27
- **Concern**: [SCOPE-REDUCTION] Plan omits the shared generated-wrapper env-default block that still binds CODEX_AVAILABLE/CURSOR_AVAILABLE from CODEX_PRESENT/CURSOR_PRESENT. Scenario: After session_env stops persisting probe-health keys, every design wrapper that sources source-env.sh will default both vendors to false and downstream revise-waterfall/panel argv will skip externals even when CODEX_BINARY_FOUND=true
- **Proposed resolution**: Add ### UPDATED: skills/design/scripts/design-step-prelude.sh (and regenerate all Generated /design wrapper headers) to drop probe-health defaults and derive attempt flags only from CODEX_BINARY_FOUND/CURSOR_BINARY_FOUND; drop per-script one-off edits where prelude regen covers them

### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: risk-integration
- **Location**: python/bootstrap.py:1359-1474
- **Concern**: /implement both-down hard-fail lacks a pinned stdout routing contract. Scenario: _run_absorbed_continue_tail still writes .degraded-tools-gate-prompted and can reach 1.r on both-down non-interactive; issue #2 requires refuse-to-proceed
- **Proposed resolution**: Add DEGRADED_HARD_FAIL=true (or IMPLEMENT_BAIL_REASON) to bootstrap ROUTING_KEYS; emit it on both-down in all modes; add implement SKILL Step 0 routing row that skips to Step 18 before 1.r; mirror design STEP0_STATUS=degraded-both-down-hard-fail

### FINDING_3:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/session_env.py:1287-1312
- **Concern**: Plan strips probe-health globals from durable session writers but not from session setup stdout. Scenario: After merge `session setup --check-reviewers` can still emit `CODEX_AVAILABLE`/`CURSOR_AVAILABLE` (and aliases them to presence), so Step 0 and other parsers keep binding global health facts the issue requires eliminating
- **Proposed resolution**: Stop emitting `CODEX_AVAILABLE`/`CURSOR_AVAILABLE` from setup stdout; emit only `CODEX_PRESENT`/`CURSOR_PRESENT` (immediate gate) plus `CODEX_BINARY_FOUND`/`CURSOR_BINARY_FOUND`; update any parser (e.g. `design-step0-session.sh`) that still reads `CODEX_AVAILABLE` from setup output

### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/bootstrap.py:418-419,836-874,877-894
- **Concern**: Bootstrap coder routing still derives `codex_available`/`cursor_available` from probe presence plus binary and re-emits probe-health keys on the Step 0 envelope. Scenario: Explicit `--coder codex|cursor` and the implicit waterfall can still treat a installed binary as unavailable when Step 0 probe failed, and stdout/session routing keeps global health labels callers are supposed to drop
- **Proposed resolution**: Derive coder eligibility from `*_BINARY_FOUND` (or fresh executable check) only; remove `CODEX_PRESENT`/`CURSOR_PRESENT`/`codex_available`/`cursor_available` from `_emit_final` and implement session writes; gate explicit coder pins on missing binary only

### FINDING_5:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/bootstrap.py:1427-1464
- **Concern**: Absorbed implement degraded tail still prompts or auto-proceeds on both-down instead of hard-failing. Scenario: Both vendors down can still reach `DEGRADED_PROMPT_REQUIRED` (interactive Continue/Abort) or non-interactive auto-proceed with a sentinel, violating requirement 2 hard-fail in every mode
- **Proposed resolution**: On `BOTH_DOWN=true`, emit a terminal hard-fail contract (`DEGRADED_HARD_FAIL=true` and/or `IMPLEMENT_BAIL_REASON`/`ROUTE=bail`) with no Continue path; ignore stale `.degraded-tools-gate-prompted`; mirror `design-step0-session.sh` `degraded-both-down-hard-fail`

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:286-296
- **Concern**: Implement Step 0 routing table has no both-down hard-fail branch. Scenario: Plan prose removes both-down Continue/Abort but the normative routing table only documents `DEGRADED_PROMPT_REQUIRED` and non-interactive auto-proceed, so orchestrators can keep treating both-down as promptable or auto-continuing
- **Proposed resolution**: Add an explicit routing row for both-down hard-fail (parse `DEGRADED_HARD_FAIL`/`BOTH_DOWN`/`STEP0_STATUS` from bootstrap) that aborts before checkpoint `1.r`; restrict `DEGRADED_PROMPT_REQUIRED` to one-down without sentinel only

### FINDING_7:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/shared/dialectic-protocol.md:38-45,147-160,187-241
- **Concern**: Missing dialectic routing update leaves a vendor-caller path on probe-health availability. Scenario: /design Step 2a.5 still derives judge and retry eligibility from CODEX_AVAILABLE plus CODEX_PRESENT and CURSOR_AVAILABLE plus CURSOR_PRESENT, so an installed vendor with a transient failed probe is replaced by Claude instead of being launched through its own retry/fallback path. This violates the issue requirement that all vendor callers stop relying on global/probe health.
- **Proposed resolution**: Add skills/shared/dialectic-protocol.md to the plan. Rebind dialectic debater retry and judge eligibility to CODEX_BINARY_FOUND/CURSOR_BINARY_FOUND or fresh executable checks, and mark any remaining CODEX_PRESENT/CURSOR_PRESENT wording as Step-0-only or compatibility-only.

### OOS_1:
- **Description**: Judge availability still defined as `CODEX_AVAILABLE` AND `CODEX_PRESENT`. Scenario: Dialectic judge prose can still instruct skipping external judges when durable health globals are stripped elsewhere, if any workflow still loads this reference
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/shared/dialectic-protocol.md:153-154
- **Phase**: design
