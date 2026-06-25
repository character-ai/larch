### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:682-684
- **Concern**: Plan deletes the standalone `--ready-to-commit` resume fence but does not require relocating the structure-test-pinned resume envelope block (`STEP5_REVIEW_STATUS` gate, ordered lacks-envelope branches, NEVER #4 sentence; `test-implement-structure.sh` ~388-393).. Scenario: Implementer can remove ~682-684 while folding MAV/coder into `checks-step5-resume`, dropping prose `make lint` still requires and restoring short-circuit risk where `NEXT_ACTION=continue` from the inner commit phase is treated as Step 6 authorization without `STEP5_REVIEW_STATUS`.
- **Proposed resolution**: In `skills/implement/SKILL.md` under the `checks-step5-resume` composite blockquote, explicitly migrate the full ~682-684 contract (update the fence anchor to the composite) and list `test-implement-structure.sh` ~388-393 strings as must-remain.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:191-193
- **Concern**: Composite stdout is checks relay plus resume child output on one stream, but the plan tells the orchestrator to parse "relayed resume stdout only" without defining how to bound that slice.. Scenario: An implementer may strip or mis-scope parsing (e.g., drop the resume tail, or apply line-anchored `NEXT_ACTION` rules to the leading checks relay line), mis-routing lacks-envelope vs success paths on mixed composite stdout.
- **Proposed resolution**: Pin orchestrator parsing: apply resume lacks-envelope and `STEP5_REVIEW_STATUS` rules to the full composite capture; whitespace-scan the leading checks relay line only for checks keys; ignore checks-line tokens for resume `NEXT_ACTION` / review-loop authorization.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-structure.sh:387
- **Concern**: Structure harness still `require`s standalone `python/cli.py implement commit-route --site step7` while the plan removes the Step 7 commit-route fence in favor of `checks-commit-route`.. Scenario: `make lint` fails after correct SKILL edits, or the harness keeps forcing prose for a retired fence.
- **Proposed resolution**: Flip line 387 to `forbid` standalone Step 7 `commit-route` on the `FILES_CHANGED=true` path and `require` the `checks-commit-route --checks-site step6 --commit-site step7` launcher needle instead (also update the `for script in [` block ~108-115).



### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/implement_dispatch.py:93-94
- **Concern**: Per-leg commit timeout needs a killable child, but the plan only registers composite CLI verbs and vaguely mentions a `python -c` shim for `_commit_route_run(..., emit_next_action=False)`.. Scenario: No child-safe entrypoint is specified; implementers may call `_commit_route_run` in-process inside `checks_commit_route_main`, defeating per-leg timeouts (FINDING_1 regression) while still passing shallow unit mocks.
- **Proposed resolution**: Add a documented child argv (e.g., `implement commit-route-leg --site … --implement-tmpdir … --emit-next-action false` or equivalent `__main__` shim), register it in `python/cli.py`, and require `_run_commit_route_leg` to spawn only that CLI with `subprocess.run(..., timeout=…)`.



### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:24-29,93-113
- **Concern**: Timeouts only kill the wrapper process. Scenario: A timed-out commit or resume leg can leave the nested review-and-fix subprocess running, so the composite can emit checks-failed or stall while the child keeps mutating the tree after the timeout is supposed to have stopped it. That breaks the per-leg deadline contract.
- **Proposed resolution**: Run each leg in its own process group and terminate the whole group on timeout, or reuse a helper that already kills descendants before seeding stall or returning checks-failed.



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: architecture
- **Location**: python/implement_dispatch.py:93-94
- **Concern**: Commit-leg child subprocess lacks a pinned entrypoint and IPC contract for `CommitRouteOutcome`. Scenario: The Files section runs `_commit_route_run(..., emit_next_action=False)` inside a timeout child and types `_run_commit_route_leg` as returning `CommitRouteOutcome`, but only standalone `implement commit-route` is registered today and it always emits `NEXT_ACTION`. An implementer can spawn the public CLI (duplicate routing tokens / invalid-envelope) or call the refactored function in-process (no killable commit timeout).
- **Proposed resolution**: Register a child-only surface (for example `implement commit-route --emit-next-action false` or a thin internal verb) and pin child stdout grammar (`COMMIT_ROUTE_OUTCOME=continue|seeded-stall|seed-failed` plus relayed commit KVs, no `NEXT_ACTION`). Parent `_run_commit_route_leg` parses that envelope after `subprocess.run(..., timeout=...)`.



### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/implement_dispatch.py:235-243
- **Concern**: Timeout helper wiring contradicts `_run_cli_capture` today. Scenario: Approach introduces `_run_leg_with_timeout`, but Files pins `_run_cli_capture(..., timeout=deadline_ms/1000)` while `_run_cli_capture` has no `timeout` kwarg. Implementers may add timeout only at the Bash layer, reviving slow-leg budget bleed inside the composite.
- **Proposed resolution**: Add `_run_leg_with_timeout` (or extend `_run_cli_capture` with `timeout`) in `implement_dispatch.py` and require all three composite legs to call it; add a unit test that a hung child is killed and mapped to `checks-failed` / `seeded-stall` without starting the next leg.



### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-structure.sh:307-308,387-394
- **Concern**: Structure harness still hard-requires retired standalone fences. Scenario: The plan folds Step 6/7 into `checks-commit-route` and leaves one Step 3 `run-step-checks` fence, but the harness still requires four `timeout: 10800000` tiers and an unconditional `python/cli.py implement commit-route --site step7` needle. A correct SKILL edit can still fail `make lint`.
- **Proposed resolution**: Replace the `10800000` count check with exactly-one Step 3 expectation; retire `require(... commit-route --site step7)` and the foreach entries for folded standalone checks/commit/resume; add `forbid`/negate needles for those retired fences per plan line 234.



### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:169-170
- **Concern**: Checks Failure Entry Macro item 4 still jumps to site success path without folded composite re-capture. Scenario: The plan rewrites `checks-repair-loop.md` §4 for folded sites but does not update macro item 4 (`On NEXT_ACTION=continue, return to the call site's stated success path`). After repair-loop `continue` at Step 5/6 folded sites, an implementer can skip the full `checks-commit-route` / `checks-step5-resume` chain and advance on stale success-path prose (NEVER #4 / round-3 FINDING_8 class).
- **Proposed resolution**: Split macro item 4: Step 3 keeps today's success-path jump; folded sites must re-run the §2-pinned composite launcher with identical argv before any Step 6/7/self-review success routing.



### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/implement_dispatch.py:93-95
- **Concern**: Commit-leg timeout child lacks a pinned parent/child stdout contract for `CommitRouteOutcome`. Scenario: Approach mandates `_run_commit_route_leg` inside a killable subprocess, but the Files section types it as returning `tuple[CommitRouteOutcome, str]` in-process. Unlike `checks-step5-resume`, which can relay raw child stdout, the parent must learn `continue` vs `seeded-stall` vs `seed-failed` after `emit_next_action=False`. Without a machine row (for example `COMMIT_ROUTE_OUTCOME=...` plus relayed commit KVs), the composite cannot emit exactly one authoritative `NEXT_ACTION` and may mis-map `seed-failed` to `stall`.
- **Proposed resolution**: Pin child stdout grammar for the commit leg; parse it in the parent; add pytest coverage for each outcome and for `TimeoutExpired` where seeding runs in the parent.



### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/implement_dispatch.py:28-34
- **Concern**: Commit-leg subprocess entry is underspecified and risks calling public `commit-route`. Scenario: Approach allows a shim, but `cli.py` registers only the two composite verbs. An implementer can spawn `python/cli.py implement commit-route` in the child; that path always prints inner `NEXT_ACTION` and revives duplicate-token invalid-envelope routing at folded sites.
- **Proposed resolution**: Register one internal child entry (for example `implement commit-route-leg --site ... --emit-next-action false`) or pin an equivalent `-c` shim in the Files section and tests; forbid the public `commit-route` CLI inside composite children.



### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/implement/references/step5-review-branches.md:5,23,27
- **Concern**: `step5-review-branches.md` is not in Files and still routes to deleted SKILL fences. Scenario: MAV/coder bodies end with "return to SKILL.md for the shared captured relevant-checks fence and deferred timing/commit/reinvoke sequence." Contract line 5 still assigns those surfaces to SKILL. After the fold, that sends implementers back to removed `run-step-checks` / `commit-route` / `--ready-to-commit` prose instead of `checks-step5-resume`.
- **Proposed resolution**: Add `### UPDATED: skills/implement/references/step5-review-branches.md`; retarget MAV/coder endings to the composite launcher; update the contract header so SKILL owns only the composite fence plus retained `--record-only` stall path.



### FINDING_13:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:651-657
- **Concern**: MAV/coder status-table blockquotes still gate on `RELEVANT_CHECKS_OK` and defer to the removed record→commit→resume chain. Scenario: The plan replaces the downstream fences with `checks-step5-resume` but leaves `main-agent-vote-required` / `coder-main-agent-required` bullets parsing `RELEVANT_CHECKS_OK` and pointing at the deleted sequence. Orchestrator prose can run legacy checks-only routing or skip the composite entirely.
- **Proposed resolution**: Rewrite those bullets to: run MAV/coder branch body, then the single `checks-step5-resume` background fence; route only on composite `NEXT_ACTION=checks-failed` or relayed resume `STEP5_REVIEW_STATUS`; drop `RELEVANT_CHECKS_OK` blockquotes at folded sites.



### FINDING_14:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:593-611
- **Concern**: Self-review SKILL edit is partial: legacy steps 7-8 and repair-loop blockquote remain. Scenario: The plan adds `checks-commit-route` and deletes the conditional commit block, but steps 7-8 still mandate separate `run-step-checks.sh` and `commit-route` fences with `RELEVANT_CHECKS_OK` / line-anchored `NEXT_ACTION` parsing. An implementer can ship both old and new fences or follow stale routing.
- **Proposed resolution**: Replace steps 7-8 with one numbered step hosting only the composite fence and its `NEXT_ACTION` blockquote; delete lines 593-611 legacy prose; keep steps 9-11.



### FINDING_15:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-structure.sh:103-115,307-310,387
- **Concern**: Structure harness positive requires still pin retired standalone fences. Scenario: Plan says to negate standalone Step 7 `commit-route`, but the harness still requires `commit-route --site step7`, counts four `timeout: 10800000` tiers, requires the old `--ready-to-commit` regex, and lists standalone launcher needles in the foreach block. `make lint` can fail after correct SKILL edits, or pass while stale needles remain.
- **Proposed resolution**: Extend the `test-implement-structure.sh` edit: replace foreach needles with the three composite one-liners; change the 10800000 count to 1; drop the ready-to-commit regex; replace line 387 with `checks-commit-route --checks-site step6 --commit-site step7`.



### FINDING_16:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Focus area**: architecture
- **Location**: python/implement_dispatch.py:673-737
- **Concern**: The commit leg lacks a pinned killable subprocess entrypoint for `emit_next_action=False`.. Scenario: The plan folds commit into a timeout-bounded child, but only refactors `_commit_route_run` in-process. `cli.py` still exposes `implement commit-route` without a suppress-`NEXT_ACTION` flag. A child that calls the public verb reprints `NEXT_ACTION`, reviving round-3 duplicate-token invalid-envelope routing. In-process calls also cannot honor per-leg ceilings from round-4 FINDING_1.
- **Proposed resolution**: Add a child-safe surface: e.g. `implement commit-route --emit-next-action false` (default true for standalone), or a thin `implement commit-route-leg` shim. Pin `_run_commit_route_leg` to `_run_leg_with_timeout` argv using that surface. Assert in tests that composite stdout has exactly one line-anchored `NEXT_ACTION` and that the child never prints its own.



### FINDING_17:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/implement_dispatch.py:235-243
- **Concern**: `_run_cli_capture` has no `timeout` kwarg, but the Files section passes `timeout=deadline_ms/1000` on checks-leg capture.. Scenario: Implementers may add timeout only on checks while commit/resume stay blocking in-process, or pass an unsupported kwarg and fail at runtime. That breaks the stated per-leg budget preservation and weakens FINDING_1 mitigation.
- **Proposed resolution**: Extend `_run_cli_capture` (or route all legs through `_run_leg_with_timeout`) with an optional `timeout` forwarded to `subprocess.run(..., timeout=...)`. Use it for checks, commit, and resume children. Add a unit test that a hung leg is killed and mapped to `checks-failed` / `stall` without starting the next leg.



### FINDING_18:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-structure.sh:307-309,387-394
- **Concern**: `test-implement-structure.sh` migration is incomplete beyond the launcher foreach list.. Scenario: The plan updates composite needles and timeout tiers, but does not explicitly retire standalone `require()` checks that still mandate `commit-route --site step7`, `timeout: 10800000` count >= 4, and the `step-5-resume --ready-to-commit` + `21600000` regex. After SKILL edits, `make lint` can still fail even when runtime routing is correct (round-4 FINDING_4 follow-on).
- **Proposed resolution**: In the same harness edit, replace line 307 with exactly-one `10800000` (Step 3 only); swap line 309 for `checks-step5-resume` + `32400000`; replace/forbid line 387 `commit-route --site step7` with `checks-commit-route --checks-site step6 --commit-site step7`; drop `--ready-to-commit` from the foreach `require` list while keeping `--record-only`.



