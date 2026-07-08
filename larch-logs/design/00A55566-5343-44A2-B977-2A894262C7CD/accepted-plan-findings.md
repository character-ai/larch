### FINDING_1: Final report emit ordering still allows stale or pre-cleanup output
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: The green `/implement` path still has conflicting terminal-report ownership rules: Step 18b, finalize-done handling, and the anti-halt boundary disagree about whether a cached Step 17 body or refreshed Step 18 markers should own the final emit. That can either show stale cost/timing data or keep the report from being the last visible output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `skills/implement/SKILL.md` Step 18b (and `skills/shared/final-summary-emit.md` implement bindings), add precedence: when composite/finalize stdout has valid markers and `EMIT_BODY=true`, terminal emit must use that post-step18b body even if a Step 17 cache exists; emit the Step 17 cache only when `EMIT_BODY=false`. Optionally narrow `should_emit_updated_body` or document that orchestrator precedence is authoritative.
  - From Cursor-Pragmatic: Add a branch: when a Step 17 body is cached and finalize stdout has `EMIT_BODY=true` with valid markers, terminal emit must use the Step 18 marker body from captured stdout, not the Step 17 cache. Use the Step 17 cache only when `EMIT_BODY=false`.
  - From Cursor-Requirements: On finalize-done, if composite stdout has `EMIT_BODY=true` with a valid marker body, terminal chat emit must use that refreshed Step 18 body; emit the cached Step 17 body only when Step 18 markers are suppressed (`EMIT_BODY=false`).
  - From Codex-Requirements: Add a firm skills/implement/SKILL.md plan bullet to rewrite that anti-halt terminal boundary so Step 16-17 only captures a pending body, Step 18 runs cleanup/teardown/tail relay, and the cached body is emitted last with no following tool call; pin removal of the old emit-then-continue wording in scripts/test-implement-structure.sh.


