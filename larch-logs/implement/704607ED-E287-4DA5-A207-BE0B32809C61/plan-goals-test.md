## Goal
Implement issue #3369: [IMPLEMENTING] [OOS] Health-check timeout default not inherited by /research external launches\n\n- **Description**: Plan mirrors the default into write-session-env for /research, but /research Step 0 runs session-setup without --write-session-env and calls run-external-agent.sh directly from phase markdown. Scenario: Research validation/research lanes never inherit the production default; only /design (source-env export) and fully wired /implement paths benefit.

## Implementation Plan
## Plan

Make the external-launch health gate default ON for every caller. Today `external_launch_health_gate_timeout()` in `scripts/lib-external-launcher-common.sh` returns empty when no source resolves a value, so the gate stays off for callers that never write session-env — including `/research`, standalone `/review`, and offline harnesses that reach `run-external-agent.sh` without intending to exercise the probe. Change the resolver's final fallthrough to the canonical `30` so the production default reaches all callers. `/design` (source-env export) and `/implement` (session-env) already resolve `30` explicitly, so they are unaffected. The behavioral surface is one function; everything else is required contract/doc/test alignment. No `skills/research/**` edits: `/research` Step 0 uses `session-setup.sh` without `--write-session-env` and launches via `run-external-agent.sh` from phase markdown; the read-time `30` fallback closes OOS #3369 by design (intentionally not mirroring the knob into `write-session-env.sh` for research-only runs).

## Files to modify/create

### UPDATED: `scripts/lib-external-launcher-common.sh`
- In `external_launch_health_gate_timeout()`, change the final `return 0` (the no-source fallthrough after the session-file loop) to set the out var to `30` first, then `return 0`.
- Add a one-line comment: this `30` fallback is the canonical default and must stay in sync with `write-session-env.sh` / `write-design-current-env.sh`.
- Leave every earlier return path untouched: an explicit positive value at any source still wins; an explicit numeric `0` at any source still returns empty (opt-out).
- Net effect: only the "nothing resolved anywhere" case changes — empty (gate off) becomes `30` (gate on). A non-numeric or empty env value with no lower-priority override now also coerces to `30`, matching the writers' normalization.

### UPDATED: `scripts/run-external-agent.md`
- Rewrite the "Launch-time health gate" sentence "The gate is enabled only when a positive `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT` resolves ...".
- New meaning: the gate is on by default because the resolver falls back to `30`; an explicit numeric `0` at any source opts out; an explicit positive value overrides the default. Keep the resolution-source order, the never-sourced note, and the 124/143 + fail-open wording byte-stable.

### UPDATED: `scripts/lib-external-launcher-common.md`
- Rewrite the `external_launch_health_gate` bullet clause "The gate is off unless a positive `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT` resolves ...".
- New meaning: the gate is on by default via a `30` resolver fallback; explicit `0` opts out; explicit positive overrides. Keep the source order, the read-through-`read-session-env-key.sh` note, and the probe / fail-open wording.

### UPDATED: `docs/configuration-and-permissions.md`
- Update the `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT` bullet: the `30` default now applies to every `run-external-agent.sh` Codex/Cursor launch via the resolver fallback, not only session-env-writer paths; `0` opts out; a positive value overrides.
- Update the paragraph that begins "`LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT` is auto-on for `/design`, `/implement`, and nested `/review` ...". Remove the "Standalone `/review` and `/research` remain an L1 activation gap ... tracked separately in OOS #3369" caveat. New meaning: the gate is auto-on for all callers via the resolver default; standalone `/review` and `/research` inherit it without session-env writers; this change closes the #3369 gap.

### UPDATED: `scripts/test-lib-external-launcher-common.sh`
- Update the `health gate off without timeout` case (env / session / implement all empty): it now expects the gate ON. Assert rc `1` with present line `CODEX_PRESENT=false` (gate fires, reports unhealthy) and that the `checker-call` file EXISTS. Rename it to reflect default-on (for example `health gate defaults on without explicit timeout`).
- Keep `health gate zero opt-out beats session fallback` unchanged: explicit `0` still opts out (rc `0`, no checker call).
- Add a direct unit assertion on `external_launch_health_gate_timeout`: no source resolves to `30`; an explicit `0` resolves to empty; an explicit positive resolves to that value. This pins the resolver default and detects `30`-literal drift.

