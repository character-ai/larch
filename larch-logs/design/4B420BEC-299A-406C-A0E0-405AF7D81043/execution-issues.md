### External Reviewer Issues

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-cursor-plan-semantics-guard.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-semantics-guard.txt)

I'll search the repo for the plan and how each timeout knob is handled in code and tests.
**Verdict:** The plan in `~<TMPDIR>/plan.txt` **mostly preserves per-knob semantics** by keeping two separate parsers. A few test and surface gaps could let a future refactor collapse them.


- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-cursor-plan-scope-guard.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-scope-guard.txt)

Searching for the plan and issue #4756 to review scope against the stated constraints.
The plan file is in the design session cache; reading it and the cited code paths next.
**Verdict:** The plan at `plan.txt` (session `claude-design-larch2-63rlhe1h`) stays within scope. It is a defaults-plus-docs/tests bump only. No retry-budget logic, no new env vars, and no per-attempt vs total model change. Nothing listed belongs in #4756.


- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-codex-plan-scope-guard.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-codex-plan-scope-guard.txt)

Scope creep found in `larch-logs/design/04E1791D-8A00-44A8-971E-45B558C60344/plan.txt`.


- **findings aggregator**: merged output failed validation; leaving <TMPDIR>/findings-in-scope.md unchanged. See <TMPDIR>/aggregator-validate.stderr.
### FINDING_1: Timeout-retry budget and new env var exceed default-bump scope
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: `larch-logs/design/04E1791D-8A00-44A8-971E-45B558C60344/plan.txt:18-29`, `:96-103`, `:177-191`
- **Concern**: The plan adds `LARCH_PROBE_TIMEOUT_RETRIES`, independent timeout retry accounting, and `(N + 1) * LARCH_PROBE_TIMEOUT_SECONDS` total-attempt docs. That violates the requested scope: **no retry-budget logic**, **no new env vars**, and **no per-attempt versus total timeout model change**.
- **Code paths**: Existing timeout default is read at `python/agents.py:947-960`. Timeout-retry mechanics live at `python/agents.py:657-659`, `:885-927`, with tests at `python/test_agents.py:1188-1343`.
- **Proposed resolution**: Drop all timeout-retry/env-var bullets. Limit the plan to bumping the existing `LARCH_PROBE_TIMEOUT_SECONDS` default and updating docs/tests that pin the old default. Move retry-budget model work to **#4756**.

