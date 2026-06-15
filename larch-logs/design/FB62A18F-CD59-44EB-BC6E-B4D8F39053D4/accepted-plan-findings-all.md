### FINDING_1: /design vendor routing still derives eligibility from removed probe-health globals
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-contract-trace, Codex-dyn-contract-trace, Cursor-dyn-routing-regression, Codex-dyn-routing-regression
- **Severity**: blocking
- **Concern**: The plan removes `CODEX_PRESENT`, `CURSOR_PRESENT`, `CODEX_AVAILABLE`, and `CURSOR_AVAILABLE` from durable `source-env.sh`, but `/design` still routes vendor attempts from those keys (or aliases defaulting to `false`). After Step 0, wrappers and Python callers see absent probe globals as unavailable even when `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND` is true. That skips Codex drafter selection, validator auto-fix, Gate B `plan revise-waterfall`, plan review panel dispatch, decompose panel, and related external tiers — violating the requirement that post–Step 0 callers use binary presence only and let launcher retry handle transient failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Derive per-call attempt flags from CODEX_BINARY_FOUND/CURSOR_BINARY_FOUND in the shared wrapper boilerplate (and regen wrappers); add skills/design/scripts/design-step-validator-autofix.sh and skills/design/scripts/review-design-step3-loop.sh to Files to modify/create
  - From Codex-Arch: Add these /design runtime launch surfaces to the plan. Derive their attempt flags from CODEX_BINARY_FOUND/CURSOR_BINARY_FOUND or a fresh executable check, and pass binary-derived values through plan auto-fix.
  - From Codex-Innovation: Change the shared design wrapper prelude and vendor call sites to derive runtime eligibility from CODEX_BINARY_FOUND and CURSOR_BINARY_FOUND or fresh executable checks, while keeping probe health only in Step 0 gate state
  - From Cursor-Pragmatic: Add a plan step to update the shared wrapper preamble across generated design wrappers (derive attempt flags from CODEX_BINARY_FOUND/CURSOR_BINARY_FOUND only) and regen or bulk-edit all siblings called out in skills/design/SKILL.md
  - From Codex-Pragmatic: Add these call sites to the plan and pass or compute CODEX_BINARY_FOUND and CURSOR_BINARY_FOUND for launch eligibility. Update plan_quality and decompose to gate on binary presence or shutil.which, not probe presence.
  - From Cursor-Requirements: Add `### UPDATED: python/plan_quality.py` plus callers `skills/design/scripts/design-step-validator-autofix.sh` and `skills/design/scripts/review-design-step3-loop.sh`: select vendors from `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND` (or `shutil.which()`), not probe-health; add focused `python/test_plan_quality.py` coverage
  - From Cursor-Requirements: Extend `skills/design/SKILL.md` Step 3 / External Reviewer Setup and `skills/design/scripts/design-step3-review.sh` (and any panel-dispatch argv builder) to bind launch eligibility from `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND`, not probe-health aliases
  - From Codex-Requirements: Add the minimal /design caller updates: feed existing --*-present/--*-available attempt flags from CODEX_BINARY_FOUND/CURSOR_BINARY_FOUND or fresh shutil.which, update plan_quality/decompose/plan_scout/plan-review embedded dispatcher callers and the drafter/autofix wrappers, and cover stale-health-false plus binary-found-true.
  - From Cursor-dyn-contract-trace: Add explicit plan steps to rebind vendor attempt flags from `CODEX_BINARY_FOUND`/`CURSOR_BINARY_FOUND` in wrapper boilerplate and in `design-step2b-drafter.sh`, `design-step-validator-autofix.sh`, and `review-design-step3-loop.sh` (or a shared rehydration helper), and update `skills/design/references/decompose-panel.md` binding text away from Step 0 probe health
  - From Codex-dyn-contract-trace: Add explicit plan headings for these runtime surfaces. Drive them from CODEX_BINARY_FOUND/CURSOR_BINARY_FOUND or fresh executable checks, and regenerate or update the python/plan_review.py embedded assets that consume the retired plan-review shell scripts.
  - From Cursor-dyn-routing-regression: Add `### UPDATED: python/plan_quality.py` and `### UPDATED: skills/design/scripts/review-design-step3-loop.sh`: gate revise/auto-fix tiers on `CODEX_BINARY_FOUND`/`CURSOR_BINARY_FOUND` (or `shutil.which`), and pass those flags from the loop instead of probe `--codex-present`.


