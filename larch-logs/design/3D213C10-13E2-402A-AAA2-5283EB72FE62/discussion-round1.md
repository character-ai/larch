## Decision 1: Fast-fail strategy
- **Question**: How should the fast-fail health check work, given check-reviewers.sh already provides a bounded (30s) cached (60s TTL) real probe at session start?
- **Resolution**: Reuse the existing check-reviewers.sh probe machinery at launch time. Before an external launch, consult the per-tool stamp cache; on a fresh+healthy verdict trust it and launch; on a fresh+unhealthy verdict skip the launch immediately; on a stale stamp re-probe bounded by the new timeout. On unhealthy, skip the real launch so the caller's existing waterfall degrades to Claude instead of waiting the full 20-30 min `--timeout`. Do NOT add a generic no-output stall watchdog (Cursor buffers stdout to 0 bytes until exit → false-positives on healthy Cursor).
- **Source**: user

## Decision 2: Activation / backward compatibility
- **Question**: On by default in production, or opt-in via env var? Tests use stub binaries and CI must stay green.
- **Resolution**: On by default in production with a sensible bounded timeout. Skipped (a) when the session stamp is fresh+healthy (no re-probe), and (b) under test-mode / CI / stub-binary harnesses via an explicit disable signal so existing run-external-agent.sh harnesses and stub-driven tests are unaffected. Must not alter timing or behavior of currently-passing tests.
- **Source**: user

## Decision 3: Scope breadth
- **Question**: How broad across run-external-agent.sh, plan-review-loop.sh, and launcher libs?
- **Resolution**: All three named shell surfaces, AND the counterpart Python code in the `python/` ship-pr.sh rework tree (modify for parity). The primary behavior lives at the shared chokepoint so all callers inherit it; plan-review-loop.sh and the launcher libs are audited/wired explicitly per the parity rule.
- **Source**: user

## Decision 4: Env var name + reuse of existing knobs
- **Question**: New env var name and how it relates to existing LARCH_PROBE_TIMEOUT_SECONDS (30s) / LARCH_PROBE_TTL_SECONDS (60s).
- **Resolution**: Introduce `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT` (per the issue) to bound the launch-time re-probe; reuse the existing 60s stamp-cache TTL (LARCH_PROBE_TTL_SECONDS) for freshness and the existing stamp files written by check-reviewers.sh. Avoid proliferating overlapping knobs.
- **Source**: codebase + issue

## Decision 5: Python counterpart shape
- **Question**: What does "modify the Python counterpart accordingly" require?
- **Resolution**: Add the `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT` env-var name + default to python/config.py (parity constant), ensure python/checks.py and python/agents.py launches propagate process env (already inherited via runner.run, so the shell-level gate fires transitively), and add a bash-vs-Python parity assertion. Do NOT wire the Python tree into the live `/implement` path — it stays dev/CI-only (stdlib-only) until Phase 7.
- **Source**: codebase (python/README.md, AGENTS.md)

## Hard constraints (must not break)
- All existing tests and CI must stay green; stub-binary harnesses for run-external-agent.sh must not trigger a real probe.
- The fast-fail must integrate with the existing per-slot waterfall: emit a health-class failure so dispatchers fall through (Codex→Cursor→Claude) rather than short-circuiting as an `other`-class failure.
- Bash 3.2 portability; `set -euo pipefail`; lib-quiet FD-3 contract; sibling `.md` updates for every touched `.sh`; external-tool launcher parity (Codex + Cursor symmetric; cross-doc supported-tool lists) per .claude/rules.
- Update docs/configuration-and-permissions.md (Environment Variables) and SECURITY.md if security-relevant.

## Non-goals
- Sub-cache-TTL mid-run detection (a tool that degrades within the freshness window after a healthy probe is caught only on the next launch past TTL).
- Replacing the session-level check-reviewers.sh probe or the `*_PRESENT` gating semantics.
- A generic no-output stall watchdog in run-external-agent.sh (rejected: Cursor buffering).
- Wiring the Python ship-pr rework into the live path (deferred to Phase 7).
