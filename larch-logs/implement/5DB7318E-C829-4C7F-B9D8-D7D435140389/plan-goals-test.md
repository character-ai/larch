## Goal
Implement issue #4725: [IMPLEMENTING] [BUG] design-step3-review premature task-notifications re-engage main agent during review (turn/cost explosion).

## Implementation Plan
## Summary

During `/design` Step 3 (plan review), Claude Code's background-task infrastructure fires premature `<task-notification>` events that re-engage the main agent while reviewers are still running autonomously. Each re-engagement burns a full main-agent turn (context reload, hook evaluation, routing). A two-round review on 2026-06-18 produced five unnecessary re-engagements with zero useful work per turn; the cost compounds at higher round counts.

> **Direction change.** This supersedes the original heartbeat/keepalive fix proposal. The required fix is **deterministic and mechanically enforced**, not a best-effort keepalive that races an undocumented debounce. See **Required solution direction** below.

## Two cost sources (address separately)

1. **Amplifier (the exploding cost).** On a premature notification the orchestrator launches a *background* recovery waiter (`until [ -f … ]; do sleep N; done`). That waiter is itself a zero-output background task, so it fires its own premature notification within seconds, the orchestrator launches another, and a tight re-engagement loop forms: potentially many turns per round. This multiplicative blowup is the primary cost driver.
2. **Base (linear).** The review task (`design-step3-review.sh`) goes silent while reviewers run (5-15 min/round) and fires roughly one notification per silence window / round boundary. Bounded, not exploding.

## Root cause

- **RC1.** Claude Code fires `task-notification` (exit 0) when a background task's output stops for a debounce period. Larch cannot suppress the notification via hook.
- **RC2.** The background recovery waiter produces zero output and is itself a background task, so it becomes a notification *amplifier* (the explosion).
- **RC3.** `plan-review run --mode loop` runs multiple rounds; each round boundary is a fresh silence window.

## Required solution direction (deterministic; `/design` to finalize)

**Primary (mechanically enforced):**

- **Remove the amplifier.** Never launch a background recovery waiter on premature notifications. On any notification, perform a single **foreground, non-sleeping** sentinel probe of `…/.completed/step-3-terminal` and either proceed (sentinel present) or end the turn. A foreground probe returns synchronously and cannot fire a task-notification, so the recovery path stops breeding notifications.
- **Enforce in the guard.** `scripts/hook-bg-poll-guard.sh` must **deny** the background sleep-loop Step 3 recovery waiter (today it *allows* it), forcing the foreground-probe-only path. Keep the foreground terminal-sentinel probe allowed.
- Update the sanctioned recovery protocol to match: `skills/design/SKILL.md` (NEVER #4 + the Step 3 recovery guidance), `skills/shared/orchestrator-never.md`, and the `/implement` orchestrator's equivalent recovery guidance.
- Confirm and document the one platform assumption this relies on: the main review task reliably re-fires a notification on completion (current evidence indicates it does).

**Secondary (optional, defense-in-depth — clearly labeled, never the primary mechanism):**

- A keepalive emitted **deterministically by the Python `plan-review run` driver** (not a bash subshell) MAY dampen the linear base notifications from the main review task. Mitigation only; do not rely on it.

**Likely out of scope** (note explicitly if pursued): foreground time-slicing of the review, blocked today by the ~10-minute foreground Bash cap versus 5-15-minute review rounds.

## Constraints

- **All new logic MUST be Python**, behind `python3 python/cli.py …`, per `.claude/rules/python-first-scripts.md` and `AGENTS.md`. Bash is permitted only for thin delegation wrappers, Claude Code hooks (e.g. `hook-bg-poll-guard.sh`), and CI / pre-commit glue. Put no new decision logic in Bash; existing Bash surfaces must delegate new behavior to `python/cli.py`.
- **Must go through full `/design`** (no `--emergency`): produce a `larch:plan` block, run the review panel, and land tests. This change touches load-bearing surfaces (the hook contract, NEVER #4, orchestrator-never), so it needs proper design plus review.
- Regression coverage: flip the Step 3 recovery-waiter cases in `scripts/test-hook-bg-poll-guard.sh` from allow to deny and add foreground-probe coverage; add Python tests for any new `python/cli.py` logic.

## Evidence (from the original report; still valid)

- `lsof` at a re-engagement showed the Python stdout/stderr handles open with no new bytes written; `kill -0 <pid>` succeeded; `.bg-wait-active` present; `.completed/step-3` absent.
- Recovery-waiter task output files were 0 bytes and each reported `exit_code: 0` within seconds, before the first sleep interval completed.
- `ps aux` showed all review PIDs alive at every re-engagement.
- Final `plan-review` stdout: `LOOP_STATUS=complete ACCEPTED_COUNT=2 ROUNDS_COMPLETED=2`. The review completed correctly; all overhead was wasted main-agent turns.

## Affected surfaces

| Surface | Role |
|---|---|
| `scripts/hook-bg-poll-guard.sh` | Deny the background Step 3 recovery waiter; keep the foreground probe allowed (hook stays thin; heavy logic delegates to `python/cli.py`) |
| `skills/design/SKILL.md` | NEVER #4 and Step 3 recovery guidance to foreground-probe-only |
| `skills/shared/orchestrator-never.md`, `/implement` orchestrator | Parallel recovery-protocol guidance to match |
| `scripts/test-hook-bg-poll-guard.sh` | Flip recovery-waiter allow to deny; add foreground-probe coverage |
| `skills/design/scripts/design-step3-review.sh` | Optional Python-driver keepalive (defense-in-depth only) |
| `python/…` (new) | New recovery-decision / keepalive logic per python-first |

---

*History: this issue originally proposed a bash keepalive in `design-step3-review.sh`, an output-producing recovery waiter in `SKILL.md`, and a widened `hook-bg-poll-guard.sh` regex. That heartbeat approach was rejected as best-effort (it races an undocumented debounce). The original proposal remains in the issue edit history.*

## Test plan
(no test plan section in plan-file)
