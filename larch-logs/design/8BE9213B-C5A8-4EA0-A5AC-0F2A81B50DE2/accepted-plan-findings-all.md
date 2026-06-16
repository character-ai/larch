### FINDING_1: Plan omits `test-implement-structure.sh` harness updates for relocated probe and removed SKILL markers
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-dyn-state-contract-auditor
- **Severity**: blocking
- **Concern**: The plan changes Step 8 SKILL prose (drops the standalone `8-pre-ship` fence and `write-initial-state-keys` / `NO_ADMIN_FALLBACK` markers) but does not update `scripts/test-implement-structure.sh`, which still pins those literals in SKILL.md. `make lint` will fail before the PR can ship.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: scripts/test-implement-structure.sh`: relocate the phantom assertion to `step-8-ship.sh`, replace the `NO_ADMIN_FALLBACK` SKILL pin with a `python/cli.py ship seed-initial-state` / `--no-admin-fallback` pin, and drop stale `write-initial-state-keys` references
  - From Codex-Arch: Add scripts/test-implement-structure.sh to the plan and retarget these assertions to the new seeder contract and wrapper-owned 8-pre-ship probe
  - From Cursor-Innovation: Add `### UPDATED: scripts/test-implement-structure.sh` — repoint the 8-pre-ship pin to `step-8-ship.sh` and pin `NO_ADMIN_FALLBACK` via the Python seeder contract instead of the deleted marker block
  - From Cursor-Pragmatic: Add scripts/test-implement-structure.sh to the plan and repoint the assertion to skills/implement/scripts/step-8-ship.sh invoking scripts/phantom-probe-with-warn.sh --step 8-pre-ship
  - From Codex-Pragmatic: Add scripts/test-implement-structure.sh to the plan; replace the stale SKILL.md literal checks with assertions for the seed-initial-state call and wrapper-owned 8-pre-ship probe.
  - From Cursor-Requirements: Add `### UPDATED: scripts/test-implement-structure.sh` to repoint the 8-pre-ship pin at `step-8-ship.sh` and replace the NO_ADMIN prose pin with the seeder contract (or equivalent literal)
  - From Codex-dyn-state-contract-auditor: Update scripts/test-implement-structure.sh in the plan; move these pins to the new authorities, such as python/test_ship.py for the seeded key and step-8-ship.sh for the wrapper-owned probe


### FINDING_2: State seeding must be first-entry only (seeder guard + SKILL re-entry rule)
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-dyn-state-contract-auditor
- **Severity**: blocking
- **Concern**: The plan seeds `ship-pr-state.sh` unconditionally on every Step 8 orchestrator entry. Re-entry paths (OOS, transient retry, conflict resume) must re-invoke only `step-8-ship.sh` while preserving driver-progressed keys (`PHASE`, `PR_NUMBER`, stall keys, `ITERATION`, `RESUME_PHASE`, etc.). Re-seeding on re-entry would overwrite or reset that state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Require seeder to fail closed when `--state-file` already exists and is non-empty (initial-create only); keep Step 5 stall seeding on the missing-file path only; document orchestrator rule: seeder + `oos file` run once before the first `step-8-ship.sh`, never on driver re-invocations
  - From Cursor-Arch: In Step 8 prose, state explicitly: first orchestrator entry only runs seeder then `oos file` then `step-8-ship.sh`; all later Step 8+ continuations invoke only `step-8-ship.sh` (probe stays inside the wrapper)
  - From Cursor-Pragmatic: Document that seed-initial-state and oos file run only on first Step 8 entry when ship-pr-state.sh is absent; seeder should fail closed if a non-initial state file already exists
  - From Cursor-dyn-state-contract-auditor: Document first-entry-only orchestration in ### UPDATED: skills/implement/SKILL.md and give seed-initial-state create-if-absent semantics (or explicit fail-closed when the state file already has driver progress keys), mirroring stall-recovery seed-terminal-state rewrite-vs-seed split in python/stall_recovery.py:1079-1106.


### FINDING_6: Pre-wrapper seeder breaks Python &lt;3.11 STALLED JSON fallback
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The load-bearing 3.11 JSON fallback only runs inside `step-8-ship.sh`. Running `python/cli.py ship seed-initial-state` before the wrapper on Python &lt;3.11 exits 2 on stderr, so Step 8 no longer receives the required STALLED JSON fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Do not run the ship seeder before the wrapper guard; either move Step 8 seeding into step-8-ship.sh after its version check or add an equivalent Bash-level 3.11 JSON fallback before the seeder


