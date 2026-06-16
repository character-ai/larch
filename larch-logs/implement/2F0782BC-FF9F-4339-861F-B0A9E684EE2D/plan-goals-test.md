## Goal
Implement issue #4394: [IMPLEMENTING] [BUG] (URGENT) Vendor agents health check overhaul (Step 0 in particular).

## Implementation Plan
## Plan

## Approach

- Keep existing Step 0 probe retry behavior.
- Use Step 0 probe health only for the operator gate:
  - one vendor down: warn and require explicit Continue unless a prior continue sentinel exists.
  - both vendors down: hard fail in every mode, with no Continue path.
- Remove `CODEX_AVAILABLE`, `CURSOR_AVAILABLE`, `CODEX_PRESENT`, and `CURSOR_PRESENT` from durable session env outputs.
- Keep only `CODEX_PRESENT` and `CURSOR_PRESENT` in immediate `session setup --check-reviewers` stdout for Step 0 gating.
- Stop emitting `CODEX_AVAILABLE` and `CURSOR_AVAILABLE` from `session setup --check-reviewers` stdout.
- Do not use Step 0 probe health to route later vendor calls.
- Route later vendor calls from `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND` or fresh executable checks.
- For fixed reviewer, voter, brainstorm, research, validation, conflict-resolution, dialectic, and implement-dispatch manifests, do not shrink expected external slots because Step 0 probe health was false.
- Let missing binaries, launcher failures, and non-zero exits surface as existing degraded, failed, or dropped external slots.
- Retry only when a vendor binary exists and the launched command exits non-zero.
- Do not retry missing or non-executable binaries.
- Keep legacy `--codex-present`, `--cursor-present`, `--codex-available`, and `--cursor-available` accepted where needed, but ignore them for routing.
- Ensure bootstrap resume gets fresh private probe data or a non-health gate artifact instead of reading stripped env keys.
- Regenerate shared `/design` wrapper preludes so generated script headers do not reintroduce probe-health defaults.

## Files to modify/create

### UPDATED: python/agents.py
- Remove `CODEX_AVAILABLE` and `CURSOR_AVAILABLE` from `CheckReviewersResult.kv()` and `kv_lines()`.
- Keep `CODEX_PRESENT` and `CURSOR_PRESENT` in immediate check-reviewer output.
- Rewrite degraded gate explanation: one down requires explicit operator confirmation; both down cannot proceed; later callers use binary checks and launcher fallback, not Step 0 health.
- Emit a hard-fail marker for both-down, for example `DEGRADED_HARD_FAIL=true`.
- Delete `_external_health_gate()` as a per-launch probe-health routing gate if it still blocks `run_external_agent()`.
- Remove the `_external_health_gate()` call from `run_external_agent()`.
- Ensure missing or non-executable binary diagnostics are non-transient and not outer-retried.
- Preserve current launch retry behavior for commands that start and exit non-zero.
- Remove tests that expect pre-launch probe-health fast-fail behavior.

### UPDATED: python/session_env.py
- Remove all four probe-health globals from `WRITE_ENV_KEYS`, `WRITE_DESIGN_ENV_KEYS`, and `CALLER_ENV_KEYS`.
- Stop emitting `CODEX_AVAILABLE` and `CURSOR_AVAILABLE` from `session setup --check-reviewers` stdout.
- Keep `CODEX_PRESENT` and `CURSOR_PRESENT` in setup stdout only for the immediate Step 0 gate.
- Keep CLI flags for compatibility: `--codex-present`, `--cursor-present`, `--codex-available`, `--cursor-available`.
- Validate legacy health flags when supplied, then discard them.
- Keep writing `CODEX_BINARY_FOUND` and `CURSOR_BINARY_FOUND`.
- Stop recovering prior `CODEX_PRESENT`, `CURSOR_PRESENT`, `CODEX_AVAILABLE`, and `CURSOR_AVAILABLE`.

