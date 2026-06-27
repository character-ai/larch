## Decision 1: In-scope changes (the four folds)
- **Question**: What is in-scope for this design?
- **Resolution**: Exactly four tightly-coupled folds in the /implement Step 2–4 region:
  (1) Fold Step 3 (checks) + Step 4 (implementation commit) + 4.r (rebase checkpoint) into ONE `implement checks-commit-route --checks-site step3 --commit-site step4 --rebase-checkpoint-4r` composite call, mirroring the already-shipped Step 6 triplet (SKILL.md line 680) and Step 5 reuse (line 572).
  (2) Fold the `step-2-entry.sh` token/timing entry-mark telemetry into the start of `implement run-dispatch`; delete the standalone pre-dispatch fence (SKILL.md 357–359).
  (3) Collapse the post-dispatch branch-compare (SKILL.md line 419): pass `--expected-branch "$BRANCH_NAME"` into `step-2-post-dispatch` and emit `POST_DISPATCH_NEXT=continue|bail` (+ `BAIL_REASON`).
  (4) Unify the two near-duplicate rebase-routing tables in `rebase-checkpoint-routing.md` (absorbed-1.r vs direct-probe) into one table + an input-source note.
- **Source**: issue (md-to-py-VII)

## Decision 2: Commit-leg semantics (the central risk)
- **Question**: What commit behavior must the composite preserve for `--commit-site step4`?
- **Resolution**: The composite must carry implementation-commit semantics BEYOND Step 6's `--stage-all`: the manifest-derived commit message plus specific-files/pathspec recovery on the claude-fallback path. On the external-implementer path the commit leg is a no-op (the dispatcher already committed). Checks-failure routing and rebase routing surface through the composite's existing `NEXT_ACTION=` / `CHECKPOINT_NEXT=` directives.
- **Source**: issue (md-to-py-VII); confirmed `checks_commit_route_main` exists in python/implement_dispatch.py

## Decision 3: Hard constraints — must not break
- **Question**: What existing behavior must be preserved?
- **Resolution**:
  - Keep orchestrator-side branch-assertion token validation (NEVER #9): even while following `POST_DISPATCH_NEXT`, the orchestrator still validates and still sets its in-memory bail vars (`FINAL_BAIL_REASON`, `IMPLEMENT_BAIL_REASON=main-branch-post-dispatch`, `STALL_STEP=2`, `PHASE=implementation`, `STALL_TRACKING=true`) before bailing to Step 12d.
  - Preserve the §2.1.5 dispatcher-envelope cross-check (#1058) — distinct from the post-dispatch branch assertion; KEEP unchanged.
  - Preserve `CHECKPOINT_NEXT=continue|load-routing` rebase-macro routing for 4.r and the harness-pinned `rebase-checkpoint-routing.md` literals.
  - Preserve the advisory `PHANTOM_*` token-scan and optional `COMMIT_SHA=` bind that currently precede the post-dispatch branch assertion.
- **Source**: issue (md-to-py-VII)

## Decision 4: Testing / verification gates
- **Question**: What must be updated and verified?
- **Resolution**: Update `EXPECTED_NEW` in `test-implement-fence-shape.sh`; run `make test-implement-fence-shape` and `make lint`. Keep the `("implement", "step-2-entry")` / `("implement", "step-2-post-dispatch")` registry-pinned tests in lockstep with any verb removal. Follow `docs/python-migration.md` "No shims" for retiring `step-2-entry.sh`.
- **Source**: issue (md-to-py-VII); confirmed registry pins in python test fixtures

## Decision 5: Non-goals
- **Question**: What is explicitly out of scope?
- **Resolution**: Do NOT touch the §2.1.5 dispatcher-envelope cross-check. Do NOT change the existing Step 5 / Step 6 `checks-commit-route` callers (new flags are additive). Do NOT broaden the sweep beyond the Step 2–4 region.
- **Source**: issue (md-to-py-VII)