### FINDING_8: Step 5 stall branch seeder call must pass full dynamic session inputs
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Today's stall branch seeds the full canonical set from session values and then forces stall-specific overrides (`MERGE=false`, `DRAFT=false`, `DEFERRED`, `NO_LOGS_COMMIT`, dynamic branch/issue/repo/manifest/tool_label, lint-fix `BAIL_REASON`, etc.). The plan lists only stall override keys and does not require passing the dynamic CLI inputs to `ship seed-initial-state`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Augment the stall branch to call the seeder with all session-established dynamic flags plus stall overrides (`--stall-tracking`, `--stall-step 5`, lint-fix `--bail-reason`, empty detail log), preserving the existing already-present-state key-based rewrite path for `BAIL_REASON`/`IMPLEMENT_BAIL_REASON`


### FINDING_10:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/ship.py:75-117
- **Concern**: [SCOPE-REDUCTION] Plan broadens `_write_ship_state` refresh work beyond the actual gap. Scenario: Only `NO_ADMIN_FALLBACK` is missing from `_ALLOWED_SHIP_STATE_KEYS`; listed fields (`EXPECTED_SESSION_ID`, `TOOL_LABEL`, `DEFERRED`, etc.) are already allowed and preserved via read-merge-write, so extra refresh logic is unnecessary churn
- **Proposed resolution**: Limit `_write_ship_state` change to adding `NO_ADMIN_FALLBACK` to `_ALLOWED_SHIP_STATE_KEYS` (and seeding it from `RunContext` if the driver should be able to set it on first write); drop the broader refresh bullet unless a test proves another key is dropped today


### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:75-117
- **Concern**: [SCOPE-REDUCTION] Plan extends _write_ship_state refresh for many keys already in _ALLOWED_SHIP_STATE_KEYS. Scenario: Only NO_ADMIN_FALLBACK is missing from the allowed set today; broad refresh expansion is while-we-are-here scope beyond the issue
- **Proposed resolution**: Limit code changes to adding NO_ADMIN_FALLBACK to _ALLOWED_SHIP_STATE_KEYS and writing it from ctx in _write_ship_state; rely on seeder plus existing read-merge for other durable keys




### FINDING_1: Step 8 Python 3.11 guard needs a fence-shape-compliant shared script
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The plan adds a first-entry orchestrator Python 3.11 guard before `seed-initial-state`, but `Files to modify/create` names no fence-shape-compliant wrapper and `step-8-ship.sh` already owns the only working guard implementation. New-fence rules in `scripts/test-implement-fence-shape.sh` forbid inline `if` / control logic; copying the guard inline into SKILL.md will fail CI, while duplicating the JSON+exit-4 block in prose guarantees drift from `step-8-ship.sh:70-73`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add one thin script (for example `skills/implement/scripts/step-8-python-guard.sh`) that both `step-8-ship.sh` and the first-entry orchestrator call via `bash "$IMPLEMENT_TMPDIR/larch-run.sh" …`; list it in the plan files and harnesses.


### FINDING_2: Step 8 first-entry seeder call lacks explicit session argv mapping
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Step 8 first-entry seeder call lacks explicit session argv mapping unlike the stall path. The orchestrator may remove the marker block but Step 8 SKILL prose only names the verb; happy-path wiring may omit dynamic flags that `step5-review-branches` documents for the same seeder, breaking seed parity with the pinned key harness or pre-ship oos file inputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Mirror the stall-path flag list in Step 8 first-entry docs: one larch-run.sh fence calling `python/cli.py ship seed-initial-state` with all session-established dynamic inputs (actual merge/draft/forked flags, manifest path, tool label, session-id prefix fields), explicitly noting stall overrides are omitted on the normal path


### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:566 skills/implement/references/step5-review-branches.md:11
- **Concern**: [SCOPE-REDUCTION] Canonical seeder key set omits OOS_PENDING=false even though current Step 5 stall seed explicitly writes it. Scenario: RunContext defaults oos_pending=True (python/run_context.py:96); _write_ship_state always emits OOS_PENDING from ctx (python/ship.py:566); _context_with_state_overlay only overrides when the key is present. Plan stall path drops the explicit OOS_PENDING=false override when replacing inline seed prose with seed-initial-state. A Step-5-stalled state file can reach step-8-ship.sh with no OOS_PENDING key and get OOS_PENDING=true on first driver refresh, mis-routing bash-path OOS checkpoint semantics.
- **Proposed resolution**: Add OOS_PENDING=false to the seed-initial-state canonical constant and python/test_ship.py ordered-key assertions; no separate stall-only override needed.