### FINDING_2: Non-default-bump #4756 work is bundled into this plan
- **Severity**: blocking
- **Focus area**: risk-integration
- **Location**: `larch-logs/design/04E1791D-8A00-44A8-971E-45B558C60344/plan.txt:30-51`, `:53-94`, `:115-201`, `:237-244`
- **Concern**: The plan includes Cursor keychain mutex changes, diagnostic resolver changes, bounded diagnostic reads, collector stderr-tail ordering, plan-review-panel redaction, `SECURITY.md`, and design-drafter tests. None are required for a **defaults + docs/tests** bump.
- **Code paths**: Default-only work should stay near `python/agents.py:956`, `docs/configuration-and-permissions.md:240-249`, and the relevant default-pinning tests. The extra surfaces are separate #4756 implementation areas.
- **Proposed resolution**: Remove those file sections from this plan. Keep them in **#4756** or follow-up issues.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-scope-guard.txt.diag)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-scope-guard.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-codex-plan-scope-guard.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-scope-guard.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-scope-guard.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
⏳ codex agent: still running (3m elapsed)
✓ codex agent: completed (exit code 0, output 1944 bytes)
  ```
### In-Scope Findings

- **risk-integration** `plan.txt` **## Approach** (lines 3–7), **### UPDATED: python/agents.py** (lines 11–17), **## Failure modes** (lines 62–66) — Scope boundaries are explicit: default bump only; no `LARCH_PROBE_TIMEOUT_RETRIES` work; no TTL/auth/transient/timeout-retry edits. That matches `plan-review-scope-anchor.txt` **Non-goals** (lines 54–57). **Suggested fix:** None.

- **risk-integration** `plan.txt` **### UPDATED: python/agents.py** (lines 13–17) vs `python/agents.py:956–959` — The only runtime change is the `_env_int(..., 30, ...)` default literal. Existing #4756 paths (`_max_timeout_probe_retries()` at `657–658`, `max_timeout_retries` wiring at `959`, timeout-retry loops at `885–895`) are left untouched. **Suggested fix:** None.

- **risk-integration** `plan.txt` **### UPDATED: python/session_env.py** (lines 19–25) vs `python/session_env.py:274–276` — Only `_external_timeout()` fallback literals change (`"30"` → `"60"`). `value.isdigit()` and `"0"` opt-out stay. No shared parser with `LARCH_PROBE_TIMEOUT_SECONDS`. **Suggested fix:** None.

- **risk-integration** `plan.txt` **Files to modify/create** (lines 9–53) vs #4756 plan `larch-logs/design/04E1791D-8A00-44A8-971E-45B558C60344/plan.txt` — Surfaces are limited to `agents.py`, `session_env.py`, `docs/configuration-and-permissions.md`, `test_agents.py`, `test_session_env.py`. None of #4756’s other headings appear (`agent_voters.py`, `collect_results.py`, `plan_review_panel.py`, keychain mutex, diagnostic resolver, `LARCH_PROBE_TIMEOUT_RETRIES` docs). **Suggested fix:** None.

- **correctness** `plan.txt` **## Approach** (lines 5–7), **### UPDATED: docs/configuration-and-permissions.md** (lines 27–34) vs `docs/configuration-and-permissions.md:246–250` — Per-knob semantics stay split: `LARCH_PROBE_TIMEOUT_SECONDS` stays per-attempt with invalid/empty/`0` → default; `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT` keeps `0` opt-out. Only numeric defaults move 30 → 60. **Suggested fix:** None.

### Out-of-Scope Observations

- `python/config.py:147` defines `EXTERNAL_HEALTH_CHECK_TIMEOUT_DEFAULT_SEC: Final = 30`. The plan does not list `config.py`. Runtime uses `session_env._external_timeout()` (`274–276`), not this constant, so behavior is still covered. Leaving `147` at `30` is a parity/doc drift risk, not scope creep into #4756. A `60` update would still fit this issue’s “defaults bump” charter.

- `docs/external-reviewers.md` mentions `LARCH_PROBE_TIMEOUT_RETRIES` (#4756) but not the `30` probe default. The plan correctly omits it; no creep, possible follow-up doc sync only.

- `plan-review-scope-anchor.txt` **Current behavior** (line 20) still says timeout exits are “not retried.” Main already has timeout retries (`python/agents.py:891–895`). That anchor text is stale post-#4756; this plan does not re-open that work and correctly says “do not change … timeout retry logic” (`plan.txt:17`).
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-scope-guard.txt.diag)

(empty: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-scope-guard.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-scope-guard.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-scope-guard.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-scope-guard.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
⏳ cursor agent: still running (4m elapsed)
⏳ cursor agent: still running (5m elapsed)
✓ cursor agent: completed (exit code 0, output 3760 bytes)
  ```
### In-Scope Findings

- **per-knob semantics** `plan.txt` **Approach** (lines 4–7) and **### UPDATED: python/agents.py** / **### UPDATED: python/session_env.py** — The plan correctly keeps divergent zero handling: probe timeout via `_env_int(..., zero_allowed=False)` (invalid/empty/`0` → default `60`) versus health-check via `_external_timeout()` `isdigit()` gate (`"0"` preserved, non-digit → `"60"`). That matches current code at ```639:646:python/agents.py``` and ```274:276:python/session_env.py```. **Suggested fix:** None on structure; keep these as separate code paths during implementation.

