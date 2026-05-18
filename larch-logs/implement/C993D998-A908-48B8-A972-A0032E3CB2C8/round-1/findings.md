### FINDING_1: **Important** `correctness` — `scripts/hook-anti-read-poll.sh:41-52`: The 30-second window never resets while the same path+offset continues, so the hook can permanently stop detecting that file after an early slow sequence. Concrete scenario: read `/tmp/a.md` at t=0 and t=1, then read it again at t=35, t=36, and t=37; the last three reads are consecutive within 2 seconds, but `first_ts` is still 0, `age=37`, and no reminder is emitted. Reset `count=1` and `first_ts=now` when the same path+offset is seen but `now - first_ts > WINDOW_SECS`, and add a harness case for the expired-window reset.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` — `scripts/hook-anti-read-poll.sh:41-52`: The 30-second window never resets while the same path+offset continues, so the hook can permanently stop detecting that file after an early slow sequence. Concrete scenario: read `/tmp/a.md` at t=0 and t=1, then read it again at t=35, t=36, and t=37; the last three reads are consecutive within 2 seconds, but `first_ts` is still 0, `age=37`, and no reminder is emitted. Reset `count=1` and `first_ts=now` when the same path+offset is seen but `now - first_ts > WINDOW_SECS`, and add a harness case for the expired-window reset.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] **Latent** `correctness` — `skills/implement/scripts/write-rejected-findings.sh:41-50`: Pre-existing behavior treats a header-only compact `rejected-findings.md` as one rejected finding because `count=0` is forced to `1`. Concrete scenario: `emit-tally.sh` can create `# Rejected Findings` with no rejected entries; Step 16 then reports `STATUS=ok` / `REJECTED_COUNT=1` instead of empty. Fix separately by treating files with no actual rejected entry markers as empty before forcing the fallback count.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Latent** `correctness` — `skills/implement/scripts/write-rejected-findings.sh:41-50`: Pre-existing behavior treats a header-only compact `rejected-findings.md` as one rejected finding because `count=0` is forced to `1`. Concrete scenario: `emit-tally.sh` can create `# Rejected Findings` with no rejected entries; Step 16 then reports `STATUS=ok` / `REJECTED_COUNT=1` instead of empty. Fix separately by treating files with no actual rejected entry markers as empty before forcing the fallback count.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] architecture: git log merge-base..HEAD
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Version bump commit not in implementation plan items 1-10 Parallel housekeeping commit on branch; not a gap in P/Q file checklist None required for plan fidelity
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] architecture: implementation plan Q6 vs scripts/hook-anti-read-poll.sh:28-30
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] State file path differs from plan’s literal filename Equivalent isolation via cwd hash subdirectory layout Align plan text to shipped path or accept as doc-only delta
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] code-quality: skills/review/scripts/test-review-core.sh:161-162
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Stub rejected-findings-full still uses ### [Code Review] pattern Not introduced by this diff; possible future confusion if composed with new parser Update stub if ever wired to compose-review-findings
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] code-quality: skills/review/scripts/test-review-core.sh:161-162
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Fixture rejected-findings-full.md still uses ### [Code Review] while compose parser expects ### [rejected]. Only relevant if that fixture is later used as a compose contract; not introduced by this branch’s touched lines in that file. Align fixture with tally output when those tests are integrated.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] risk-integration: branch diff (larch-logs + agnix + changelog + bump)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Broad PR surface beyond P/Q Attribution noise if CI fails None (informational)
- **Suggested revision**: Address the concern above.