### UPDATED: skills/design/scripts/design-step0-session.sh
- Parse `CODEX_PRESENT` and `CURSOR_PRESENT` from setup stdout only for the immediate degraded-tools gate.
- Stop parsing `CODEX_AVAILABLE` and `CURSOR_AVAILABLE` from setup stdout.
- Stop passing probe-health flags into `session write-design-env`.
- Continue passing binary-found flags.
- Change status routing: `ok` proceeds; one-down with no sentinel emits `STEP0_STATUS=needs-degraded-decision` and `DEGRADED_PROMPT_REQUIRED=true`; one-down with a prior sentinel emits `STEP0_STATUS=degraded-one-down`; both-down emits `STEP0_STATUS=degraded-both-down-hard-fail` and `DEGRADED_HARD_FAIL=true`.
- Remove `degraded-both-down-auto`.
- Do not create `.degraded-tools-gate-prompted` until the operator chooses Continue.
- Ignore stale sentinels when both vendors are down.

### UPDATED: skills/design/scripts/design-step-prelude.sh
- Remove generated-wrapper defaults that derive `CODEX_AVAILABLE` and `CURSOR_AVAILABLE` from `CODEX_PRESENT` and `CURSOR_PRESENT`.
- Source design env first, then derive any prompt-side attempt flags from `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND` or fresh executable checks.
- Do not export `CODEX_PRESENT`, `CURSOR_PRESENT`, `CODEX_AVAILABLE`, or `CURSOR_AVAILABLE` as routing defaults.
- Keep repo, tmpdir, and quiet-stream setup unchanged.
- Regenerate all generated `skills/design/scripts/design-step*.sh` wrapper headers that duplicate this prelude block.

### UPDATED: python/bootstrap.py
- Stop deriving coder availability from `CODEX_PRESENT` / `CURSOR_PRESENT`.
- Derive `codex_available` and `cursor_available` from binary-found state only, or remove those labels from routing decisions.
- Remove `CODEX_PRESENT`, `CURSOR_PRESENT`, `codex_available`, and `cursor_available` from final implement routing envelopes when they would be interpreted as health facts.
- Keep explicit `--coder codex` / `--coder cursor` behavior, but mark unavailable only when the requested binary is missing.
- For resume and absorbed Step 0 tails, do not call the degraded gate with missing probe values from stripped session env.
- Rerun a private `check-reviewers` probe for the immediate gate, or read only explicit degraded gate status from a non-routing artifact.
- Rework absorbed continue tail: hard-fail both-down in all modes before checkpoint `1.r`; emit `DEGRADED_HARD_FAIL=true` or an equivalent terminal route on both-down; ignore stale degraded sentinel on both-down; emit `DEGRADED_PROMPT_REQUIRED=true` only for one-down without sentinel; proceed on one-down only when an explicit continue sentinel already exists.
- Stop emitting durable `CODEX_PRESENT` / `CURSOR_PRESENT` as routing facts.

### UPDATED: python/implement_dispatch.py
- Stop refusing Cursor dispatch because `CURSOR_PRESENT=false`.
- Gate Cursor dispatch on `CURSOR_BINARY_FOUND=true` or a fresh executable check.
- Apply the same binary-only guard to Codex if present.
- Keep legacy `CURSOR_PRESENT` / `CODEX_PRESENT` parsing only for compatibility, not routing.
- Preserve explicit coder selection semantics.

### UPDATED: skills/implement/references/step2-dispatch.md
- Replace Step 2 dispatch routing text that forwards or gates on `CURSOR_PRESENT`.
- Document `CURSOR_BINARY_FOUND` or a fresh executable check as the only prompt-side Cursor dispatch guard.
- Mark `CURSOR_PRESENT` and `CODEX_PRESENT` compatibility-only when old env or argv examples remain.
- State that stale probe-health false must not block an explicitly selected vendor when the binary exists.

### UPDATED: skills/implement/references/conflict-resolution.md
- Rework conflict-resolution Phase 3 external review routing away from `CODEX_PRESENT` and `CURSOR_PRESENT`.
- Use `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND` or fresh executable checks for prompt-side impossible-command guards.
- Keep Claude fallbacks only for missing binaries, launcher failures, or existing fallback paths.
- Align the reference with `skills/shared/external-reviewers.md`.