### FINDING_1: Step 8 seeder fence violates thin-fence contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements, Codex-Generic
- **Severity**: blocking
- **Concern**: The planned Step 8 `python/cli.py ship seed-initial-state` example in `skills/implement/SKILL.md` uses a multi-line `larch-run.sh` Bash fence with `\` line continuations (and likely inline shell such as `$(cat ... || true)`). Post-Step-0 fences must be exactly one nonblank physical line with no continuations or inline control logic. `scripts/test-implement-fence-shape.sh` `validate_new` (lines 136–171) enforces that contract. As written, the SKILL edit fails `make lint` / `test-implement-fence-shape.sh` and contradicts the plan’s own fence-shape compliance goal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add thin step-8-seed-ship-pr-state.sh wrapper (or single physical-line fence) and replace the multi-line seed-initial-state example
  - From Cursor-Requirements: Replace the multi-line seeder fence with a single-line launcher call (all flags on one line, no `\`), or add a thin `skills/implement/scripts/step-8-seed-initial.sh` (or similar) that reads session-established values internally and invoke it as one line: `bash "$IMPLEMENT_TMPDIR/larch-run.sh" skills/implement/scripts/step-8-seed-initial.sh`.
  - From Codex-Generic: Move argv assembly into a wrapper or seed verb defaults, then keep SKILL.md to one larch-run line; do not relax the fence-shape harness


### FINDING_2: Seeder `EXPECTED_TMPDIR_BASENAME_PREFIX` diverges from `step-8-ship.sh` derivation
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The planned seeder examples pass `--expected-tmpdir-basename-prefix "claude-implement-${CLONE_TAG:-_}-"`, but `skills/implement/scripts/step-8-ship.sh` derives `CLONE_TAG_FULL` from `basename "$PWD"` with sanitization (`tr -c 'A-Za-z0-9_-' '_'`) and 32-character truncation when `CLONE_TAG` is unset (lines 61–68), then passes `--expected-tmpdir-basename-prefix "claude-implement-${CLONE_TAG_FULL}-"` (line 91). Implement sessions rarely export `CLONE_TAG`, so the seeder can write `claude-implement-_-` while the ship driver and the real session tmpdir use a different prefix. That mismatch affects both Step 8 entry and the Step 5 stall seed path (`skills/implement/references/step5-review-branches.md`). Step 18 `verify_cleanup_target` in `scripts/implement-finalize.sh` reads the seeded prefix from `ship-pr-state.sh` and may reject legitimate cleanup or accept the wrong directory unless `EXPECTED_SESSION_ID` fallback masks the error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: EXPECTED_TMPDIR_BASENAME_PREFIX in ship-pr-state.sh can disagree with driver argv and Step 18 cleanup prefix checks Reuse step-8-ship.sh CLONE_TAG_FULL / clone_basename_prefix logic in the seeder wrapper before writing EXPECTED_TMPDIR_BASENAME_PREFIX
  - From Cursor-Innovation: Reuse the exact CLONE_TAG_FULL block from step-8-ship.sh in both seeder call sites, or extract one shared shell helper and call it from step-8-ship.sh and the SKILL.md seed fences.
  - From Cursor-Pragmatic: Reuse the same CLONE_TAG_FULL derivation as step-8-ship.sh:61-68 in both seeder call sites (Step 8 and Step 5 stall), or extract a shared helper and pin it in test-step-8-ship.sh and test_ship.py




### FINDING_1: Retired session reader path in seeder wrapper contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Generic
- **Severity**: blocking
- **Concern**: The plan’s `step-8-seed-initial` wrapper contract (`.sh` / `.md` around line 54) tells implementers to read session keys via `scripts/read-session-env-key.sh`. That shell script was retired in #3668 (`python/migrated-scripts.tsv`); it is not present in the repo today. Session reads live on `python/cli.py session read-key` (see `step-2-entry.sh`, `step-5-review.sh`). Implementing the plan verbatim causes script-not-found at Step 8 or Step 5 stall seeding, may revive a retired path and fail migration lint, and blocks `seed-initial-state` from ever writing `ship-pr-state.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Match step-2-entry.sh: inline python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" session read-key --file "$IMPLEMENT_TMPDIR/session-env.sh" --key ... --default ...
  - From Cursor-Innovation: Match sibling wrappers (step-2-entry.sh, step-5-review.sh): call python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" session read-key --file "$IMPLEMENT_TMPDIR/session-env.sh" (and ship-pr-state.sh when needed). Update step-8-seed-initial.md contract text accordingly.
  - From Cursor-Pragmatic: Use python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" session read-key --file "$IMPLEMENT_TMPDIR/session-env.sh" (or ship-pr-state.sh when appropriate), matching existing implement wrappers; update step-8-seed-initial.md accordingly.
  - From Cursor-Requirements: Use python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" session read-key --file "$IMPLEMENT_TMPDIR/session-env.sh" internally (match step-5-review.sh), or have seed-initial-state read session-env from --tmpdir inside Python
  - From Codex-Generic: Use the existing python/cli.py session read-key contract, or explicitly add the missing helper if truly required


