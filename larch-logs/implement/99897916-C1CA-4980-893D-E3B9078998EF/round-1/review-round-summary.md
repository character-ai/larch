# Review Round 1

- Mode: `diff`
- 4 accepted, 4 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Stale probe-clamp counters survive marker removal or Step 3 relaunch in same tmpdir
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Per-sentinel `bg-poll-guard-probe-denials.*.count` files persist when `.bg-wait-active` is removed without terminal-sentinel completion (dead PID, timeout, or background-task expiry), and are only cleared on sentinel presence or `marker_step_completed`. Step 3 wrapper launch removes terminal sentinels but not probe counters. A prior wait can trip the clamp without writing `step-3-terminal`; after the wait ends or Step 3 relaunches in the same `DESIGN_TMPDIR`, the first sanctioned foreground probe can read a stale counter and be denied immediately, blocking recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Clear per-sentinel probe counter files when removing a live marker for dead PID/timeout and/or when writing a fresh marker; add harness coverage for clamp → marker removal → new marker → first probe allowed.
  - From cursor-specialist-edge-cases-output.txt: Clear `bg-poll-guard-probe-denials.*.count` alongside the existing sentinel `rm` at wrapper launch, or reset when writing a new `bg-wait` marker (mirror for step5c/final-summary).


### FINDING_2: Probe-clamp counters leak across parallel live tmpdirs
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, dyn-dyn-probe-clamp-output.txt
- **Severity**: important
- **Concern**: `terminal_sentinel_probe_clamp` iterates every live tmpdir and bumps/resets per-sentinel counters for each dir where the sentinel is absent, while `bash_is_terminal_sentinel_foreground_probe` already binds a probe to one specific tmpdir via `DESIGN_TMPDIR=<abs>;` (or the sole live dir). Probes aimed at tmpdir A can increment tmpdir B's counter while B is idle; parallel `/design` waits in the same `CLAUDE_PID` contaminate each other's probe budgets, so a later legitimate probe in B can be denied on first retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Limit counter bumps and resets to the matching live dir only.
  - From codex-specialist-edge-cases-output.txt: Scope the clamp to the matched live dir and decide on that dir only.
  - From dyn-dyn-probe-clamp-output.txt: Resolve the probe's target tmpdir with the same rules as `bash_is_terminal_sentinel_foreground_probe` (explicit `DESIGN_TMPDIR` match, else the sole live dir) and only bump, reset, and threshold-check the counter for that target dir; keep `any_present` scoped to the target dir as well.


### FINDING_7: Missing `--issue-verified` guard only fires when parsed counts are nonzero
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The missing `--issue-verified` check is gated on nonzero created/deduped counts. Non-empty `/issue` stdout with only zero-count keys, failures, or diagnostics can return success and leave `UNMAPPED_CONFIRMED` false, violating the documented contract and masking an unmapped confirmation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Trigger the guard from non-empty stdout directly, not from created/deduped counts.
  - From codex-specialist-testing-output.txt: Treat any non-empty `issue_output` with missing `issue_verified` as unmapped and non-zero, and add a regression test for a zero-count non-empty issue stdout.


### FINDING_8: Missing ingest status is ledgered as non-retryable dismissal
- **Reviewer(s)**: codex-generalist-output.txt
- **Severity**: important
- **Concern**: Missing ingest status is counted as a launch failure but also ledgered as `dismissed:verification-failed`. If a verifier launch is skipped, interrupted, or its `ingest-verdict` call is lost, then `finalize` and `record` run, the unverified candidate hash is committed to `larch-logs/rejected-analysis-ledger.tsv`, and future runs skip it as a ledger duplicate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generalist-output.txt: Treat `status is None` like `launch-failed`: increment `launch_failures`, do not append a ledger dismissal, and let `record` return non-zero without making the candidate non-retryable.


