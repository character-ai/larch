# Design Discussion — Round 1

Issue: #2837 — Summary of /implement still sometimes omits costs report
Tier: `--simple` (sketch_budget=2, review_budget=full)
User scope extension: "same is true for /design summary"

## Decision 1: What surface is omitting the costs report
- **Question**: Is the bug in the structured `render-run-summary.sh` block (`- **Cost**: 💰 …`), in the agent's free-form follow-up natural-language summary at end of turn, or both?
- **Resolution**: User believes the structured block is **often not shown** in chat at all; possibly shown without costs in other cases — they can't tell exactly. Treat this as: primary failure mode is "structured block not surfaced to chat reliably." Secondary failure mode is "agent writes free-form summary instead/in addition, which omits cost."
- **Source**: user

## Decision 2: Surface scope breadth
- **Question**: Does the fix cover only the chat-printed summary, or also the GitHub tracking-issue `larch:final-summary` comment and the committed `larch-logs/.../final-summary.md`?
- **Resolution**: **Chat-printed only.** The GitHub comment and the committed `larch-logs/.../final-summary.md` already get their content from `render-run-summary.sh` and are not the reported failure mode. Do not touch them. (Note: the chat-print and the comment/file content all come from the same renderer, so improving the chat path should not regress the others.)
- **Source**: user

## Decision 3: Cost-line acceptance rule
- **Question**: Must the cost line always render (with explicit `N/A` when unavailable), or only when token data exists?
- **Resolution**: **Keep the current `render-run-summary.sh` rule** (always emit `- **Cost**:` with `N/A` fallback). The bug is not the rule; harden the callsites and the chat surface.
- **Source**: user

## Decision 4: Root-cause analysis vs hardening only
- **Question**: Should the design include root-cause analysis of WHY the structured block sometimes doesn't reach chat, or just enforce "make it appear"?
- **Resolution**: **RCA first, then targeted fix.** During plan research (Step 2b), investigate the actual mechanism — candidates: lib-quiet.sh FD-3 routing, conditional `--print-stdout` flags at callsites, missing invocations on certain bail/terminal paths, model halt-then-freeform-summary behavior. Propose a fix at the actual failure point. (Allow some hardening as belt-and-suspenders if the root cause is non-deterministic, but the fix must target the discovered cause.)
- **Source**: user

## Decision 5: Terminal-outcome coverage
- **Question**: Must the structured block print reliably on ALL terminal outcomes, or only happy paths?
- **Resolution**: **All terminal outcomes.** This includes `merged`, `approved`, `bailed`, `bailed-needs-user-input`, `stalled`, `design-only`, `forked-dry-run`, `pr-created`, `pr-created-draft`, `force-merged-externally`, and all `/design` cancelled-* / approved-partition / failed-plan-write outcomes. Bail/stall is exactly when the user most wants the cost visible.
- **Source**: user

## Decision 6: Free-form summary rule
- **Question**: May the plan strengthen NEVER rules forbidding agent free-form follow-up summary, or is freeform acceptable when it includes cost?
- **Resolution**: **Strengthen NEVER rule** in both `/implement` and `/design` SKILL.md. The structured block must be the only summary; any agent free-form follow-up is forbidden. This makes the cost guarantee mechanical — if the structured block prints, costs are present; the freeform alternative is eliminated entirely.
- **Source**: user

## Decision 7: Test stability constraint
- **Question**: Must existing tests pass unchanged, or are modest test updates and new tests acceptable?
- **Resolution**: **Updates acceptable.** Existing test files may be updated where their assertions need adjustment; new tests may be added (e.g., a callsite test asserting Step 17 / Step 5c invocations pass `--print-stdout`, or a NEVER-rule lint asserting no freeform-summary instructions remain). Byte-aligned snapshots that are not directly affected must still pass.
- **Source**: user

## Summary of binding scope

- **In scope**: chat-printed summary surface for `/implement` (Step 17) and `/design` (Step 5c, including pre-publish and post-publish phases); SKILL.md prose (NEVER rules); test additions where needed.
- **Out of scope**: GitHub tracking-issue `larch:final-summary` comment and committed `larch-logs/.../final-summary.md` content (they already work via `render-run-summary.sh`). Other skills (`/review`, `/research`, `/report-tokens`, etc.) are out of scope.
- **Hard constraints**: `render-run-summary.sh` cost-line rule unchanged; existing tests pass except where assertions directly need updating.
- **Must-have**: Structured block reliably reaches chat on every terminal outcome (merged, bailed, stalled, design-only, forked-dry-run, approved, cancelled-*, etc.) in both `/implement` and `/design`. Free-form follow-up summary forbidden by NEVER rule.