- **missing validation** `plan.txt` **### UPDATED: python/test_agents.py** (lines 36–42) vs **Edge cases** (line 60) — The plan only updates `test_check_reviewers_invalid_env_normalization` for `"bad"` → `[60, 60, 60]` (current assertion at ```1063:1070:python/test_agents.py```). **Edge cases** requires `LARCH_PROBE_TIMEOUT_SECONDS=0` still falls back via `zero_allowed=False`, but no test is planned for `"0"` or `""`. A refactor that routes both knobs through one `_env_int` helper would pass CI. **Suggested fix:** Add parametrized `check_reviewers` cases for `LARCH_PROBE_TIMEOUT_SECONDS` in `("0", "", "bad")` asserting timeout `60`, alongside the existing invalid test.

- **missing validation** `plan.txt` **### UPDATED: python/test_session_env.py** (lines 44–53) vs **Edge cases** (line 57) — Planned `_external_timeout()` tests cover unset, non-digit, `"0"`, and `"45"`. **Edge cases** also requires empty string → `"60"`, but the test bullet only says “Non-digit value.” Empty is covered logically, not explicitly named. **Suggested fix:** Add an explicit `monkeypatch.setenv(..., "")` case asserting `"60"`, and a distinct `"0"` → `"0"` case so opt-out cannot regress.

- **drift risk** `plan.txt` **Files to modify/create** (no `python/config.py` entry) — `EXTERNAL_HEALTH_CHECK_TIMEOUT_DEFAULT_SEC: Final = 30` at ```147:147:python/config.py``` is not listed. `_external_timeout()` uses hardcoded `"30"` literals today (```275:276:python/session_env.py```). Bumping only session_env/agents leaves a stale named constant that a DRY refactor could wire in with `zero_allowed=False`, breaking `"0"` opt-out. **Suggested fix:** Add **### UPDATED: python/config.py** bumping the constant to `60`, or a plan note forbidding reuse of that constant in `_external_timeout()` without preserving `isdigit()` zero semantics.

- **normalization footgun** `plan.txt` **Failure modes** (line 64) — The plan warns against shared semantics but does not forbid a shared helper in the code sections. An implementer could “simplify” both knobs through `_env_int(..., zero_allowed=False)` and silently remove health-gate opt-out. **Suggested fix:** Add an explicit constraint under **### UPDATED: python/session_env.py**: “Do not route `_external_timeout()` through `_env_int` or any helper that maps `0` to the default.”

### Out-of-Scope Observations

- **Plan preserves semantics; current tree already implements the split.** No planned change normalizes the two knobs into one rule. The risk is incomplete tests and a missing `config.py` touch during a literal-only bump.

- **`probe_timeout_seconds or _env_int(...)`** at ```956:956:python/agents.py``` treats `probe_timeout_seconds=0` as falsy and falls through to env parsing. The plan says “Do not change `probe_timeout_seconds` override behavior,” so this pre-existing quirk remains. It is separate from `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0` opt-out (session-env / gate disable), not probe per-attempt timeout.

- **`_external_health_gate()` is absent** from current `python/agents.py`; docs still describe launch-time health gating (`docs/configuration-and-permissions.md` lines 250–254). That is doc/runtime drift, not introduced by this plan.

- **Related #4756 plan** (`larch-logs/implement/23DAC8E4-EE0F-4743-A440-FEE99676625A/plan-goals-test.md`, **Approach** lines 11–14) adds `LARCH_PROBE_TIMEOUT_RETRIES` via `_env_int(..., 0)` with `zero_allowed=True` (```657:658:python/agents.py```). That is a third, distinct knob; it does not conflate probe-timeout seconds with health-check timeout.

- **`config.EXTERNAL_HEALTH_CHECK_TIMEOUT_DEFAULT_SEC` is unused** in runtime Python today; drift risk is latent unless something starts importing it.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-semantics-guard.txt.diag)

(empty: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-semantics-guard.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-semantics-guard.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-semantics-guard.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-semantics-guard.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
✓ cursor agent: completed (exit code 0, output 5051 bytes)
  ```
