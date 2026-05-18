### FINDING_1: **Important** `correctness` — `scripts/hook-anti-read-poll.sh:41-52`: The 30-second window never resets while the same path+offset continues, so the hook can permanently stop detecting that file after an early slow sequence. Concrete scenario: read `/tmp/a.md` at t=0 and t=1, then read it again at t=35, t=36, and t=37; the last three reads are consecutive within 2 seconds, but `first_ts` is still 0, `age=37`, and no reminder is emitted. Reset `count=1` and `first_ts=now` when the same path+offset is seen but `now - first_ts > WINDOW_SECS`, and add a harness case for the expired-window reset.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` — `scripts/hook-anti-read-poll.sh:41-52`: The 30-second window never resets while the same path+offset continues, so the hook can permanently stop detecting that file after an early slow sequence. Concrete scenario: read `/tmp/a.md` at t=0 and t=1, then read it again at t=35, t=36, and t=37; the last three reads are consecutive within 2 seconds, but `first_ts` is still 0, `age=37`, and no reminder is emitted. Reset `count=1` and `first_ts=now` when the same path+offset is seen but `now - first_ts > WINDOW_SECS`, and add a harness case for the expired-window reset.
- **Suggested revision**: Address the concern above.


### FINDING_11: code-quality: scripts/test-hook-anti-read-poll.sh:45-47
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Comment claims new cwd clears state; test uses same cwd and different offset Maintainers misread reset semantics Fix comment text
- **Suggested revision**: Address the concern above.


### FINDING_14: code-quality: skills/implement/scripts/write-rejected-findings.sh:62
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Quiet transcript still advertises details=rejected-findings.md after copying rejected-findings-full.md. Operators grep the wrong filename when reconciling count vs log body. Align the message with the actual source file or state both paths.
- **Suggested revision**: Address the concern above.


### FINDING_15: correctness: scripts/compose-review-findings.sh:127-139
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] code-review-rejected parser only recognizes ### [rejected] headers Re-composing from legacy rejected-findings-full.md using ### [Code Review] drops all rejected sections and under-reports FINDINGS_TOTAL Accept legacy header or document migration
- **Suggested revision**: Address the concern above.


### FINDING_19: correctness: skills/implement/scripts/write-rejected-findings.sh:41-46
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Empty check uses only rejected-findings.md -s before any full-file handling. If upstream ever leaves the bare file empty but full populated, the script exits empty and skips the durable log copy despite existing detail. Treat non-empty rejected-findings-full.md as sufficient to pass the empty gate when deciding to copy and emit.
- **Suggested revision**: Address the concern above.


### FINDING_27: risk-integration: scripts/test-hook-anti-read-poll.sh:1-67
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Harness omits time-window and repeat-fire assertions. 30s expiry and repeated PostToolUse emissions can regress without failing CI. Add controlled clock stubs or sleep-based cases for window boundary and fourth-read behavior.
- **Suggested revision**: Address the concern above.


### FINDING_28: risk-integration: scripts/test-hook-anti-read-poll.sh:1-67
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No test for WINDOW_SECS expiry or post-window streak 30s window semantics and post-expiry warning behavior are unverified; regressions would not be caught Add time override or state-file injection tests
- **Suggested revision**: Address the concern above.


### FINDING_31: risk-integration: skills/implement/scripts/write-rejected-findings.sh:52-59
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Verbatim copy of rejected-findings-full.md into run logs without redact-secrets / redact-tmpdir pipeline used in compose-review-findings.sh Rejected findings that quote secrets or PII from the codebase are persisted in full in larch-logs and may be committed or synced, increasing accidental leakage versus the old short ledger copy. Run the artifact through the same redaction helpers before writing the log copy, or document strict confidentiality handling for this file.
- **Suggested revision**: Address the concern above.


### FINDING_33: security: scripts/hook-anti-read-poll.sh:28-48
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Read-poll state file stores full file_path under world-readable /tmp-style TMPDIR by default On a multi-user host, another local user could read state-*.tsv and infer sensitive project paths the agent is polling. chmod 600 the state file after write and/or relocate state to a user-private cache directory.
- **Suggested revision**: Address the concern above.


### FINDING_9: code-quality: CHANGELOG.md:.agnix.toml:scripts/github-remote-repo.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Bundled agnix AS-014 disable, 29.3.11 changelog slice, and GitHub URL regex edits are outside the stated P+Q feature and the implementation plan’s file list. Reviewers must untangle unrelated policy/lint churn from run-log and hook behavior; bisecting a regression on hook or compose logic also blames unrelated commits. Split unrelated hygiene into its own PR or document an explicit dependency in the same issue if it cannot be decoupled.
- **Suggested revision**: Address the concern above.


