### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: agents/claude-implementer.md
- **Concern**: [SCOPE-REDUCTION] Tier 1 replaces the required `design.plan_revision` autonomous lane with a Claude-only `MODE=plan-revise` carve-out. Scenario: Binding scope requires tier 1 to use the existing autonomous plan-revision machinery (plan-review apply lane). `python/larch/core/config.py` already owns `design.plan_revision` as Codex→Cursor→Claude via `python/cli.py plan revise-waterfall`. The plan routes tier 1 through a second `/design` subagent mode instead, bypassing registry policy (G-Cfg-1), expanding AGENTS/agent surfaces, and conflicting with the non-goal to keep plan-review machinery untouched.
- **Proposed resolution**: Route tier 1 through `design.plan_revision` / `plan revise-waterfall` with a synthetic single-finding input for the named violation or deviation; reserve main-agent tier 2 and fresh `larch:arch-assessor` respawns. Drop `MODE=plan-revise`, `agents/_implementer-base.md`, and the second AGENTS carve-out unless scope is explicitly renegotiated.
