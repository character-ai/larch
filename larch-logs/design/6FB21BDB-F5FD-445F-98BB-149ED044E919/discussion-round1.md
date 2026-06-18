## Decision 1: Fix scope
- **Question**: Which of the four suggested fixes in issue #4688 are in-scope?
- **Resolution**: Fix the definite `step-5c-terminal`→`step-5c` sentinel mismatch (Fix 1), and add a guard-compatible recovery path so a premature `<task-notification>` no longer forces 180+ foreground `ps` polls (Fixes 2+3). Defer the uncertain harness-level premature-notification root cause (Fix 4) — it is not reliably fixable inside larch.
- **Source**: user

## Decision 2: Recovery mechanism
- **Question**: How should the guard let the orchestrator cheaply recover after a premature notification when the wrapper PID is still alive and `run_in_background` recovery waiters are killed (exit 144)?
- **Resolution**: Whitelist a single lightweight, non-sleeping foreground sentinel probe (a `[ -f "$DESIGN_TMPDIR/.completed/step-N" ]`-style file test that echoes DONE/WAIT) past `hook-bg-poll-guard.sh` while `.bg-wait-active` is live. The probe is read-only, references only the completion sentinel (never progress/result artifacts), and contains no sleep — so the anti-polling protection is preserved.
- **Source**: user

## Decision 3: Sentinel-mismatch fix direction
- **Question**: Fix the mismatch by changing the hook to expect `.completed/step-5c`, or by making `design-step5c.sh` write `.completed/step-5c-terminal`?
- **Resolution**: Change `hook-bg-poll-guard.sh` to expect `.completed/step-5c`, matching what `design-step5c.sh` already writes and the `.completed/step-N` convention used by every other guarded step. Do NOT modify `design-step5c.sh`. (Minimum change.)
- **Source**: codebase

## Hard constraints
- The recovery affordance MUST NOT reopen the anti-polling hole the guard exists to close: no whitelist for progress/result artifacts (`.step3-review-result.env`, task-output files), no sleep loops, no repeated progress polling.
- Keep the change minimal and surgical: `scripts/hook-bg-poll-guard.sh` (sentinel fix + recovery whitelist) plus the recovery guidance the SKILL surface relies on. Avoid touching the broader review-loop control flow.
- Defer Fix 4 (premature-notification root cause) — harness-level and uncertain; candidate for an OOS follow-up / upstream report.