### FINDING_8: architecture: scripts/compose-review-findings.sh:127-144
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Generic ### flush still runs for headings inside a rejected block unless they match FINDING_|OOS_. Future tally markdown with other ### subheadings would fragment one rejected artifact into multiple composed records. Extend inner-heading handling or document and enforce a strict tally markdown subset.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: CHANGELOG.md:.agnix.toml:scripts/github-remote-repo.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Bundled agnix AS-014 disable, 29.3.11 changelog slice, and GitHub URL regex edits are outside the stated P+Q feature and the implementation plan’s file list. Reviewers must untangle unrelated policy/lint churn from run-log and hook behavior; bisecting a regression on hook or compose logic also blames unrelated commits. Split unrelated hygiene into its own PR or document an explicit dependency in the same issue if it cannot be decoupled.
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: scripts/hook-anti-read-poll.sh:13-23
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Four separate jq parses of the same JSON payload. Extra process overhead on every Read PostToolUse in large sessions. Combine into one jq program that emits all needed fields.
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: scripts/test-hook-anti-read-poll.sh:45-47
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Comment claims new cwd clears state; test uses same cwd and different offset Maintainers misread reset semantics Fix comment text
- **Suggested revision**: Address the concern above.

### FINDING_12: code-quality: scripts/test-hook-anti-read-poll.sh:45-47
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Comment says a new cwd wipes state but the test reuses /proj. Misleads maintainers into breaking the test when “fixing” cwd. Update the comment to describe offset-based reset.
- **Suggested revision**: Address the concern above.

### FINDING_13: code-quality: scripts/test-hook-anti-read-poll.sh:45-48
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Misleading test comment Readers may believe cwd is controlling isolation in the offset-reset case Reword comment to match behavior (offset change resets streak)
- **Suggested revision**: Address the concern above.

### FINDING_14: code-quality: skills/implement/scripts/write-rejected-findings.sh:62
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Quiet transcript still advertises details=rejected-findings.md after copying rejected-findings-full.md. Operators grep the wrong filename when reconciling count vs log body. Align the message with the actual source file or state both paths.
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: scripts/compose-review-findings.sh:127-139
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] code-review-rejected parser only recognizes ### [rejected] headers Re-composing from legacy rejected-findings-full.md using ### [Code Review] drops all rejected sections and under-reports FINDINGS_TOTAL Accept legacy header or document migration
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: scripts/hook-anti-read-poll.sh:35-48
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] State file is a one-line TSV storing raw file_path. Tab characters in file_path break read -r field splitting and corrupt count or path tracking. Reject or escape tab/newline in paths or use structured JSON state instead of TSV.
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: scripts/hook-anti-read-poll.sh:41-56
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Streak counts identical Read uses within 30s without requiring consecutive Read-only tool sequence Read then Bash then Read then Bash then Read on same path+offset still hits count=3 and emits though Reads are not back-to-back Align requirements/docs to actual behavior or add session-level consecutiveness if required
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: scripts/hook-anti-read-poll.sh:41-56
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Third and subsequent identical reads within 30s all emit warnings. Long polls could flood additionalContext with duplicate guidance. Consider firing once per streak or debouncing within the window.
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: skills/implement/scripts/write-rejected-findings.sh:41-46
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Empty check uses only rejected-findings.md -s before any full-file handling. If upstream ever leaves the bare file empty but full populated, the script exits empty and skips the durable log copy despite existing detail. Treat non-empty rejected-findings-full.md as sufficient to pass the empty gate when deciding to copy and emit.
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: skills/implement/scripts/write-rejected-findings.sh:41-59
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Early empty exit on bare rejected-findings.md skips copying non-empty rejected-findings-full.md Full detail file exists while bare file is empty; run log never gets full copy; STATUS=empty Consider full-file presence before STATUS=empty short-circuit
- **Suggested revision**: Address the concern above.

### FINDING_21: correctness: skills/implement/scripts/write-rejected-findings.sh:41-59
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Early exit on empty rejected-findings.md skips full-file preference If rejected-findings.md is empty while rejected-findings-full.md is non-empty the script exits STATUS=empty and never copies full detail to the run log and may emit REJECTED_COUNT=0 Gate empty/ok on full file too or document bare-only contract
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: skills/implement/scripts/write-rejected-findings.sh:49-56
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] REJECTED_COUNT comes only from rejected-findings.md while the log may mirror rejected-findings-full.md. Ledger and full artifact can disagree; UI totals may not match log sections. Document the contract or derive counts from the same artifact used for the log copy if parity is required.
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: .agnix.toml:21-26
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] AS-014 disabled globally for the repo Agnix no longer flags that pattern class; future real violations in the same shape could slip until caught elsewhere. Keep the disable narrowly scoped if agnix supports it, or schedule periodic manual review of the suppressed pattern class.
- **Suggested revision**: Address the concern above.