### UPDATED: python/review_and_fix.py
- Stop rehydrating `CODEX_PRESENT` and `CURSOR_PRESENT` into process env.
- Stop using probe health to skip `_run_coder_codex()` or `_run_coder_cursor()`.
- Update lint-fix and Step 5 fixer loops to use `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND` or `shutil.which()`.
- Keep auth preflight and launcher failure handling unchanged.
- Do not export probe-health-derived env vars to downstream fix paths.

### UPDATED: python/checks.py
- Stop using `CODEX_PRESENT` / `CURSOR_PRESENT` to decide lint-fix or relevant-check fixer eligibility.
- Use `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND` from the run env when present.
- Fall back to fresh executable checks when binary-found state is absent.
- Preserve current non-zero launcher failure handling.

### UPDATED: python/run_context.py
- Stop treating `CODEX_PRESENT` and `CURSOR_PRESENT` from source env files as current routing facts.
- Preserve old values only as nullable historical metadata where summaries need them.
- Prefer `CODEX_BINARY_FOUND` and `CURSOR_BINARY_FOUND` for current availability labels.

### UPDATED: python/ship.py
- Thread binary-found semantics through ship checks and lint-fix paths.
- Do not derive Codex or Cursor fixer availability from Step 0 probe health.
- Preserve existing ship failure and fallback behavior.

### UPDATED: python/oos_filer.py
- Replace `LARCH_OOS_CODEX_AVAILABLE` as a probe-health routing input.
- Prefer binary presence via `CODEX_BINARY_FOUND` when provided, else `shutil.which("codex")`.
- Keep an explicit test override only if existing tests need it, but document it as binary-present semantics.

### UPDATED: python/plan_quality.py
- Stop building auto-fix vendor order from `--codex-present`, `--cursor-present`, `--codex-available`, or `--cursor-available`.
- Keep those arguments accepted for CLI compatibility.
- Build auto-fix and revise-waterfall tiers from binary-found args or fresh executable checks.
- Preserve Claude fallback when no external binary is available or all external attempts fail.

### UPDATED: python/plan_review.py
- Update embedded plan-review panel dispatch so slots are not gated on Step 0 probe health.
- Update embedded plan-voter dispatch so external voters are not suppressed by stale `CODEX_PRESENT` / `CURSOR_PRESENT=false`.
- Use binary-derived attempt flags or unconditional external slot attempts where the manifest should expose degradation.
- Preserve no-fallback behavior for duplicate judge prevention.

### UPDATED: skills/design/references/plan-review.md
- Rewrite normative panel dispatch instructions so Step 3 does not gate Codex or Cursor slots on Step 0 `CODEX_PRESENT` / `CURSOR_PRESENT`.
- Remove or deprecate `--codex-available` / `--cursor-available` as Step 0 health-routing argv.
- State that failed or missing external vendors surface as failed, dropped, or degraded slots through launcher behavior.

### UPDATED: skills/design/references/brainstorm.md
- Rewrite Step 1d.5 brainstorm lane launch guards away from Step 0 `codex_available` / `cursor_available`.
- Use `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND` or fresh executable checks for prompt-side impossible-command guards.
- Mark any remaining `codex_available`, `cursor_available`, `CODEX_PRESENT`, or `CURSOR_PRESENT` language as historical or compatibility-only, not routing.

### UPDATED: skills/research/references/research-phase.md
- Rebind research lane eligibility away from Step 0 probe-health globals and mental flags derived from them.
- Use `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND` or fresh executable checks for prompt-side impossible-command guards.
- Remove or mark as compatibility-only any `CODEX_AVAILABLE`, `CURSOR_AVAILABLE`, `CODEX_PRESENT`, `CURSOR_PRESENT`, `codex_available`, or `cursor_available` language that affects lane launch decisions.

### UPDATED: skills/research/references/validation-phase.md
- Rebind validation lane eligibility away from Step 0 probe-health globals and mental flags derived from them.
- Remove validation status wording that records `fallback_presence_failed` solely because Step 0 probe health was false.
- Align validation routing language with `skills/shared/external-reviewers.md` and `skills/research/SKILL.md`.

