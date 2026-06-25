## Decision 1: Scope — both folds in one plan
- **Question**: Should this design cover both the route→init fold (ROUTE=proceed) and the 1d.5 entry/complete fold, or just one?
- **Resolution**: Both folds in one plan. They share one regression test (`make test-design-structure`) and the same SKILL.md / design-verb surface. Implementer may stage them as separate commits.
- **Source**: user

## Decision 2: Route fold fires ONLY on ROUTE=proceed
- **Question**: Which routes fold the init-runparams work into the route verb?
- **Resolution**: Only `ROUTE=proceed`. The `clarify`, `already-planned`, `resume@*`, and `cancel-*` branches must still return their `ROUTE` without folding init. `already-planned → replace-via-full-flow` keeps its separate `step0-init` fence because an `AskUserQuestion` operator gate sits between route and init.
- **Source**: codebase + issue

## Decision 3: Preserve the step0-init verb and 1d.5 --mode complete verb
- **Question**: Can the now-redundant `step0-init` fence and `step1d5 --mode complete` fence be removed outright?
- **Resolution**: No. `step0-init` must remain a launcher verb for the already-planned replace-via-full-flow path. `step1d5 --mode complete` must remain for the brainstorm path (runs after the brainstorm body). Only the dominant no-gate paths drop the second fence.
- **Source**: issue + codebase

## Decision 4: Hard constraints to preserve (no-break list)
- **Question**: What existing behavior must not break?
- **Resolution**: (a) batched `step-1c`/`step-1d` sentinel writes still occur before pause-check in the 1d.5 entry verb; (b) the two distinct 1d.5 skip breadcrumbs (plain skip vs. `.brainstorm-done` present) are preserved; (c) wrapper "pause-check before real work" ordering is preserved (enforced by `assert_wrapper_pause_before_work` in `scripts/test-design-structure.sh`); (d) feature-description.txt composition stays mechanical (`# {title}\n\n{body}` for issue paths, verbal prompt for verbal path), matching today's `step0_init_main`; (e) the route verb still emits its existing route KVs, now plus the init KVs, for the proceed path.
- **Source**: issue + codebase

## Decision 5: Verified — route plumbing is only partly present
- **Question**: Is the route→init plumbing already wired (issue flagged "design_lifecycle.py already references init-runparams")?
- **Resolution**: Partly. `step0_init_main` already writes `feature-description.txt` (`# {title}\n\n{body}`) and shells out to `init-runparams` (env-refresh + `[DESIGNING]` rename + run-params write + flag jq-merge). `route_main` / `step0_route_main` do NOT currently call init. So the fold reuses existing Python (extract the init body into a shared helper, call it from the route verb on proceed) rather than building new init logic.
- **Source**: codebase
