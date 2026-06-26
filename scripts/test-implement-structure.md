# test-implement-structure.sh

High-level structural harness for the wrapperized `/implement` prompt. It verifies that heavy prose lives in references, SKILL.md calls Step wrapper scripts, wrapper siblings exist, and helper scripts document current Step 0, Step 5, Step 8, Step 18, telemetry, launcher, and Preflight responsibilities.

## Launcher invariants

- Four pre-bootstrap call sites retain the old plugin-root guard shape.
- The single Preflight helper call replaces the two direct `plan-block read` fences.
- The helper block may use Bash 3.2 argv construction.
- The helper block invokes the script through `bash`, so executable mode is not part of the runtime contract.
- The helper emits one `KEY=value` record per line on success.
- The helper emits `RESUME=true` or `RESUME=false`.
- The prompt-side parser consumes the helper envelope only after exit `0`.
- Post-Step-0 call sites use `bash "$IMPLEMENT_TMPDIR/larch-run.sh" <relative-script>`.
- Background wrapper assertions match the one-line launcher form for Step 5 review composites, Step 7a, and Step 8.
- Timeout assertions and `<task-notification>` assertions remain load-bearing.
- Step 8+ loads `ship-pr-exit-matrix.md` before the route-exit and pre-driver fences. Every-run branch semantics stay there, while the OOS checkpoint router and autonomous CI-fix bodies live in `ship-pr-oos-checkpoint-router.md` and `ship-pr-ci-fix.md`.
- Step 18 loads `step18-cleanup.md` before the gate fence. Four-layer stall tracking, Step 18a.5 skip predicates, and teardown prose stay there, while eligible-path escalation-success filing lives in `step18a5-filing.md`.
- Wrapper sibling and executable checks still pin every local `skills/implement/scripts/*.sh` helper used by the prompt.

## Caller

`make test-implement-structure` and the Makefile harness shard.
## Rebase checkpoint invariants

- `python/push.py` emits `CHECKPOINT_NEXT`.
- `python/larch/state/bootstrap.py` relays `CHECKPOINT_NEXT`.
- `skills/implement/SKILL.md` documents `CHECKPOINT_NEXT=continue|load-routing` and the Step 7a `CHECKPOINT_NEXT`-only skip predicate.
- `skills/implement/references/rebase-checkpoint-routing.md` owns `ROUTE=` and process-code detail after the macro chooses `load-routing`.

## Final-summary emit invariants

- `/implement` Step 17 and Step 18b point to `skills/shared/final-summary-emit.md` instead of restating the marker extraction algorithm.
- Step 17 binds captured foreground `python/cli.py implement step-16-17` wrapper stdout as its source.
- Step 18b binds captured foreground `step-18.sh --phase finalize` wrapper stdout as its source.
- Both `/implement` marker-first callsites forbid `<task-notification>` sources, Read fallback, and sidecar follow-on.