### UPDATED: skills/shared/dialectic-protocol.md
- Rebind judge and retry eligibility away from `CODEX_AVAILABLE`, `CURSOR_AVAILABLE`, `CODEX_PRESENT`, and `CURSOR_PRESENT`.
- Use `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND` or fresh executable checks for prompt-side impossible-command guards.
- Keep dialectic debater and judge slots from being replaced by Claude solely because Step 0 probe health failed.

### UPDATED: python/plan_scout.py
- Stop using `cursor_present` from Step 0 probe health to decide whether to attempt Cursor scout.
- Keep legacy args accepted for caller parity.
- Derive scout tier attempts from binary presence or explicit binary-found args.

### UPDATED: python/decompose.py
- Stop using `codex_present` and `cursor_present` probe-health args to decide decompose panel or aggregate vendor slots.
- Keep legacy args accepted and validated.
- Derive decompose external slots from binary presence or unconditional per-manifest attempt semantics.

### UPDATED: python/legacy_review_shell/review-core.sh
- Stop using `CODEX_AVAILABLE` and `CURSOR_AVAILABLE` as Step 0 health gates for review routing.
- Keep deprecated args accepted and validated when supplied.
- Convert reviewer and voter routing to binary-derived attempt flags or unconditional attempted slots.

### UPDATED: python/legacy_review_shell/dispatch-panel.sh
- Treat `--codex-available` and `--cursor-available` as deprecated compatibility aliases.
- Stop interpreting them as Step 0 probe health.
- Use binary presence or unconditional external-slot launch.
- Keep the existing panel topology and fallback behavior.

### UPDATED: python/legacy_review_shell/tally-code-votes.sh
- Stop lowering expected code-vote counts based on `CODEX_AVAILABLE` / `CURSOR_AVAILABLE`.
- Keep deprecated args accepted for compatibility.
- Count configured external voters consistently with the dispatch manifest.

### UPDATED: scripts/dispatch-code-voters.sh
- Treat `--codex-available` and `--cursor-available` as deprecated compatibility aliases.
- Do not skip voter slots because Step 0 probe health was false.
- Keep `--no-fallback`.
- Keep expected judge counts stable for Claude, Codex, and Cursor when the manifest includes those voters.

### UPDATED: scripts/dispatch-with-waterfall.sh
- Clarify `--codex-present` and `--cursor-present` as per-call attempt flags.
- Keep `--codex-available` and `--cursor-available` aliases for compatibility.
- Do not read global probe-health env vars for routing.

### UPDATED: scripts/lib-external-launcher-common.sh
- Ensure launcher health or executable guards check the real binary path before retry loops.
- If the binary is missing or not executable: emit a fast-fail diagnostic; return unhealthy immediately; do not sleep; do not call Step 0 probe logic.
- Keep retry behavior for executable binaries that run and return probe or launcher failures.

### UPDATED: skills/design/scripts/design-step2b-drafter.sh
- Stop preferring Codex from `CODEX_PRESENT`.
- Prefer Codex when `CODEX_BINARY_FOUND=true` or a fresh executable check succeeds.
- Keep `LARCH_DESIGN_DRAFTER=codex|claude` override behavior.

### UPDATED: skills/design/scripts/design-step-validator-autofix.sh
- Stop passing `CODEX_PRESENT`, `CURSOR_PRESENT`, `CODEX_AVAILABLE`, and `CURSOR_AVAILABLE` into plan autofix as routing inputs.
- Pass binary-found flags if the CLI keeps explicit binary args.

### UPDATED: skills/design/scripts/review-design-step3-loop.sh
- Stop passing `CODEX_PRESENT` and `CURSOR_PRESENT` from sourced design env into `plan revise-waterfall`.
- Pass binary-derived attempt flags or omit legacy flags after the Python CLI makes them optional.

### UPDATED: skills/design/scripts/design-step3-review.sh
- Bind Step 3 panel and voter launch eligibility from `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND` or fresh executable checks.
- Remove or mark as compatibility-only any gate on `CODEX_PRESENT` / `CURSOR_PRESENT` from source env.
- Keep external-slot launch attempts where binary is present; let launcher failures surface as degraded results.

