## Decision 1: forked_target / UPSTREAM_REPO input mechanism
- **Question**: How should `phase_tracking` learn `forked_target` and `UPSTREAM_REPO`?
- **Resolution**: Add new CLI flags `--forked-target true|false` and `--upstream-repo OWNER/REPO` to `scripts/implement-bootstrap.sh`. SKILL.md call site forwards them. `phase_infra` and `write-session-env.sh` remain unchanged.
- **Source**: user

## Decision 2: Branch-2 fresh-adopt happy-path harness case
- **Question**: Should the harness add an explicit Branch-2 fresh-adopt happy-path case in addition to the body-enumerated GP2/GP3/B1/B2/B3/B5?
- **Resolution**: Yes — add a `GP-adopt` (or similarly named) case exercising the full Branch-2 chain: `get-issue-state` (OPEN) → `larch-log.sh init` → `post-tracking-issue.sh` → `tracking-issue-write rename` → sentinel write.
- **Source**: user

## Decision 3: BRANCH_SELECTED enum values
- **Question**: What KV value should `BRANCH_SELECTED` take for each adoption path?
- **Resolution**: Four explicit dash-separated tokens: `branch-1-resume`, `branch-2-adopt`, `forked-target-skip`, `repo-unavailable-skip`. Empty string when `--up-to-phase` did not reach `tracking`.
- **Source**: user

## Decision 4: SKILL.md prose collapse scope (Phase 2)
- **Question**: How aggressively should `skills/implement/SKILL.md` Step 0 prose between L526-650 be collapsed by Phase 2?
- **Resolution**: Moderate collapse — replace the four fenced bash blocks (calls #6, #7, #8a/#8b, #9) and surrounding Branch 1 / Branch 2 / carve-out subsections with a single fenced `implement-bootstrap.sh --up-to-phase tracking` invocation block, a brief KV-output table, and a bail-routing table. Approximates the Phase 4 end-state ergonomics inside the Phase 2 scope.
- **Source**: user

## Decision 5: Default behavior when --forked-target / --upstream-repo are absent
- **Question**: How should `phase_tracking` handle invocations missing the new fork flags (legacy callers, harness invocations)?
- **Resolution**: Default `forked_target=false`, proceed normally (treat absent flags as the non-fork path). No `die_usage` failure. Keeps Phase 1 backward compatibility and avoids forcing every harness fixture to thread the flag.
- **Source**: user

## Decision 6: Hard constraints (NEVER list) carried into Phase 2
- **Question**: Which NEVER rules apply to `phase_tracking`?
- **Resolution**: NEVER #14 (no prompt-side `session-env.sh` writes — sanctioned writers only), NEVER #9 (no `ScheduleWakeup`), NEVER #16 (foreground only), Bash 3.2 portability (BASH_AUTHORING.md §3), `script-md-siblings` rule (sibling `.md` required and updated in same commit), `lib-quiet.sh` contract (use `emit` / `emit_kv` / `emit_breadcrumb`, `larch_err` for diagnostics).
- **Source**: umbrella issue #2732 body + AGENTS.md / CLAUDE.md

## Decision 7: Out-of-scope items (Phase 2 must NOT touch)
- **Question**: What is explicitly out of scope for Phase 2?
- **Resolution**: Phase 3 (`phase_plan_materialize`), Phase 4 (`phase_coder_select` waterfall), Rebase Checkpoint Macro (#1.r / #4.r / #7.r / #7a.r), Step 0 inline composite #10 (gh issue view + feature-description), Step 0 inline #13 (slug derivation), `persist-implement-run-flags.sh` call #11, `check-mid-run-dirty-tree.sh` call #12, `run-step1-plan-log.sh` call #15, `tracking-issue-summary.sh upsert-summary larch:plan` call #16. Those are deferred to Phase 3+.
- **Source**: umbrella issue #2732 body (Scope section)
