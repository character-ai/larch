## Goal
Implement issue #5021: [IMPLEMENTING] [BUG] Step 18a transient-infra reship incorrectly calls record-escalation with wrong trigger token.

## Implementation Plan
## Summary

During Step 18a stall recovery for a `transient-infra` / `step8-shippr` reship, the `/implement` orchestrator incorrectly called `python/cli.py stall-recovery record-escalation` — a call that should only happen when Main Claude is doing code-editing repair, not for a pure script reship. The call also used a wrong trigger token (`no-ci-checks-observed`, not in `_COMMON_TRIGGERS`), causing two `record-escalation` Tool Failure entries in the execution-issues log. The run itself succeeded (merged), but the spurious failures are noise and expose a documentation ambiguity that will re-trigger on any `no-ci-checks-observed` reship.

## Original report

During `/implement #4974` run `B5A346A6-0FA5-497D-976E-23DEF5317FE2`, the ship PR driver exited with code 4 (`outcome=STALLED`, `detail=no-ci-checks-observed`). Step 18a classified it as `FAILURE_CLASS=transient-infra`, `RESUME_HINT=step8-shippr`. The orchestrator then called `record-escalation --trigger no-ci-checks-observed` (wrong token), which failed token validation and logged two Tool Failure entries before the reship succeeded.

## Reproduction scenario

1. Run `/implement --merge <issue>` on a PR where GitHub CI takes longer than the initial poll window to register checks (triggers `no-ci-checks-observed` stall).
2. Python ship driver exits 4, `outcome=STALLED`, `detail=no-ci-checks-observed`.
3. Step 18a classify returns `FAILURE_CLASS=transient-infra`, `RESUME_HINT=step8-shippr`.
4. Orchestrator reads stall-recovery.md step 6: "Call `record-escalation` before inline `step8-shippr` repair when Step 18a itself owns the repair."
5. Orchestrator calls `record-escalation --site step8-shippr --trigger no-ci-checks-observed --step no-ci-checks-observed --phase ci-initial --dispatcher unknown`.
6. `_safe_token("trigger", "no-ci-checks-observed")` returns False — token not in `_COMMON_TRIGGERS`.
7. Two Tool Failure entries written; reship proceeds anyway; merge succeeds.

## Expected behavior

For `FAILURE_CLASS=transient-infra` with `RESUME_HINT=step8-shippr`: re-invoke `step-8-ship.sh` directly, with **no** call to `record-escalation`. The stall-recovery.md step 5 says "Record only branches that hand work to Main Claude. Do not record ordinary retries or reships." A pure `transient-infra` reship has no Main Claude code edits, so no escalation event exists to record.

Even if `record-escalation` were somehow appropriate on this path, the trigger token must come from `_COMMON_TRIGGERS` — the stall detail / classifier output (`no-ci-checks-observed`) is not a valid trigger. The stable owner token would be `step8-shippr`.

## Observed behavior

- Two `record-escalation` Tool Failure entries written to `execution-issues.ndjson` and committed to the run log.
- Error: `stall-recovery: record-escalation token validation failed` (exit code 1 twice).
- Run completed successfully (benign, but noisy).

## Root cause analysis

**Two distinct sub-bugs, one underlying ambiguity:**

**Sub-bug 1: Wrong call site.** stall-recovery.md step 6 and SKILL.md "Escalation recording owners" both say to call `record-escalation` "before inline `step8-shippr` repair when Step 18a itself owns the repair." Neither document clarifies that:
- "inline repair" and "Step 18a itself owns the repair" refer specifically to scenarios where Main Claude performs code edits (e.g., CI fix after Python emits `ledger_ready=true`).
- For `transient-infra` classification (pure reship, no code edits, no `ledger_ready=true` from Python JSON), `record-escalation` must NOT be called — this is an "ordinary reship" per step 5's explicit exclusion.

The `RESUME_HINT=step8-shippr` from `classify` output, combined with step 6's mention of "step8-shippr repair," created a false positive where the orchestrator interpreted any `step8-shippr` reship as requiring escalation recording.

