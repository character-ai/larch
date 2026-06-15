### FINDING_1: /implement both-down does not hard-fail before checkpoint 1.r
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: blocking
- **Concern**: When both Codex and Cursor are unhealthy after retries, `/implement` Step 0 can still reach the absorbed continue tail and checkpoint `1.r` instead of refusing to proceed. `python/bootstrap.py` `_run_absorbed_continue_tail` (lines 1427–1464) still sets `DEGRADED_PROMPT_REQUIRED=true` on interactive both-down or auto-proceeds non-interactive with a sentinel; it emits no pinned hard-fail routing key. `skills/implement/SKILL.md` Step 0 routing documents `DEGRADED_PROMPT_REQUIRED` and non-interactive auto-proceed but has no both-down hard-fail row. This violates issue requirement 2 (both down → refuse to proceed in every mode).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add DEGRADED_HARD_FAIL=true (or IMPLEMENT_BAIL_REASON) to bootstrap ROUTING_KEYS; emit it on both-down in all modes; add implement SKILL Step 0 routing row that skips to Step 18 before 1.r; mirror design STEP0_STATUS=degraded-both-down-hard-fail
  - From Cursor-Requirements: On `BOTH_DOWN=true`, emit a terminal hard-fail contract (`DEGRADED_HARD_FAIL=true` and/or `IMPLEMENT_BAIL_REASON`/`ROUTE=bail`) with no Continue path; ignore stale `.degraded-tools-gate-prompted`; mirror `design-step0-session.sh` `degraded-both-down-hard-fail`
  - From Cursor-Requirements: Add an explicit routing row for both-down hard-fail (parse `DEGRADED_HARD_FAIL`/`BOTH_DOWN`/`STEP0_STATUS` from bootstrap) that aborts before checkpoint `1.r`; restrict `DEGRADED_PROMPT_REQUIRED` to one-down without sentinel only

### FINDING_2: Session setup stdout still emits probe-health globals
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan removes probe-health globals from durable session writers, but `python/session_env.py` session-setup stdout (lines 1287–1312) still emits `CODEX_AVAILABLE`/`CURSOR_AVAILABLE` (aliased from presence). Step 0 and other parsers can keep binding global health facts the issue requires eliminating.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Stop emitting `CODEX_AVAILABLE`/`CURSOR_AVAILABLE` from setup stdout; emit only `CODEX_PRESENT`/`CURSOR_PRESENT` (immediate gate) plus `CODEX_BINARY_FOUND`/`CURSOR_BINARY_FOUND`; update any parser (e.g. `design-step0-session.sh`) that still reads `CODEX_AVAILABLE` from setup output

### FINDING_3: Bootstrap coder routing still derives eligibility from probe health
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: `python/bootstrap.py` coder selection (lines 418–419, 836–874, 877–894) still derives `codex_available`/`cursor_available` from probe presence plus binary and re-emits probe-health keys on the Step 0 envelope. Explicit `--coder codex|cursor` and the implicit waterfall can treat an installed binary as unavailable when the Step 0 probe failed, and stdout/session routing keeps global health labels callers are supposed to drop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Derive coder eligibility from `*_BINARY_FOUND` (or fresh executable check) only; remove `CODEX_PRESENT`/`CURSOR_PRESENT`/`codex_available`/`cursor_available` from `_emit_final` and implement session writes; gate explicit coder pins on missing binary only

### FINDING_4: Dialectic protocol still gates judge/retry on probe-health availability
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: `skills/shared/dialectic-protocol.md` (lines 38–45, 147–160, 187–241) is not in the plan's listed surfaces. It still derives judge and retry eligibility from `CODEX_AVAILABLE` plus `CODEX_PRESENT` and `CURSOR_AVAILABLE` plus `CURSOR_PRESENT`. An installed vendor with a transient failed probe can be replaced by Claude instead of launched through its own retry/fallback path, violating requirement 3 (caller sites must not rely on global/probe health).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Add skills/shared/dialectic-protocol.md to the plan. Rebind dialectic debater retry and judge eligibility to CODEX_BINARY_FOUND/CURSOR_BINARY_FOUND or fresh executable checks, and mark any remaining CODEX_PRESENT/CURSOR_PRESENT wording as Step-0-only or compatibility-only.

---

**Merge notes**

| Merged | Rationale |
|--------|-----------|
| Pragmatic F1 + Requirements F3 + Requirements F4 → **FINDING_1** | Same behavioral risk: both-down should hard-fail on `/implement` Step 0; code, stdout contract, and SKILL routing are one fix surface. Severity **blocking**. |
| Kept separate | F2 (setup stdout), F3 (bootstrap coder routing), F4 (dialectic protocol) are different files, fixes, and caller paths. |

**Plan gap**: FINDING_4 flags `dialectic-protocol.md` as missing from the plan's **Surfaces in scope** list despite issue requirement 3 ("all places that call vendors").

### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/scripts/design-step-prelude.sh:24-29
- **Concern**: [SCOPE-REDUCTION] Plan omits the shared generated-wrapper prelude that still binds CODEX_AVAILABLE/CURSOR_AVAILABLE from CODEX_PRESENT/CURSOR_PRESENT defaults. Scenario: ~35 design-step*.sh wrappers duplicate this block and call design_source_env_optional after setting CODEX_AVAILABLE=false; once durable session env drops probe-health keys, sourced env can set CODEX_BINARY_FOUND=true while CODEX_AVAILABLE stays false, so downstream revise-waterfall/panel paths still skip external tiers despite installed binaries
- **Proposed resolution**: Add ### UPDATED: skills/design/scripts/design-step-prelude.sh to remove probe-health defaults, derive routing only from CODEX_BINARY_FOUND/CURSOR_BINARY_FOUND after source, and sync every generated wrapper that duplicates the prelude header (not only the handful named individually)

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step-prelude.sh:24-27
- **Concern**: [SCOPE-REDUCTION] Plan omits the shared generated-wrapper env-default block that still binds CODEX_AVAILABLE/CURSOR_AVAILABLE from CODEX_PRESENT/CURSOR_PRESENT. Scenario: After session_env stops persisting probe-health keys, every design wrapper that sources source-env.sh will default both vendors to false and downstream revise-waterfall/panel argv will skip externals even when CODEX_BINARY_FOUND=true
- **Proposed resolution**: Add ### UPDATED: skills/design/scripts/design-step-prelude.sh (and regenerate all Generated /design wrapper headers) to drop probe-health defaults and derive attempt flags only from CODEX_BINARY_FOUND/CURSOR_BINARY_FOUND; drop per-script one-off edits where prelude regen covers them