### UPDATED: skills/design/references/decompose-panel.md
- Update decompose panel dispatch instructions to use binary-derived attempt flags.
- Stop gating Codex or Cursor decompose slots on Step 0 probe health.
- Keep Claude fallback for missing binaries.

### UPDATED: skills/design/SKILL.md
- Update Step 0 instructions to stop binding `codex_available` / `cursor_available` from probe health.
- Route `degraded-both-down-hard-fail` as terminal (print error, exit non-zero, no AskUserQuestion).
- Route `needs-degraded-decision` through a prominent Continue / Abort `AskUserQuestion`.
- Remove `degraded-both-down-auto`.
- Remove prose that says the degraded gate does not flip `codex_available` / `cursor_available`.
- Update later vendor-launch prose to use binary-found state or launcher fallback.

### UPDATED: skills/implement/SKILL.md
- Update Step 0 bootstrap absorbed-continue-tail instructions for both-down hard-fail.
- Update vendor-launch prose to use binary-found state.
- Remove `degraded-both-down-auto` references.

### UPDATED: skills/review/SKILL.md
- Update reviewer and voter dispatch prose to use binary-found instead of probe-health globals.
- Mark deprecated `--codex-available` / `--cursor-available` args as compatibility-only.

### UPDATED: skills/research/SKILL.md
- Update Step 0 and research-lane launch prose to use binary-found state.
- Remove or mark as compatibility-only any `codex_available` / `cursor_available` mental-flag language.

## Edge cases

- Re-entry after one-down Continue should not re-prompt.
- Re-entry after both-down must still fail, even with a stale sentinel.
- Non-interactive one-down without a sentinel must not auto-proceed.
- Empty `CODEX_PRESENT` or `CURSOR_PRESENT` from setup remains fail-safe down for Step 0 only.
- Old session env files may contain probe-health globals; current routing must ignore them.
- Binary presence is not health. A found binary can still fail and should use existing launcher handling.
- A missing binary should fail or skip before launcher retry paths.

## Failure modes

- If `session write-design-env` drops binary-found keys, later vendor routing may fall back incorrectly.
- If both-down returns a generic setup failure, the operator may miss the hard-fail reason.
- If stale sentinels are honored on both-down, the new hard-fail contract is violated.
- If review or voter expected counts still shrink from probe health, degraded slots may disappear silently.
- If `run_external_agent()` tests still expect health-gate exit codes, they will fail after deleting `_external_health_gate()`.

## Testing strategy

- Run focused Python tests: `python3 -m pytest python/test_agents.py python/test_session_env.py python/test_bootstrap.py` and `python3 -m pytest python/test_implement_dispatch.py python/test_review_and_fix.py python/test_oos_filer.py`
- Run focused shell tests: `scripts/test-dispatch-code-voters.sh` and `scripts/test-design-structure.sh`
- Run required repo checks: `make py-lint`, `make py-test`, `make lint`
- Manually inspect Step 0 wrapper output for healthy, Codex-only down, Cursor-only down, both-down, one-down re-entry, and both-down stale-sentinel re-entry.
- Verify `/design` source env no longer contains probe-health globals.
- Verify source env and implement session env still contain binary-found keys when known.

## Acceptance

- Step 0 hard-fails with no prompt when both vendors are down.
- Step 0 warns and confirms when exactly one vendor is down; Continue sentinel is honored on re-entry.
- `CODEX_AVAILABLE`, `CURSOR_AVAILABLE`, `CODEX_PRESENT`, and `CURSOR_PRESENT` are absent from `source-env.sh` and `session-env.sh` after a normal run.
- `CODEX_BINARY_FOUND` and `CURSOR_BINARY_FOUND` are present in session env when known.
- `_external_health_gate()` is deleted; `run_external_agent()` attempts launch without a pre-launch health gate.
- Review, voter, brainstorm, research, validation, decompose, and conflict-resolution manifests gate slots on binary-found state only; stale probe-health false does not shrink manifests when binaries exist.
- Implementer coder selection uses binary-found state; stale probe-health false does not trigger a fallback when the requested binary exists.
- All Python and shell tests pass.

review_status: complete
rounds_completed: 5
diff_lines: 1560

## Test plan
(no test plan section in plan-file)
