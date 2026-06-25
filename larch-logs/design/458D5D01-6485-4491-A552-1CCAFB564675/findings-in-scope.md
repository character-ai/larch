### FINDING_1: Resume envelope contract not migrated to `checks-step5-resume` composite
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Concern**: Plan deletes the standalone `--ready-to-commit` resume fence but does not require relocating the structure-test-pinned resume envelope block (`STEP5_REVIEW_STATUS` gate, ordered lacks-envelope branches, NEVER #4 sentence; `test-implement-structure.sh` ~388-393). An implementer can remove ~682-684 while folding MAV/coder into `checks-step5-resume`, dropping prose `make lint` still requires and restoring short-circuit risk where `NEXT_ACTION=continue` from the inner commit phase is treated as Step 6 authorization without `STEP5_REVIEW_STATUS`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `skills/implement/SKILL.md` under the `checks-step5-resume` composite blockquote, explicitly migrate the full ~682-684 contract (update the fence anchor to the composite) and list `test-implement-structure.sh` ~388-393 strings as must-remain.

### FINDING_2: Composite stdout parsing slice is undefined
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Composite stdout is checks relay plus resume child output on one stream, but the plan tells the orchestrator to parse "relayed resume stdout only" without defining how to bound that slice. An implementer may strip or mis-scope parsing (e.g., drop the resume tail, or apply line-anchored `NEXT_ACTION` rules to the leading checks relay line), mis-routing lacks-envelope vs success paths on mixed composite stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin orchestrator parsing: apply resume lacks-envelope and `STEP5_REVIEW_STATUS` rules to the full composite capture; whitespace-scan the leading checks relay line only for checks keys; ignore checks-line tokens for resume `NEXT_ACTION` / review-loop authorization.

### FINDING_3: Structure harness still requires retired standalone fences
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: `test-implement-structure.sh` still positively requires standalone fences the plan retires (`commit-route --site step7`, four `timeout: 10800000` tiers, `--ready-to-commit` regex, foreach launcher needles for folded standalone checks/commit/resume). A correct SKILL edit can still fail `make lint`, or the harness can pass while stale needles remain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Flip line 387 to `forbid` standalone Step 7 `commit-route` on the `FILES_CHANGED=true` path and `require` the `checks-commit-route --checks-site step6 --commit-site step7` launcher needle instead (also update the `for script in [` block ~108-115).
  - From Cursor-Innovation: Replace the `10800000` count check with exactly-one Step 3 expectation; retire `require(... commit-route --site step7)` and the foreach entries for folded standalone checks/commit/resume; add `forbid`/negate needles for those retired fences per plan line 234.
  - From Cursor-Pragmatic: Extend the `test-implement-structure.sh` edit: replace foreach needles with the three composite one-liners; change the 10800000 count to 1; drop the ready-to-commit regex; replace line 387 with `checks-commit-route --checks-site step6 --commit-site step7`.
  - From Cursor-Requirements: In the same harness edit, replace line 307 with exactly-one `10800000` (Step 3 only); swap line 309 for `checks-step5-resume` + `32400000`; replace/forbid line 387 `commit-route --site step7` with `checks-commit-route --checks-site step6 --commit-site step7`; drop `--ready-to-commit` from the foreach `require` list while keeping `--record-only`.

### FINDING_4: Commit-leg lacks pinned killable child entrypoint and stdout contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: blocking
- **Concern**: Per-leg commit timeout needs a killable child, but the plan only registers composite CLI verbs and vaguely mentions a `python -c` shim for `_commit_route_run(..., emit_next_action=False)`. Only standalone `implement commit-route` exists today and it always emits `NEXT_ACTION`. Without a documented child argv and pinned parent/child stdout grammar (`COMMIT_ROUTE_OUTCOME=continue|seeded-stall|seed-failed` plus relayed commit KVs, no `NEXT_ACTION`), implementers may call `_commit_route_run` in-process (defeating per-leg timeouts), spawn the public CLI (duplicate routing tokens / invalid-envelope), or mis-map `seed-failed` to `stall` while the composite cannot emit exactly one authoritative `NEXT_ACTION`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a documented child argv (e.g., `implement commit-route-leg --site … --implement-tmpdir … --emit-next-action false` or equivalent `__main__` shim), register it in `python/cli.py`, and require `_run_commit_route_leg` to spawn only that CLI with `subprocess.run(..., timeout=…)`.
  - From Cursor-Innovation: Register a child-only surface (for example `implement commit-route --emit-next-action false` or a thin internal verb) and pin child stdout grammar (`COMMIT_ROUTE_OUTCOME=continue|seeded-stall|seed-failed` plus relayed commit KVs, no `NEXT_ACTION`). Parent `_run_commit_route_leg` parses that envelope after `subprocess.run(..., timeout=...)`.
  - From Cursor-Pragmatic: Pin child stdout grammar for the commit leg; parse it in the parent; add pytest coverage for each outcome and for `TimeoutExpired` where seeding runs in the parent.
  - From Cursor-Pragmatic: Register one internal child entry (for example `implement commit-route-leg --site ... --emit-next-action false`) or pin an equivalent `-c` shim in the Files section and tests; forbid the public `commit-route` CLI inside composite children.
  - From Cursor-Requirements: Add a child-safe surface: e.g. `implement commit-route --emit-next-action false` (default true for standalone), or a thin `implement commit-route-leg` shim. Pin `_run_commit_route_leg` to `_run_leg_with_timeout` argv using that surface. Assert in tests that composite stdout has exactly one line-anchored `NEXT_ACTION` and that the child never prints its own.

### FINDING_5: Leg timeout does not terminate nested descendant processes
- **Reviewer(s)**: Codex-Arch
- **Severity**: blocking
- **Concern**: Timeouts only kill the wrapper process. A timed-out commit or resume leg can leave the nested review-and-fix subprocess running, so the composite can emit checks-failed or stall while the child keeps mutating the tree after the timeout is supposed to have stopped it. That breaks the per-leg deadline contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Run each leg in its own process group and terminate the whole group on timeout, or reuse a helper that already kills descendants before seeding stall or returning checks-failed.

### FINDING_6: `_run_cli_capture` has no timeout kwarg for per-leg ceilings
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan pins `_run_cli_capture(..., timeout=deadline_ms/1000)` while `_run_cli_capture` has no `timeout` kwarg today. Implementers may add timeout only at the Bash layer, pass an unsupported kwarg and fail at runtime, or leave commit/resume blocking in-process. That breaks the stated per-leg budget preservation and weakens timeout mitigation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add `_run_leg_with_timeout` (or extend `_run_cli_capture` with `timeout`) in `implement_dispatch.py` and require all three composite legs to call it; add a unit test that a hung child is killed and mapped to `checks-failed` / `seeded-stall` without starting the next leg.
  - From Cursor-Requirements: Extend `_run_cli_capture` (or route all legs through `_run_leg_with_timeout`) with an optional `timeout` forwarded to `subprocess.run(..., timeout=...)`. Use it for checks, commit, and resume children. Add a unit test that a hung leg is killed and mapped to `checks-failed` / `stall` without starting the next leg.

### FINDING_7: Checks Failure Entry Macro item 4 not updated for folded sites
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Checks Failure Entry Macro item 4 still jumps to site success path without folded composite re-capture. The plan rewrites `checks-repair-loop.md` §4 for folded sites but does not update macro item 4 (`On NEXT_ACTION=continue, return to the call site's stated success path`). After repair-loop `continue` at Step 5/6 folded sites, an implementer can skip the full `checks-commit-route` / `checks-step5-resume` chain and advance on stale success-path prose (NEVER #4 / round-3 FINDING_8 class).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Split macro item 4: Step 3 keeps today's success-path jump; folded sites must re-run the §2-pinned composite launcher with identical argv before any Step 6/7/self-review success routing.

### FINDING_8: `step5-review-branches.md` still routes to deleted SKILL fences
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Concern**: `step5-review-branches.md` is not in Files and still routes to deleted SKILL fences. MAV/coder bodies end with "return to SKILL.md for the shared captured relevant-checks fence and deferred timing/commit/reinvoke sequence." Contract line 5 still assigns those surfaces to SKILL. After the fold, that sends implementers back to removed `run-step-checks` / `commit-route` / `--ready-to-commit` prose instead of `checks-step5-resume`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add `### UPDATED: skills/implement/references/step5-review-branches.md`; retarget MAV/coder endings to the composite launcher; update the contract header so SKILL owns only the composite fence plus retained `--record-only` stall path.

### FINDING_9: MAV/coder status-table bullets still use legacy `RELEVANT_CHECKS_OK` routing
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: MAV/coder status-table blockquotes still gate on `RELEVANT_CHECKS_OK` and defer to the removed record→commit→resume chain. The plan replaces downstream fences with `checks-step5-resume` but leaves `main-agent-vote-required` / `coder-main-agent-required` bullets parsing `RELEVANT_CHECKS_OK` and pointing at the deleted sequence. Orchestrator prose can run legacy checks-only routing or skip the composite entirely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Rewrite those bullets to: run MAV/coder branch body, then the single `checks-step5-resume` background fence; route only on composite `NEXT_ACTION=checks-failed` or relayed resume `STEP5_REVIEW_STATUS`; drop `RELEVANT_CHECKS_OK` blockquotes at folded sites.

### FINDING_10: Self-review SKILL still retains legacy steps 7-8 fences
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Self-review SKILL edit is partial: legacy steps 7-8 and repair-loop blockquote remain. The plan adds `checks-commit-route` and deletes the conditional commit block, but steps 7-8 still mandate separate `run-step-checks.sh` and `commit-route` fences with `RELEVANT_CHECKS_OK` / line-anchored `NEXT_ACTION` parsing. An implementer can ship both old and new fences or follow stale routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Replace steps 7-8 with one numbered step hosting only the composite fence and its `NEXT_ACTION` blockquote; delete lines 593-611 legacy prose; keep steps 9-11.
```

**Merge notes (brief):**
- **FINDING_4** subsumes input 4, 6, 10, 11, 16 (same commit-leg child/IPC gap; severity **blocking**).
- **FINDING_3** subsumes input 3, 8, 15, 18 (same harness retirement gap).
- **FINDING_6** subsumes input 7 and 17 (`_run_cli_capture` / `_run_leg_with_timeout` wiring).
- **FINDING_5** kept separate from **FINDING_4**/**FINDING_6**: descendant process-group kill is a distinct fix from child argv registration and capture-timeout plumbing.
- No `[OUT_OF_SCOPE]` tags in source input; none emitted.