### FINDING_2: checks, ship, and review-and-fix lint-fix paths still gate on probe-health globals
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-dyn-routing-regression
- **Severity**: important
- **Concern**: The plan omits `python/checks.py`, `python/run_context.py`, `python/ship.py`, and related review-and-fix lint-fix entry points that still read `CODEX_PRESENT` / `CURSOR_PRESENT` (via `_presence_flag` or equivalent) to decide whether to launch Codex or Cursor fixers. After session-env stops exporting probe globals, prompt-side `/implement` steps, `ship pr` checks, and Step 5 relevant-checks lint-fix can treat both vendors as unavailable and return `main-agent-required` even when binaries exist on PATH.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add python/checks.py, python/run_context.py, python/ship.py, and python/test_checks.py to the plan. Make lint-fix and run_checks_phase use CODEX_BINARY_FOUND/CURSOR_BINARY_FOUND or shutil.which for launch eligibility, preserving existing non-zero launcher failure handling.
  - From Codex-Innovation: Thread binary-found or shutil.which semantics through RunContext, ship.run_ship, checks_lint_fix_main, run_checks_phase, and run_lint_fix. Keep missing-binary as the only pre-launch skip condition
  - From Codex-dyn-routing-regression: Expand the plan to update review_and_fix._run_lint_fix_loop and checks.py lint-fix entry points to derive eligibility from CODEX_BINARY_FOUND/CURSOR_BINARY_FOUND or shutil.which, and stop rehydrating/exporting probe-health vars for that path.


### FINDING_3: bootstrap resume absorbed degraded gate loses probe inputs after session-env strip
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic, Codex-dyn-contract-trace
- **Severity**: blocking
- **Concern**: `python/bootstrap.py` resume and the absorbed Step 0 degraded-tools gate still read `CODEX_PRESENT` / `CURSOR_PRESENT` from session-env or a filtered envelope. Once those keys are removed from durable env, resume passes empty presence values into `degraded-tools-gate`, which can misclassify one-down continued runs as both-down hard-fail, re-prompt incorrectly, or fail to enforce stale both-down sentinel handling after dirty-tree recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: For resume, run a fresh check-reviewers probe for the immediate gate or persist a non-health gate decision artifact. Do not call degraded-tools-gate with empty presence values from the stripped session-env
  - From Codex-Pragmatic: Keep probe presence as private in-memory data through the degraded gate, or rerun check_reviewers for bootstrap initial and resume before the gate. Do not persist it to session-env or bootstrap-routing.
  - From Codex-dyn-contract-trace: Revise the python/bootstrap.py plan to provide a non-global source for the gate on resume, such as rerunning session setup --check-reviewers for the immediate gate or persisting only DEGRADED/BOTH_DOWN/continue status in bootstrap-routing.env. Keep later routing binary-derived and test one-down continue plus stale both-down sentinel.


### FINDING_4: `/implement` orchestrator SKILL.md stale vs planned degraded-gate and binary-only dispatch contract
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements, Codex-dyn-contract-trace
- **Severity**: blocking
- **Concern**: `skills/implement/SKILL.md` still documents non-interactive auto-degrade on the absorbed bootstrap tail, a single `DEGRADED_PROMPT_REQUIRED` branch without both-down hard-fail routing, and Step 2 fail-closed on `CURSOR_PRESENT` from session-env. That conflicts with the planned contract (both-down terminal hard-fail, one-down explicit Continue, binary-derived dispatch in `implement_dispatch.py`) and can block or mis-route Cursor when the binary exists but probe health was false at Step 0.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add ### UPDATED: skills/implement/SKILL.md: replace degraded-both-down-auto/non-interactive proceed prose; add both-down hard-fail routing; require AskUserQuestion for one-down; drop CURSOR_PRESENT Step 2 fail-closed in favor of binary-found
  - From Cursor-Requirements: Add `### UPDATED: skills/implement/SKILL.md` (and `scripts/test-implement-fence-shape.sh` if fence text changes): align Step 0 degraded routing with both-down hard-fail / one-down `AskUserQuestion`, and replace Step 2 `CURSOR_PRESENT` fail-closed with `CURSOR_BINARY_FOUND` / executable-check semantics matching `implement_dispatch.py`
  - From Codex-dyn-contract-trace: Add plan headings for skills/implement/SKILL.md. Align their Step 0 and later-launch instructions with one-down Continue, both-down hard fail, stale sentinel handling, and binary-derived dispatch flags.


### FINDING_5: `/review` and `/research` skill prompts still use old degraded-gate and probe-health launch routing
- **Reviewer(s)**: Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Codex-dyn-contract-trace, Codex-dyn-routing-regression
- **Severity**: important
- **Concern**: Standalone `/review` and `/research` SKILL surfaces (and research phase references) still document one-down auto-proceed without `AskUserQuestion`, both-down continue paths in non-interactive mode, and later `codex_available` / `cursor_available` binding from Step 0 probe health. That violates the planned user-safety gate (explicit Continue when one vendor is down; hard-fail when both are down) and the binary-only caller routing rule, silently shrinking reviewer panels and research lanes when a binary exists but Step 0 probe failed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add explicit /review and /research prompt updates: parse CODEX_BINARY_FOUND and CURSOR_BINARY_FOUND, bind launch eligibility from binary presence or fresh executable checks, and reserve CODEX_PRESENT and CURSOR_PRESENT only for degraded-gate messaging.
  - From Cursor-Requirements: Add `### UPDATED: skills/review/SKILL.md`: sync Step 0 with the updated `skills/shared/external-reviewers.md` contract (one-down prompt unless continue sentinel; both-down terminal; no auto-proceed)
  - From Codex-Requirements: Add minimum prompt changes for these two skills: one-down asks for Continue before launch, both-down hard-fails, and later dispatch/lane flags use binary-found state or fresh executable checks while preserving existing waterfall behavior.
  - From Codex-dyn-contract-trace: Add plan headings for skills/review/SKILL.md, skills/research/SKILL.md, and skills/implement/SKILL.md. Align their Step 0 and later-launch instructions with one-down Continue, both-down hard fail, stale sentinel handling, and binary-derived dispatch flags.
  - From Codex-dyn-routing-regression: Add ### UPDATED: skills/review/SKILL.md. Keep CODEX_PRESENT/CURSOR_PRESENT only for the degraded gate, require Continue on one-down, and bind codex_available/cursor_available from CODEX_BINARY_FOUND/CURSOR_BINARY_FOUND or fresh executable checks before calling review core.