### UPDATED: `scripts/test-run-external-agent.sh`
- Change the top-of-file env-reset line that unsets `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT` to instead export `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0`. The non-gate `--tool codex` cases must keep launching the child without a real `check-reviewers.sh` probe; an explicit `0` preserves that isolation under the new default-on behavior.
- Update the `gate-disabled` case (it passes an empty `timeout_value`): an empty value now defaults the gate ON, so repurpose it to assert default-on (`CODEX_PRESENT=false` → exit `7`, child not run, `health-probe fast-fail` diag). Add a separate explicit-`0` opt-out case asserting exit `0` and the child ran. The per-case `env ... LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT="$timeout_value"` override still drives each gate-test case.

### UPDATED: `scripts/test-launch-review.sh`
- Export `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0` at the top-level harness (with the existing `unset`/`export` block) and inside both the `--tool codex` and `--tool cursor` subshells before any `launch-review.sh` invocation that reaches `run-external-agent.sh` without intending to exercise the gate.
- Keeps offline launcher-smoke assertions isolated from the real `check-reviewers.sh` pre-launch probe under the new resolver default-on behavior. Wired by `make test-harnesses-2` (`test-launch-review`); not invoked by `scripts/relevant-checks.sh`.

### UPDATED: `scripts/test-launch-codex-ci.sh`
- Export `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0` with the other top-level harness exports (alongside `LARCH_QUIET_DISABLE`, `IMPLEMENT_TMPDIR`, etc.) before `launch-codex-ci.sh` argv-contract cases that reach `run-external-agent.sh`.
- Same isolation rationale as `test-run-external-agent.sh`. Wired by `make test-harnesses-13` (`test-launch-codex-ci`); not invoked by `scripts/relevant-checks.sh`.

### UPDATED: `scripts/test-launch-cursor-ci.sh`
- Export `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0` with the other top-level harness exports (alongside `LARCH_QUIET_DISABLE`, `IMPLEMENT_TMPDIR`, etc.) before `launch-cursor-ci.sh` argv-contract cases that reach `run-external-agent.sh`.
- Same isolation rationale as `test-launch-codex-ci.sh`. Wired by `make test-harnesses-3` (`test-launch-cursor-ci`); not invoked by `scripts/relevant-checks.sh`.

### UPDATED: `scripts/test-token-vendor-scrapers.sh`
- Export `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0` at harness top (with other exports) and ensure the `launch-cursor-implement.sh` / `launch-codex-implement.sh` record-vendor smoke loop inherits `0` (export before the per-variant `PATH=...` subshell invocations) so stubs are not blocked by `check-reviewers.sh` before `record-vendor` runs.
- Wired by `make test-harnesses-10` (`test-token-vendor-scrapers`); not invoked by `scripts/relevant-checks.sh`.

### UPDATED: `skills/implement/scripts/test-codex-implementer.sh`
- Export `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0` alongside the existing top-level `unset`/`export` block (with `LARCH_EXECUTION_ISSUES_LOG`, `LARCH_TIMING_LEDGER`, `RUN_EXTERNAL_AGENT_POLL_INTERVAL`) before `launch-codex-implement.sh` smoke cases that delegate to `run-external-agent.sh`.
- Wired by `make test-harnesses-10` (`test-codex-implementer`); not invoked by `scripts/relevant-checks.sh`.

### UPDATED: `skills/implement/scripts/test-cursor-implementer.sh`
- Export `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0` alongside the existing top-level `unset`/`export` block before `launch-cursor-implement.sh` smoke cases that delegate to `run-external-agent.sh`.
- Wired by `make test-harnesses-12` (`test-cursor-implementer`); not invoked by `scripts/relevant-checks.sh`.

### UPDATED: `scripts/test-dispatch-code-voters.sh`
- Export `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0` at the top-level harness (with the existing `unset`/`export` block) before any `launch-review.sh` / `run-external-agent.sh` invocation that does not intend to exercise the gate.
- Same isolation rationale as `test-launch-review.sh`. Wired by `make test-harnesses-8`, `test-harnesses-12`, `test-harnesses-13`, `test-harnesses-14`, `test-harnesses-16`, `test-harnesses-17`; not invoked by `scripts/relevant-checks.sh`.

### UPDATED: `scripts/test-dispatch-with-waterfall.sh`
- Export `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0` at the top-level harness before any `launch-review.sh` / `run-external-agent.sh` invocation that does not intend to exercise the gate.
- Same isolation rationale as `test-launch-review.sh`. Wired by `make test-harnesses-19`; not invoked by `scripts/relevant-checks.sh`.

