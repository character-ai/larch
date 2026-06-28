## Goal
Implement issue #5711: [IMPLEMENTING] [OOS] Narrow the Claude degraded-auth fast-fail regex to exclude the benign connectors-disabled message.

## Implementation Plan
## Out-of-Scope Observation

**Surfaced by**: Main agent

**Phase**: implement

**Vote tally**: N/A — auto-filed per policy


## Description

`python/larch/agents/agents.py` `_run_claude_with_stdin` (~line 6091) breaks the polling loop and returns `config.EXIT_TIMEOUT` (124) when `_CLAUDE_DEGRADED_AUTH_RE` matches the stderr tail within `_CLAUDE_AUTH_FAST_FAIL_WINDOW` (60s). `_CLAUDE_DEGRADED_AUTH_RE` (defined ~line 61) includes `claude.ai connectors are disabled` and `takes precedence over your claude.ai login`, which are parts of a benign informational message that prints on successful runs too; issue #5677 calls it a red herring (roughly 41/50 successful voter runs carry it on stderr). If that benign line reaches the stderr file during the 60s window, a healthy Claude voter can be killed as a false-positive `EXIT_TIMEOUT`, surfacing as the "claude subprocess timed out" voter failures. Investigate whether the benign line is flushed during the window (versus only at process exit); if so, narrow the fast-fail trigger to require a genuinely degraded signal (for example `apiKeyHelper failed` or `did not return a value`) and exclude the benign connectors-disabled line, or require co-occurrence with a real hang. The change must not regress #5605's intended degraded-auth fast-fail; add regression coverage in `python/test_agents.py`. Context: the #5677 bounded voter retry mitigates the separate "No messages returned from query" failure mode but not this false-positive fast-fail mode.

---
*This issue was automatically created by the larch `/implement` workflow from an out-of-scope observation surfaced during the workflow.*

## Test plan
(no test plan section in plan-file)
