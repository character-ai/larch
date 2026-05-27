## Decision 1: Manual takeover actor
- **Question**: Who/what does the work after a stall?
- **Resolution**: Main Claude finishes inline — the orchestrator session directly writes remaining code via Edit/Write tools, commits, and resumes the existing `/implement` state machine.
- **Source**: user

## Decision 2: Bug-issue filing — clone vs consumer repo
- **Question**: What does "file an issue" mean across larch-clone and non-larch-clone environments?
- **Resolution**: Conditional on environment. **In a larch clone**: file a GitHub issue in the larch repo automatically. **In a non-larch consumer repo**: print a chat message asking the user to manually file an issue in the larch repo, with a pre-formatted generic description that is concise and contains no IP-sensitive data from the consumer repo — just a generic description of the failure circumstances.
- **Source**: user

## Decision 3: Stall scope
- **Question**: Which stall categories trigger the takeover flow?
- **Resolution**: All stall paths uniformly — any `STALL_TRACKING=true` exit point triggers the takeover flow regardless of which step stalled (Step 0 bootstrap, Step 2 impl, Step 3/6 checks, Step 5 review, Step 8 bump, Step 9+ ship-pr).
- **Source**: user

## Decision 4: Takeover timing relative to `[STALLED]` rename
- **Question**: Does takeover fire before or after the existing Step 18 `[STALLED]` title-prefix rename?
- **Resolution**: **Before** `[STALLED]` rename. Takeover intercepts the bail path between stall detection and Step 18. If takeover succeeds, the run continues normally and the issue eventually transitions to `[DONE]` like any successful merge. Only if takeover also fails does the existing Step 18 `[STALLED]` rename + cleanup fire. Net effect: `[STALLED]` only appears on issues where recovery itself failed.
- **Source**: user

## Decision 5: Recovery scope across pipeline steps
- **Question**: How far through `/implement` should the takeover carry the work?
- **Resolution**: Resume the exact step that stalled and continue forward end-to-end. If Step 2 stalled, main Claude writes the impl and proceeds through Steps 3–17 normally. If Step 5 stalled, it picks up at review-and-fix. If `ship-pr.sh` stalled, it resumes the shipping phase. Goal: complete the same logical run to merge no matter where it broke.
- **Source**: user

## Decision 6: Retry / failure-class-dependent recovery cap
- **Question**: What if the takeover attempt itself fails?
- **Resolution**: Retry policy is **failure-class-dependent**, not a single attempt cap. The classifier must distinguish:
  - **Same-cause repeated failure**: try a different strategy (e.g., re-read `larch:plan` and start the stalled step from scratch instead of resuming partial state). One same-cause retry, then fall through to `[STALLED]`.
  - **Transient infrastructure (GitHub API unreachable, network errors, gh CLI hiccups)**: retry ~4 times with 5-second delays.
  - **Test failures**: many retries are acceptable (tests typically need iterative fixes; cap is per failure class, not per-recovery).
  - **Lint / relevant-checks failures**: similar to test failures — iterate until clean or hit per-class cap.
  - Sketch phase / implementation phase decides the exact classifier taxonomy and per-class caps.
- **Source**: user

## Decision 7: Bug-issue filing timing and update behavior
- **Question**: When and how often should the bug issue be filed?
- **Resolution**: **File on first detection AND update on terminal failure.** First detection: file a larch issue (or print message in consumer-repo case) with the initial root-cause analysis. Terminal failure (after retries exhausted): post a comment on that same issue with retry outcomes + final state. No issue filing on takeover-succeeded path (success doesn't need a bug issue, only the run log captures it).
- **Source**: user

## Decision 8: Tracking-issue title transition on successful takeover
- **Question**: What title prefix should the tracking issue end up at after a successful takeover?
- **Resolution**: Leave at `[IMPLEMENTING]` throughout the takeover; transition to `[DONE]` only when ship-pr completes (same as a normal successful merge). Do NOT introduce a `[STALLED]` intermediate state on the success path; do NOT introduce a new `[DONE-RECOVERED]` marker. The existing title-prefix lifecycle is unchanged for both success and terminal-failure paths.
- **Source**: user

## Decision 9: Larch-clone detection mechanism (codebase-derived)
- **Question**: How does the feature detect "running in a larch clone"?
- **Resolution**: Reuse the canonical detection in `scripts/check-stale-plugin.sh`: a working-tree root contains `skills/implement/SKILL.md` iff it is a larch dev clone. The new takeover code paths can call a shared helper (or inline the same check) to branch on clone vs consumer behavior for issue filing.
- **Source**: codebase