### UPDATED: `scripts/test-collect-agent-retry.sh`
- Export `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0` at the top-level harness before any `launch-review.sh` / `run-external-agent.sh` invocation that does not intend to exercise the gate.
- Same isolation rationale as `test-launch-review.sh`. Wired by `make test-harnesses-16`; part of full `make lint` sweep; not invoked by `scripts/relevant-checks.sh`.

### UPDATED: `scripts/test-collect-agent-results.sh`
- Export `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0` at the top-level harness (with the existing `export LARCH_QUIET_DISABLE` / `TMPDIR` isolation block) before `collect-agent-results.sh` retry paths that invoke `run-external-agent.sh` with `TOOL=cursor` via `.meta` `CMD_JSON`.
- Same isolation rationale as `test-collect-agent-retry.sh`: transient-retry cases must not run the real `check-reviewers.sh` pre-launch probe under the new resolver default-on behavior. Wired by `make test-harnesses-20` (`test-collect-agent-results`); also registered in `scripts/relevant-checks.sh` when `scripts/collect-agent-results.sh` (or this harness) is in the change set.

### UPDATED: `skills/design/scripts/test-plan-review-loop.sh`
- Export `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0` at harness top alongside the existing `RUN_EXTERNAL_AGENT_POLL_INTERVAL` / `WAIT_FOR_REVIEWERS_POLL_INTERVAL` exports (before `run_loop` and before the `STUB_BIN` PATH backstop) so every path that reaches real `dispatch-plan-review-panel.sh` / `collect-agent-results.sh` → `launch-review.sh` → `run-external-agent.sh` stays isolated from the real `check-reviewers.sh` pre-launch probe.
- Critical for the "real panel dispatch + collect with stubbed externals only" block (~1025–1061): it binds real panel/collect scripts with `PATH` stub `codex`/`cursor` only; without opt-out, resolver default `30` runs `check-reviewers.sh` before the stub, so `CURSOR_PRESENT=false` (or probe failure) can fast-fail before the stub writes output/done and break assertions at 1058–1061.
- Wired by `make test-harnesses-1` (`test-plan-review-loop`); runs under full `make lint` — must not be omitted from the pre-merge harness sweep.

## Approach
- One behavioral edit at the resolver layer; everything else aligns contract docs, the user-facing env-var doc, and thirteen offline harnesses that reach `run-external-agent.sh` without session-env and without intending a real health probe.
- Keep the hot path byte-minimal: only the final fallthrough changes; reuse the existing per-source `0`-opt-out and positive-override branches verbatim.
- No `skills/research/**` edits. `/research` research and validation lanes call `run-external-agent.sh` directly from `skills/research/references/research-phase.md` and `validation-phase.md` without persisting `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT` in session-env; the resolver `30` fallback is the intentional fix for that path and closes #3369 without mirroring the knob into `write-session-env.sh` for research-only runs.

## Edge cases
- Explicit `0` (env or any session file): unchanged — gate off (opt-out).
- Explicit positive (env or any session file): unchanged — that value wins.
- Non-numeric / empty env value with no session override: now coerces to `30` (gate on), matching the writers' garbage→30 normalization. Intentional.
- Non-Codex/Cursor tool (`claude`, etc.): still no-ops regardless of timeout.
- `/design` and `/implement`: already resolve `30` explicitly; only the no-source path changed, so they are unaffected.
- `/research` without session-env: now gets gate-on via resolver fallback (intended product behavior, not a harness-only change).