### FINDING_4: Pre-driver `oos file` failure can be skipped on Step 8 retry
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: After seeding, `ship-pr-state.sh` is non-empty and `OOS_PENDING=false`. If `python/cli.py oos file` fails on first entry, a later retry can follow the planned later-continuation path and invoke only `step-8-ship.sh`, shipping accepted OOS without durable filing evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Rerun the guard and oos file hook on any Step 8 entry where the active driver has not started yet, for example PHASE=checks with no PR_NUMBER; keep seeding create-if-absent but do not classify that state as a post-driver continuation




### FINDING_1: Step 5 stall seed must force MERGE=false and DRAFT=false
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: blocking
- **Concern**: The planned shared seeder (`step-8-seed-initial.sh` / `ship seed-initial-state`) replaces today's stall missing-state prose, which explicitly overrides `DRAFT=false` and `MERGE=false` after copying session values. The plan's stall wrapper only passes `--stall-tracking`, `--stall-step`, and `--bail-reason`, and reads `MERGE`/`DRAFT` from session via `read_session_key`. A `/implement --merge` or `--draft` run that stalls at Step 5 would seed `ship-pr-state.sh` with merge/draft still true, diverging from today's stall contract and changing Step 8+ / final-report / Step 18 stall-recovery semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add explicit stall-only overrides to the seeder contract: --merge false and --draft false (or equivalent Python stall-profile flags) on the Step 5 missing-state wrapper invocation, matching today's forced values.
  - From Cursor-Innovation: Add a stall-seed profile to seed-initial-state (or wrapper flags --merge false --draft false) that mirrors the current stall override block; extend python/test_ship.py stall override test to assert MERGE=false and DRAFT=false when session merge/draft are true.
  - From Cursor-Requirements: Add explicit stall-path overrides in the step5-review-branches.md wrapper example and step-8-seed-initial.sh contract (e.g. --merge false --draft false when --stall-step is set, or a dedicated --stall-seed mode), and extend python/test_ship.py stall-override coverage to assert MERGE=false and DRAFT=false on the Step 5 seed path


### FINDING_2: Missing agent-lint G004 exclusion for planned clone-tag helper
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan adds source-only `skills/implement/scripts/lib-implement-clone-tag.sh` but does not list an `agent-lint.toml` G004 exclusion for it (same pattern as `lib-resolve-implement-tmpdir.sh`). `make lint` / agent-lint G004 scans SKILL.md literal invocations and does not follow shell `source` edges; the clone-tag helper may be flagged unreachable/dead and block the PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add `### UPDATED: agent-lint.toml` (or fold into an existing lint-touch surface): exclude `skills/implement/scripts/lib-implement-clone-tag.sh` and `lib-implement-clone-tag.md` with a sourced-only comment mirroring `lib-resolve-implement-tmpdir.sh`.


### FINDING_4: Seeder wrapper lacks durable sources for required dynamic keys
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The seeder wrapper lacks durable sources for required dynamic keys. The one-line Step 8 fence passes no dynamic argv, `larch-run` only resolves tmpdir/plugin root, and `session-env` does not carry all required seed values such as `BRANCH_NAME`, `ISSUE_NUMBER`, `MANIFEST_PATH`, `TOOL_LABEL`, no-admin, and no-logs. A cold Step 8 seed can write empty or defaulted canonical keys, then ship-pr stalls or loses manifest/no-logs behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Define the wrapper source order per key. Read bootstrap-routing.env for Step 0 routing keys, map LARCH_RUN_ID when needed, and pass or persist Step 2/prompt-only values such as MANIFEST_PATH, TOOL_LABEL, merge/draft, no-admin, and no-logs before seeding. Extend the wrapper harness with realistic Step 0 and Step 2 files.


### FINDING_6:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/stall_recovery.py:1079-1083
- **Concern**: [SCOPE-REDUCTION] Terminal stall seeder change conflicts with the non-goal. Scenario: The approach says to keep stall-recovery seed-terminal-state unchanged, but also says to make the terminal stall path fail closed on a non-empty ship-pr-state.sh. Current terminal recovery rewrites STALL_TRACKING, STALL_STEP, and PHASE into an existing driver state; removing that rewrite can break existing transient-to-stall recovery.
- **Proposed resolution**: Remove the terminal-stall fail-closed bullet. Limit create-if-absent semantics to the new initial ship-pr-state seeder.