### FINDING_7: Design plan-review reference still gates dispatch on Step 0 probe-health globals
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Concern**: Normative `skills/design/references/plan-review.md` still gates panel and voter dispatch on Step 0 `CODEX_PRESENT` / `CURSOR_PRESENT` and documents `--codex-available` argv. `/design` Step 3 MANDATORY-reads this file, so Python-only changes would leave orchestrator instructions to skip external slots when Step 0 probe failed even with binaries installed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add ### UPDATED: skills/design/references/plan-review.md: rewrite dispatch/voter sections to binary-found or unconditional attempted slots and drop Step 0 probe-health routing language (lines 44 and 155-156)




### FINDING_1: Conflict-resolution Phase 3 still gates on session-env probe-health keys
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Live conflict-resolution Phase 3 (§3b) still gates external review on `CODEX_PRESENT` / `CURSOR_PRESENT` in session-env. After durable env drops those probe-health keys, orchestrators may skip Codex/Cursor during merge-conflict review (or follow stale fail-safe `false`), shrinking the mandated 3-reviewer panel instead of attempting externals with launcher fallbacks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: skills/implement/references/conflict-resolution.md: rebase §3b on CODEX_BINARY_FOUND/CURSOR_BINARY_FOUND or fresh executable checks; attempt externals and keep Claude fallbacks only for missing binaries or launcher failures
  - From Cursor-Pragmatic: Add ### UPDATED: skills/implement/references/conflict-resolution.md to use binary-found or fresh executable checks and launcher fallback, matching `skills/shared/external-reviewers.md`; do not gate on stripped probe-health globals


### FINDING_4: Step 2 dispatch reference still routes on `CURSOR_PRESENT`
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Normative Step 2 dispatch doc still routes on `CURSOR_PRESENT`. The doc still says `CURSOR_PRESENT` is forwarded for dispatch gating. `implement_dispatch.py` and `skills/implement/SKILL.md` move to binary-found semantics, but orchestrators that read this reference can keep fail-closed `CURSOR_PRESENT` behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add `### UPDATED: skills/implement/references/step2-dispatch.md` (and sync the Step 2 launcher note in `skills/implement/SKILL.md`) to document `CURSOR_BINARY_FOUND`/executable checks only; mark `CURSOR_PRESENT` compatibility-only, not routing.


### FINDING_5: Brainstorm reference still gates externals on Step 0 availability flags
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Brainstorm normative reference still gates external launches on Step 0 `codex_available` / `cursor_available` (Step 1d.5). After durable probe-health keys are stripped, orchestration that follows `brainstorm.md` can skip Codex/Cursor brainstorm lanes whenever Step 0 probe health was false even when binaries exist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add `### UPDATED: skills/design/references/brainstorm.md` to gate on `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND` or unconditional launch with launcher degradation; align with the design SKILL brainstorm bullet.
  - From Cursor-Requirements: Add `### UPDATED: skills/design/references/brainstorm.md` to switch launch guards to `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND` (or unconditional attempt plus launcher fallback) and align with the updated `skills/design/SKILL.md` brainstorm prose




### FINDING_1: Research lanes still gate on Step 0 probe-health globals
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: blocking
- **Concern**: After durable probe-health globals are removed, `/research` still binds lane eligibility and lane-status attribution from `CODEX_AVAILABLE`/`CURSOR_AVAILABLE`/`CODEX_PRESENT`/`CURSOR_PRESENT` (or mental flags derived from them). Normative references (`research-phase.md`, `validation-phase.md`) and `skills/research/SKILL.md` Step 0a/0b can still skip Codex/Cursor or record `fallback_presence_failed` when binaries exist, reintroducing global Step 0 health routing the plan eliminates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add ### UPDATED: skills/research/references/research-phase.md and skills/research/references/validation-phase.md; rebind lane eligibility to CODEX_BINARY_FOUND/CURSOR_BINARY_FOUND or launcher failure, not probe-health mental flags; mirror in research SKILL Step 0a binding block (lines 130-137).
  - From Cursor-Requirements: Add explicit skills/research/SKILL.md work: stop parsing/writing CODEX_AVAILABLE/CURSOR_AVAILABLE; bind lane eligibility from CODEX_BINARY_FOUND/CURSOR_BINARY_FOUND (or fresh executable checks) only; update Step 0b lane-status attribution; align with the updated skills/shared/external-reviewers.md contract.




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