## Failure modes
1. Test-isolation regression in offline harnesses that call launchers → `run-external-agent.sh` without session-env and without intending to exercise the gate: `scripts/test-run-external-agent.sh`, `scripts/test-launch-review.sh` (codex/cursor subshells), `scripts/test-launch-codex-ci.sh`, `scripts/test-launch-cursor-ci.sh`, `scripts/test-token-vendor-scrapers.sh` (implement launcher smoke), `skills/implement/scripts/test-codex-implementer.sh`, `skills/implement/scripts/test-cursor-implementer.sh`, `scripts/test-dispatch-code-voters.sh`, `scripts/test-dispatch-with-waterfall.sh`, `scripts/test-collect-agent-retry.sh`, `scripts/test-collect-agent-results.sh`, and `skills/design/scripts/test-plan-review-loop.sh` (real panel/collect integration block). They previously relied on gate-off (var unset). Earliest signal: smoke cases invoke the real `check-reviewers.sh`, stub Codex/Cursor on PATH fails `larch_run_one_codex_probe`, `run-external-agent` exits `7`/`8` before launcher assertions (e.g. `test-launch-review.sh` codex smoke ~586–603, `test-launch-codex-ci.sh` / `test-launch-cursor-ci.sh` fix-role smoke, implementer harnesses, token-vendor implement record-vendor loop, voter/waterfall/retry dispatch, `test-collect-agent-results.sh` transient-retry paths with `TOOL=cursor` meta, `test-plan-review-loop.sh` real panel/collect ~1058–1061). `scripts/relevant-checks.sh` does not run `make test-harnesses-1`, `2`, `3`, `8`, `10`, `12`, `13`, `14`, `16`, `17`, `19`, or `20` on every edit (it appends `test-collect-agent-results` only when collector paths change), so "lib + run-external harnesses + relevant-checks" alone can miss the break when only the resolver changes — including `make lint` shard `test-harnesses-1`. Mitigation: explicit `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0` at the top of each affected harness (and subshells where env is not inherited); run `make test-harnesses-1`, `make test-harnesses-2`, `make test-harnesses-3`, `make test-harnesses-8`, `make test-harnesses-10`, `make test-harnesses-12`, `make test-harnesses-13`, `make test-harnesses-14`, `make test-harnesses-16`, `make test-harnesses-17`, `make test-harnesses-19`, and `make test-harnesses-20` before merge.
2. Behavior change for standalone `/review` and `/research`. Both now run a pre-launch probe per external reviewer (≤ the resolved `30`s, fail-open on unparseable). Earliest signal: standalone `/review` or `/research` adds a probe step or fast-fails a launch when a tool is unhealthy. Mitigation: documented in `docs/configuration-and-permissions.md`; `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0` opts out. This is the intended systemic outcome.
3. `30`-literal drift. The default now lives in three files (two session-env writers + the resolver). Earliest signal: one default changes while another does not. Mitigation: the sync comment plus the new direct resolver test pinning `30`.

## Testing strategy
- Update and extend `scripts/test-lib-external-launcher-common.sh`: gate default-on case, preserved explicit-`0` opt-out, new direct `external_launch_health_gate_timeout` assertion.
- Update harness opt-out exports: `scripts/test-run-external-agent.sh`, `scripts/test-launch-review.sh`, `scripts/test-launch-codex-ci.sh`, `scripts/test-launch-cursor-ci.sh`, `scripts/test-token-vendor-scrapers.sh`, `skills/implement/scripts/test-codex-implementer.sh`, `skills/implement/scripts/test-cursor-implementer.sh`, `scripts/test-dispatch-code-voters.sh`, `scripts/test-dispatch-with-waterfall.sh`, `scripts/test-collect-agent-retry.sh`, `scripts/test-collect-agent-results.sh`, `skills/design/scripts/test-plan-review-loop.sh`; run-external gate default-on and explicit-`0` cases as already scoped for `test-run-external-agent.sh`.
- Run `bash scripts/test-lib-external-launcher-common.sh`, `bash scripts/test-run-external-agent.sh`, `make test-harnesses-1`, `make test-harnesses-2`, `make test-harnesses-3`, `make test-harnesses-8`, `make test-harnesses-10`, `make test-harnesses-12`, `make test-harnesses-13`, `make test-harnesses-14`, `make test-harnesses-16`, `make test-harnesses-17`, `make test-harnesses-19`, and `make test-harnesses-20`, then `bash scripts/relevant-checks.sh` (or `make lint`).
- Per `.claude/rules/verify-external-tool-invocations.md`: no new external CLI invocation is introduced; the gate keeps calling the existing `check-reviewers.sh`.

## Notes
- No `SECURITY.md` change: the health gate is a reliability feature, not a security boundary.
- No `README.md` change: the feature matrix does not document this knob.
- Default-literal centralization across the writers is an explicit non-goal (Round 1): the writers coerce to `30` at write time, the resolver default is a separate read-time safety net, and the new resolver test gives drift detection without coupling the writers to `lib-external-launcher-common.sh`.

## Acceptance
- With no env and no session files, `external_launch_health_gate_timeout` returns `30` and Codex/Cursor launches run the health probe before the child.
- Explicit `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0` anywhere in the resolution order still disables the gate.
- All listed offline harnesses pass with top-level `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0` without changing their launcher assertions, including `skills/design/scripts/test-plan-review-loop.sh` under `make test-harnesses-1`.
- `docs/configuration-and-permissions.md` documents universal default-on and removal of the #3369 activation-gap caveat.

diff_lines: 165

## Test plan
(no test plan section in plan-file)
