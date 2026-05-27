## Decision 1: Breadcrumb-monitor early-exit cascade scope
- **Question**: Should the orchestrator-level breadcrumb-monitor early-exit be fixed in this PR, or deferred?
- **Resolution**: Defer to a follow-up issue. Step 5b OOS captures "broaden monitor early-exit investigation / defensive timeout" as a Description. The voter-side fixes are sufficient to address the cascade per user observation ("Voter A-B fix would reduce the gap, addressing this cascade too").
- **Source**: user

## Decision 2: Codex stdin-close fix approach
- **Question**: Stdin redirection vs setsid vs let sketches decide?
- **Resolution**: Let sketches decide. The 4-agent sketch phase (Architecture/Edge/Innovation/Pragmatic) will propose alternatives; synthesis + dialectic picks the winner.
- **Source**: user

## Decision 3: Codex stdin-close fix surface area
- **Question**: Apply only to voters, or to all background-Codex launches?
- **Resolution**: Apply to all background-Codex launches (lib-codex-launcher-common.sh / launch-review.sh / equivalent shared layer). The stdin-close issue is a general background-Codex limitation per #2962 closing notes; fixing it in one place benefits voters, reviewers, implementer, research.
- **Source**: user

## Decision 4: Voter race fix structural approach
- **Question**: Inline wait, reuse wait-for-reviewers.sh, or extract new shared helper?
- **Resolution**: Reuse wait-for-reviewers.sh (or a minimal generalized sibling). wait-for-reviewers.sh is already a general-purpose `.done` sentinel waiter — verified via `wc -l` (176 lines) and source inspection: it accepts arbitrary `.done` paths as positional args with no reviewer-specific logic.
- **Source**: user

## Decision 5: Cursor sidecar empty fix scope
- **Question**: Fix sidecar population, treat as benign, or warn-only?
- **Resolution**: Include the sidecar population fix in the same PR. Investigate why Cursor's `.sidecar` initializes at 0 bytes and never populates; fix the underlying launcher behavior. (Note: `tally-code-votes.sh` does NOT read sidecars — verified via grep — so this is a cleanup item, not a tally blocker.)
- **Source**: user

## Decision 6: Verification bar
- **Question**: Offline tests only, offline + live re-run, or live re-run as bar?
- **Resolution**: Offline regression tests only. Add bash test harness coverage that simulates each failure mode (Codex stdin closed, voter `.tmp` not yet renamed, Cursor empty sidecar) and asserts the fix prevents the failure. No live /implement re-run gating required.
- **Source**: user

## Decision 7: Where tally reads voter results (background fact)
- **Question**: Does `tally-code-votes.sh` read voter `.sidecar` files? If yes, sidecar fix becomes a tally-correctness fix; if no, sidecar fix is cosmetic.
- **Resolution**: NO. `tally-code-votes.sh` only reads voter `.txt` outputs via `parse-judge-vote-and-rating.sh`. Sidecar files are not consumed by tally — verified by `grep -n 'sidecar' skills/review/scripts/tally-code-votes.sh scripts/parse-judge-vote-and-rating.sh` returning empty.
- **Source**: codebase

## Decision 8: Cross-skill voter dispatch reuse
- **Question**: Is `dispatch-code-voters.sh` used by both `/implement` Step 5 and standalone `/review`?
- **Resolution**: YES. The fix must preserve compatibility with both call paths. The script is invoked via `review-core.sh` line 621 (`"$DISPATCH_VOTERS_SH" "${voter_args[@]}"`), which is itself invoked by both `/implement` Step 5 (via `review-and-fix.sh`) and `/review` standalone.
- **Source**: codebase

## Decision 9: Launcher synchrony invariant
- **Question**: Is `launch-claude-review.sh` (voter-1 launch) synchronous? Is `dispatch-with-waterfall.sh` (voter-2/3 launch) synchronous?
- **Resolution**: BOTH are synchronous by design. `launch-claude-review.sh` calls `launch-claude-subprocess.sh` in foreground and writes `.done` after rc capture; `dispatch-with-waterfall.sh` uses `wait $pid` to block until completion. The observed race comes from the cascade (orchestrator-side breadcrumb-monitor early-exit causing concurrent orphaned process reads), but the user-prescribed fix (wait for `.done` before tally) is a robust defense-in-depth regardless of which path triggers the read.
- **Source**: codebase

## Decision 10: Hard constraint — backward compatibility
- **Question**: What must NOT break?
- **Resolution**:
  - Existing reviewer path (collect-agent-results.sh → wait-for-reviewers.sh) must remain unchanged in behavior.
  - dispatch-with-waterfall.sh public KV output grammar (ALL_OUTPUT_FILES, ALL_OUTPUT_TOOLS, DISPATCH_OK) must remain stable.
  - dispatch-code-voters.sh public KV output (VOTER_*_PATH, VOTER_*_TOOL, VOTER_*_STATUS, VOTER_*_PARSE_RATE_STATUS) must remain stable.
  - launcher argv validation harnesses (test-launch-review.sh, test-dispatch-code-voters.sh) must be updated in the same PR (per `.claude/rules/launcher-argv-test-coverage.md`).
- **Source**: codebase

## Decision 11: Non-goal — pipeline refactor
- **Question**: Should the design refactor the review-and-fix pipeline?
- **Resolution**: NO. Focused fix only. Touch only what's needed to address the three voter failure modes and the Codex stdin limitation (cross-caller). Sub-step boundaries: voter sentinel waiting, Codex stdin guard, Cursor sidecar population.
- **Source**: codebase