### FINDING_24: risk-integration: scripts/compose-review-findings.sh:127-145
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] code-review-rejected parser only matches ### [rejected] Legacy ### [Code Review] headers in sole rejected-findings.md are skipped by the generic ### handler so rejected bodies disappear and FINDINGS_TOTAL can be wrong for old artifacts Accept both header formats or add migration regression fixture
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: scripts/hook-anti-read-poll.sh:41-55
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Warning condition uses count>=3 for every subsequent read while age stays within the window. Fourth and later identical reads within 30s keep emitting additionalContext spam. Fire once per streak crossing (count==3) or add cooldown fields in persisted state.
- **Suggested revision**: Address the concern above.

### FINDING_26: risk-integration: scripts/hook-anti-read-poll.sh:50-56
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Warns on every Read once count>=3 within window Continued polling emits duplicate JSON reminders each Read Emit once per streak or throttle
- **Suggested revision**: Address the concern above.

### FINDING_27: risk-integration: scripts/test-hook-anti-read-poll.sh:1-67
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Harness omits time-window and repeat-fire assertions. 30s expiry and repeated PostToolUse emissions can regress without failing CI. Add controlled clock stubs or sleep-based cases for window boundary and fourth-read behavior.
- **Suggested revision**: Address the concern above.

### FINDING_28: risk-integration: scripts/test-hook-anti-read-poll.sh:1-67
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No test for WINDOW_SECS expiry or post-window streak 30s window semantics and post-expiry warning behavior are unverified; regressions would not be caught Add time override or state-file injection tests
- **Suggested revision**: Address the concern above.

### FINDING_29: risk-integration: scripts/test-hook-anti-read-poll.sh:50-62
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Path-reset coverage is shallow Interleaved A/B reads might still hide off-by-one streak bugs Add explicit interleave sequence assertions
- **Suggested revision**: Address the concern above.

### FINDING_30: risk-integration: skills/implement/scripts/write-rejected-findings.sh:41-63
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] REJECTED_COUNT and emit count come only from bare rejected-findings.md while the log may copy rejected-findings-full.md. Orchestrator or operator compares KV or banner count to the detailed log and draws the wrong conclusion when the bare ledger is stubby or pattern-mismatched. When selecting the full file for the log copy, derive count from that same file or explicitly document that telemetry is bare-only.
- **Suggested revision**: Address the concern above.

### FINDING_31: risk-integration: skills/implement/scripts/write-rejected-findings.sh:52-59
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Verbatim copy of rejected-findings-full.md into run logs without redact-secrets / redact-tmpdir pipeline used in compose-review-findings.sh Rejected findings that quote secrets or PII from the codebase are persisted in full in larch-logs and may be committed or synced, increasing accidental leakage versus the old short ledger copy. Run the artifact through the same redaction helpers before writing the log copy, or document strict confidentiality handling for this file.
- **Suggested revision**: Address the concern above.

### FINDING_32: risk-integration: skills/implement/scripts/write-rejected-findings.sh:62-63
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Emit line always says details=rejected-findings.md Operators may grep the wrong artifact name when full file was copied Clarify emit text when full file is used
- **Suggested revision**: Address the concern above.

### FINDING_33: security: scripts/hook-anti-read-poll.sh:28-48
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Read-poll state file stores full file_path under world-readable /tmp-style TMPDIR by default On a multi-user host, another local user could read state-*.tsv and infer sensitive project paths the agent is polling. chmod 600 the state file after write and/or relocate state to a user-private cache directory.
- **Suggested revision**: Address the concern above.

