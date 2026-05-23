## Decision 1: Scope — fix /implement cost report AND add to /design
- **Question**: What is the actual gap? /implement already has a Cost bullet via render-run-summary.sh, but recent runs show "TOTAL N/A — Claude N/A, Codex N/A, Cursor N/A" because LARCH_*_RATE_PER_M env vars are unset.
- **Resolution**: Fix /implement's cost line by shipping sensible default rates so dollar amounts appear by default. Also add a single-line cost+tokens summary to /design Step 5 closeout (currently /design has NO summary at all). Out of scope: /research, the legacy nested-/design references in /implement (separate cleanup session is in flight — do NOT file OOS for nested references).
- **Source**: user

## Decision 2: /design summary format
- **Question**: What should the /design end-of-run summary look like?
- **Resolution**: Single compact line: `💰 Cost: TOTAL ~$X — Claude $A, Codex $B, Cursor $C  |  Tokens: <T>k`. Placed BEFORE the terminal machine footer `➡️ 5: cleanup — plan written to issue #<N>; NEXT REQUIRED: continue`.
- **Source**: user

## Decision 3: Default rates ship by default; env vars override
- **Question**: Should the repo ship default per-vendor rates so dollars appear without env var setup?
- **Resolution**: Yes — ship sensible defaults (per-vendor) in token-cost.sh. LARCH_CLAUDE_RATE_PER_M / LARCH_CODEX_RATE_PER_M / LARCH_CURSOR_RATE_PER_M / LARCH_TOKEN_RATE_PER_M continue to take precedence when explicitly set. Numeric default values must be exposed in docs/configuration-and-permissions.md and scripts/token-cost.md so users know what they're getting.
- **Source**: user

## Decision 4: Cost line on ALL exit paths
- **Question**: Should the cost+tokens summary be emitted on all /design exit paths (success, bail, cancel, error) or only the happy path?
- **Resolution**: ALL exits — happy path Step 5 cleanup, Gate A/B/C cancels, Step 0 cancel/clarify branch, and error paths. The summary line is printed before any terminal `**ℹ /design cancelled by operator.**` / `**⚠ ...**` final message.
- **Source**: user

## Decision 5: Nested /design is out of scope
- **Question**: How should the cost summary behave when /design runs nested under /implement (SESSION_ENV_PATH non-empty)?
- **Resolution**: Per user: "/design can NEVER be called from /implement. There is a separate design session in flight to clean up the remnants of that stuff in /implement -- do not file OOS for it." Plan and implementation will NOT touch SESSION_ENV_PATH branches and will NOT file OOS items pointing at nested-/design code paths.
- **Source**: user

## Decision 6: Hard constraints (backward compatibility)
- **Question**: What existing behavior MUST be preserved?
- **Resolution**: (1) /implement's existing run summary block schema (mode, path, duration, tokens, cost, issue, PR, plan review, code review, OOS filed, exec issues, warnings, run logs) and the `<!-- larch:run-summary v=1 -->` sentinel — no schema change. (2) render-run-summary.sh CLI flags. (3) token-cost.sh stdout `KEY=value` lines. (4) Env-var precedence: explicit LARCH_*_RATE_PER_M values MUST continue to override defaults. (5) /design terminal machine footer `➡️ 5: cleanup — plan written to issue #<N>; NEXT REQUIRED: continue` MUST remain the last output line on the happy path.
- **Source**: codebase

## Decision 7: Out-of-scope
- **Question**: What is explicitly NOT in scope?
- **Resolution**: (1) /research cost summary (only /implement fix + /design add). (2) Per-step cost breakdown (just per-vendor totals, matching existing render-run-summary format). (3) Input/output/cache split (no new pricing complexity). (4) Real-time cost streaming during the run (only end-of-run summary). (5) Changes to token-tally.sh's separate $ column behavior (it has its own LARCH_TOKEN_RATE_PER_M-only path and doesn't need touching).
- **Source**: user
