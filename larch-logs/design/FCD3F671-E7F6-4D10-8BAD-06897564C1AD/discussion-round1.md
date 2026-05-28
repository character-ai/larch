## Decision 1: Fix scope
- **Question**: Issue #3146 lists four fix directions (A=add --recount; B=strip prose preamble; C=add file-replacement fallback tier; D=hard-line-wrap). Which should this design cover?
- **Resolution**: A+B+C with a single new 4th tier that re-launches an external with PATCH_FORMAT=file-replacement after tiers 1–3 unified-diff exhaust. D is out of scope (plan format unchanged).
- **Source**: user

## Decision 2: Telemetry signal for fallback success
- **Question**: When the 4th tier (file-replacement) succeeds, how should /design distinguish that success from a primary unified-diff success?
- **Resolution**: Add a new status value `REVISE_STATUS=ok-fallback` (distinct from `ok`). Consumers in `plan-review-loop.sh` and `plan-review.md` must treat `ok-fallback` as success.
- **Source**: user

## Decision 3: Tier 4 degraded behavior
- **Question**: When the new 4th tier fires but Codex (the preferred external) is unavailable (`CODEX_PRESENT=false`), what should the 4th tier do?
- **Resolution**: Mini-waterfall Codex → Cursor → Claude within tier 4, mirroring the existing tier 1–3 waterfall pattern. Up to three internal launches inside tier 4 (only when tier 4 fires).
- **Source**: user

## Decision 4: Test coverage
- **Question**: Beyond the immediate fix, what scenarios must the regression harness (`scripts/test-revise-plan-with-waterfall.sh`) cover for this design?
- **Resolution**: Skip new test coverage entirely (operator directive). Do NOT add new fixtures or assertions. Existing harness assertions must continue to pass on the unified-diff happy path; adjust only if mandatory to keep them green.
- **Source**: user

## Decision 5: Backward compatibility for `REVISE_STATUS=ok-fallback` consumers
- **Question**: Which consumers of `REVISE_STATUS` must be updated so they treat `ok-fallback` as success and not as a revision failure?
- **Resolution**: Codebase audit identifies the consumer surface:
  1. `skills/design/scripts/plan-review-loop.sh` `_run_revise_with_status_parse` — change `[[ "$revise_status" == "ok" ]]` to accept both `ok` and `ok-fallback` as success.
  2. `skills/design/references/plan-review.md` — update the "Revision failures" prose to mention `ok-fallback` as a success status.
  3. `skills/design/scripts/revise-plan-with-waterfall.md` — extend the documented status enum.
  No other consumers of `REVISE_STATUS` matter for control flow; downstream round-summary.env writers re-emit whatever value `_run_revise_with_status_parse` collects.
- **Source**: codebase

## Decision 6: Bash 3.2 portability and pre-existing invariants
- **Question**: Are there any Bash 3.2 / repo-wide invariants that constrain the implementation shape?
- **Resolution**: Yes. (a) `BASH_AUTHORING.md` §3 — no Bash 4+ features (assoc arrays, namerefs, mapfile, `${var^^}`, `&>>`, coprocs). The existing script already uses positional case-based tier slots (`tier1_status`/`tier2_status`/`tier3_status`); extend to `tier4_status` the same way. (b) `restore_plan_or_die()` already restores the snapshot before any new tier runs, so tier 4 always sees the original `plan.txt`. (c) Adding `--recount` to `git apply` is portable; git has supported it since 2.0+.
- **Source**: codebase
