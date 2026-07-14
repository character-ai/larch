## Goal
Implement issue #7198: [IMPLEMENTING] [FEATURE] Conflict-fix resolution via the ci-fixer subagent.

## Implementation Plan
#### Summary

Rebase-conflict resolution runs in the main agent today per `skills/implement/references/conflict-resolution.md`: conflicted hunks and resolution reasoning enter the main context. Route the resolution phases to the `larch:ci-fixer` subagent from #7192 in a conflict mode. Caller routing, the rebase-abort bail invariant, operator escalation, and ship relaunch stay with the main agent.

#### Current state (verified 2026-07-12; re-verify during /design)

- Consumers: the Rebase Checkpoint Macro early checkpoints (Steps 1.r, 4.r, 7.r, 7a.r; `caller_kind=early_rebase`; entry when `python3 python/cli.py push rebase --no-push --skip-if-pushed --keep-on-conflict` exits 1 with a rebase in progress) and the ship driver `run_rebase_rebump` (`caller_kind=ship_pr_pre_push`; `NEXT_ACTION=conflict-fix` with `RESUME_PHASE=ship-pr-rrr-phase14` and `CONFLICT_FILES` in `.ship-route-exit-handoff.env` and `ship-pr-state.sh`), emitted from the conflict branches in `python/larch/implement/dispatch_ship.py`.
- Procedure: Phase 1 per-file classification and resolution from `CONFLICT_FILES` (fallback `git diff --name-only --diff-filter=U`); sides are labeled "upstream (main)" and "feature branch", never "ours"/"theirs"; Phase 3 is main-agent self-review for non-trivial `ship_pr_pre_push` resolutions (the trivial-all gate skips it; no external panel); Phase 4 is a local-only `--continue --no-push --keep-on-conflict` loop with per-hop `CONFLICT_FILES` re-capture; Phase 4 exit 0 relaunches `step-8-ship.sh` through the Step 8 bgjob pair (`ship_pr_pre_push`) or returns to the macro (`early_rebase`); every bail runs `python3 python/cli.py git rebase-abort` first because the rebase stays in progress.
- The procedure may escalate to the operator for irreconcilable conflicts.

#### Proposed design

1. Conflict mode for `larch:ci-fixer` (same agent definition as #7192; a different prompt template). Inputs, paths and tokens only: caller kind, `CONFLICT_FILES`, repo root, the phase rules (label rule, trivial classification, self-review requirement for non-trivial `ship_pr_pre_push` resolutions, per-hop re-capture, no push), and the bail invariant.
2. The subagent performs Phases 1-3 and the Phase 4 local `--continue` loop via the documented `push rebase` commands, re-capturing `CONFLICT_FILES` per hop. Final message: `FIXER_RESULT=resolved|bail`, `FIXER_SUMMARY=<one line>`, plus a per-file resolution table for the run log. Bail reasons include `needs-operator` for irreconcilable conflicts.
3. The main agent parses the result only. `resolved` routes exactly as today's Phase 4 exit 0 (relaunch the Step 8 bgjob pair, or return to the macro). `bail` or an unparseable message: verify the rebase was aborted (run `git rebase-abort` idempotently), then route today's bail path. `needs-operator`: the main agent runs the existing escalation prompt and, on operator guidance, continues the same subagent via `SendMessage` (fresh-spawn fallback per the #7192 gating pattern).
4. Salvage: a dead subagent with a rebase still in progress is handled by `git rebase-abort` plus today's bail routing. The #7192 dirty-tree salvage-commit rule does NOT apply mid-rebase; abort is the deterministic safe action and matches the existing bail invariant.
5. Attribution: `MODE=subagent`, `TIER=subagent`.

#### Keep unchanged

- Both caller families' routing, gates, and `RESUME_PHASE=ship-pr-rrr-phase14` resume semantics.
- The no-push Phase 4 rule, the never-ours/theirs label rule (moves into the subagent prompt verbatim), and the rebase-abort bail invariant.
- Rebase mechanics in `python/larch/git/rebase.py`.

#### Acceptance criteria

1. Forced-conflict end-to-end runs for both caller kinds resolve via the subagent and relaunch or return correctly; the transcript shows no main-agent Read of conflicted hunks.
2. Dead-subagent salvage aborts the rebase and routes the existing bail path.
3. The operator-escalation round-trip is covered.
4. `skills/implement/references/conflict-resolution.md` is rewritten as the subagent contract; fence and structure tests pass; `make py-lint` and `make py-test` green for changed files.

#### Non-goals

- CI fixing and checks fixing (#7192 and the sibling checks-fallback issue).
- Ship routing and rebase mechanics.

#### Priority and dependencies

Blocked by #7193 (native edge). #7192 and #7193 are top priority and land first; this issue reuses #7192's agent definition, result conventions, and SendMessage gating.

## Test plan
(no test plan section in plan-file)