**Sub-bug 2: Wrong trigger token.** Even if the call were appropriate, `no-ci-checks-observed` is not in `_COMMON_TRIGGERS` (`python/stall_recovery.py:70`). The only valid trigger for a Step 18a `step8-shippr` dispatch is `step8-shippr` itself (the stable owner token, which IS in `_COMMON_TRIGGERS`). The stall classifier output (the matched pattern or bail detail) must not be used as the trigger token — the trigger must be from the stable allowlist.

**Confidence: high.** Confirmed by code inspection: `_COMMON_TRIGGERS` does not contain `no-ci-checks-observed`; step 5 and SKILL.md line 103 ("Clean retries, reships, and health-only paths do not record escalation events") both exclude this case.

## Evidence

- `python/stall_recovery.py:70-76` — `_COMMON_TRIGGERS` frozenset. `no-ci-checks-observed` absent; `step8-shippr` present.
- `python/stall_recovery.py:907-909` — `_safe_token("trigger", trigger)` fails → `hard_fail("token-validation-failed")` → Tool Failure appended.
- `skills/implement/references/stall-recovery.md:45` — step 5: "Record only branches that hand work to Main Claude. Do not record ordinary retries or reships."
- `skills/implement/references/stall-recovery.md:46` — step 6: "before inline `step8-shippr` repair when Step 18a itself owns the repair" — ambiguous: omits the Main-Claude-edits precondition.
- `skills/implement/SKILL.md:882` — "Step 18a inline `step8-shippr` repairs" listed under escalation recording owners — also omits the Main-Claude-edits precondition.
- `skills/implement/references/ship-pr-exit-matrix.md:31-38` — escalation recording is tied to Python `ledger_ready=true` JSON signal for `first-fixer-non-health`, `local-unfixable`, etc. Exit-4 `transient-infra` never emits `ledger_ready=true`.
- `python/stall-recovery-report.md:103` — "Clean retries, reships, and health-only paths do not record escalation events."
- Run log: `larch-logs/implement/B5A346A6-0FA5-497D-976E-23DEF5317FE2/execution-issues.ndjson` — two `Tool Failure: record-escalation` entries with `reason: token-validation-failed`.

## Affected files

- `skills/implement/references/stall-recovery.md` — step 6 needs to explicitly exclude `transient-infra` / pure-reship paths from `record-escalation`. Should specify that the precondition is "Main Claude will perform code edits" not merely "RESUME_HINT=step8-shippr".
- `skills/implement/SKILL.md` — "Escalation recording owners" paragraph (line 882) lists "Step 18a inline `step8-shippr` repairs" without the Main-Claude-edits qualifier. Needs same clarification.
- Optionally: `python/stall_recovery.py` — `record-escalation` could emit a cleaner error when called with a non-trigger token like a stall-detail value, to make the bug surface faster in future runs.

## Suggested fix(es)

**Fix 1 (primary):** In stall-recovery.md step 6, add a qualifying sentence:

> "The `record-escalation` call applies only when Step 18a is performing actual code-editing work (e.g., Main Claude implementing inline after a `protected-path` bail or fixing CI after Python emitted `ledger_ready=true`). For `transient-infra` and any other `step8-shippr` reship that involves no Main Claude code edits, skip `record-escalation` entirely."

**Fix 2:** In SKILL.md "Escalation recording owners" paragraph, change "Step 18a inline `step8-shippr` repairs" to something like "Step 18a `step8-shippr` code-editing repairs (only when Python emitted `ledger_ready=true` or Main Claude is performing code edits)."

**Fix 3 (defense-in-depth):** Add an example to the record-escalation documentation or stall-recovery.md noting that the `--trigger` token must come from `_COMMON_TRIGGERS` — specifically that stall classifier output (like `no-ci-checks-observed`) is never a valid trigger.

## Open questions

- Should `record-escalation` validate against the stall-recovery classification to catch the case where neither `ledger_ready=true` was emitted nor code-editing recovery was performed? Or is prompt-level documentation the right fix surface?
- Are there other `RESUME_HINT=step8-shippr` stall classes (beyond `transient-infra`) where the same incorrect `record-escalation` call would be triggered?

## Test plan
(no test plan section in plan-file)
