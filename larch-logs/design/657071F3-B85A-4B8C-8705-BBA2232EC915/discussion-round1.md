## Decision 1: Gap 1 launcher scope
- **Question**: Which launcher lanes get the stderr-tail surfacing hook?
- **Resolution**: All 4 implement/CI launchers (`launch-codex-implement.sh`, `launch-cursor-implement.sh`, `launch-codex-ci.sh`, `launch-cursor-ci.sh`) PLUS the lint-fix-loop lane (`lint-fix-loop.sh`, `codex.wrapper.log` / `cursor.wrapper.log`).
- **Source**: user

## Decision 2: Gap 1 surfacing depth
- **Question**: How far should a failed agent's stderr tail travel?
- **Resolution**: End-to-end to chat. The lane must both produce the redacted tail and have its consumer surface it on failure, so the tail actually reaches `/implement` chat output. Not producer-only.
- **Source**: user

## Decision 3: Tier
- **Question**: SIMPLE or HARD given the broadened cross-lane scope?
- **Resolution**: SIMPLE (no sketches, no dialectic). Full plan-review panel + plan-command validator still run. #3202 already established the hook pattern to mirror.
- **Source**: user

## Decision 4: Reuse the #3202 tail library (hard constraint)
- **Question**: New tail rendering, or reuse existing?
- **Resolution**: Reuse `scripts/lib-failed-agent-stderr-tail.sh` (added by #3202) for redacted, byte-capped, line-bounded tails. Do not reinvent tail rendering or redaction.
- **Source**: codebase

## Decision 5: Preserve existing launcher contracts (hard constraint)
- **Question**: What must not break?
- **Resolution**: Surfacing is additive. Preserve each launcher's output file, `.meta`, `.done`/`.inner.done` sentinels, telemetry `.sidecar` / `.token-record`, dirty-tree sidecar, and existing `execution-issues.md` logging via `append-tool-failure.sh`. Do not regress the already-wired review/research/sketch lanes.
- **Source**: codebase

## Decision 6: All target launchers route through run-external-agent.sh (constraint reframes the fix)
- **Question**: Are these leaf launchers invoking codex/cursor directly, or wrapped?
- **Resolution**: All 4 implement/CI launchers and `lint-fix-loop.sh` invoke `run-external-agent.sh` (already #3202-wired). The remaining gap is that each lane redirects the wrapped stderr to its own `*.wrapper.log` and the consumer (`step2-implement.sh`, `ship-pr.sh`, `lint-fix-loop.sh`) does not surface the resulting stderr-tail sidecar to chat. The fix targets that choke point, not a new direct-CLI hook.
- **Source**: codebase

## Decision 7: Gap 2 test
- **Question**: What does Gap 2 add, and where?
- **Resolution**: Add a new behavioral case to `skills/design/scripts/test-plan-review-loop.sh` with failing panel stubs that assert collector stderr tails actually reach FD 2 when a panel reviewer fails (guarding the `plan-review-loop.sh:752-762` tee). If the test reveals the tee is broken, fix it minimally in the same change.
- **Source**: issue / codebase

## Decision 8: Redaction on the public surface (security constraint)
- **Question**: Must surfaced tails be redacted?
- **Resolution**: Yes. Any tail surfaced to chat must pass through the redaction path (`redact-secrets.sh` / the lib's sanitize step) before display. Chat output is a user-visible surface.
- **Source**: SECURITY.md / codebase
