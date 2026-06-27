## Proposed Design Outline

### Goals
- Fold /implement Step 3 (checks) + Step 4 (commit) + 4.r (rebase checkpoint) into ONE `checks-commit-route` composite call, mirroring the already-shipped Step 6 triplet and Step 5 reuse.
- Fold the `step-2-entry.sh` token/timing telemetry into the start of `implement run-dispatch`; retire the standalone pre-dispatch fence.
- Collapse the post-dispatch branch-compare into a `POST_DISPATCH_NEXT` token and unify the two near-duplicate rebase-routing tables.

### Non-goals
- Do NOT touch the §2.1.5 dispatcher-envelope cross-check (#1058 — KEEP).
- Do NOT change the existing Step 5 / Step 6 `checks-commit-route` callers (new flags are additive).
- Do NOT broaden the sweep beyond the Step 2–4 region.

### Approach sketch
- Extend `checks_commit_route_main` (python/implement_dispatch.py) with `--commit-site step4` + `--rebase-checkpoint-4r`: commit leg no-ops on the external path, does specific-files/pathspec + manifest-message commit on claude-fallback; checks-failure + rebase routing reuse the composite's existing `NEXT_ACTION=` / `CHECKPOINT_NEXT=`.
- Move the conditional token/timing marks into the start of `run_dispatch`; delete `step-2-entry.sh` + verb + registry row + `.md` sibling per "No shims".
- Add `--expected-branch` to `step-2-post-dispatch`; emit `POST_DISPATCH_NEXT=continue|bail` (+ `BAIL_REASON`) as new wire tokens in config.py; orchestrator still validates and sets its in-memory bail vars (NEVER #9).
- Rewrite the SKILL.md Step 2–4 fences to the slimmer shape; unify `rebase-checkpoint-routing.md` to one table + an input-source note.

### Surfaces in scope
- `skills/implement/SKILL.md` (Step 2–4 region), `skills/implement/references/rebase-checkpoint-routing.md`
- `skills/implement/scripts/step-2-entry.{sh,md}`, `skills/implement/scripts/step-2-post-dispatch.{sh,md}`
- `python/implement_dispatch.py`, `python/cli.py` (verb registry), `python/config.py` (wire tokens)
- `skills/implement/scripts/test-implement-fence-shape.sh` (`EXPECTED_NEW`) and related fence-shape/structure harnesses

### Open questions
- None. The commit-leg external/fallback split, verb retirement, and table unification are all resolvable from the existing Step 6 composite precedent plus the "No shims" / G-CLI-1 convention.
