### FINDING_1: panel [code-review/accepted]

## **Important** `correctness` — `scripts/hook-anti-read-poll.sh:41-52`: The 30-second window never resets while the same path+offset continues, so the hook can permanently stop detecting that file after an early slow sequence. Concrete scenario: read `/tmp/a.md` at t=0 and t=1, then read it again at t=35, t=36, and t=37; the last three reads are consecutive within 2 seconds, but `first_ts` is still 0, `age=37`, and no reminder is emitted. Reset `count=1` and `first_ts=now` when the same path+offset is seen but `now - first_ts &gt; WINDOW_SECS`, and add a harness case for the expired-window reset.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` — `scripts/hook-anti-read-poll.sh:41-52`: The 30-second window never resets while the same path+offset continues, so the hook can permanently stop detecting that file after an early slow sequence. Concrete scenario: read `/tmp/a.md` at t=0 and t=1, then read it again at t=35, t=36, and t=37; the last three reads are consecutive within 2 seconds, but `first_ts` is still 0, `age=37`, and no reminder is emitted. Reset `count=1` and `first_ts=now` when the same path+offset is seen but `now - first_ts &gt; WINDOW_SECS`, and add a harness case for the expired-window reset.
- **Suggested revision**: Address the concern above.

### FINDING_11: panel [code-review/accepted]

## code-quality: scripts/test-hook-anti-read-poll.sh:45-47

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Comment claims new cwd clears state; test uses same cwd and different offset Maintainers misread reset semantics Fix comment text
- **Suggested revision**: Address the concern above.

### FINDING_14: panel [code-review/accepted]

## code-quality: skills/implement/scripts/write-rejected-findings.sh:62

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Quiet transcript still advertises details=rejected-findings.md after copying rejected-findings-full.md. Operators grep the wrong filename when reconciling count vs log body. Align the message with the actual source file or state both paths.
- **Suggested revision**: Address the concern above.

### FINDING_15: panel [code-review/accepted]

## correctness: scripts/compose-review-findings.sh:127-139

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] code-review-rejected parser only recognizes ### [rejected] headers Re-composing from legacy rejected-findings-full.md using ### [Code Review] drops all rejected sections and under-reports FINDINGS_TOTAL Accept legacy header or document migration
- **Suggested revision**: Address the concern above.

### FINDING_19: panel [code-review/accepted]

## correctness: skills/implement/scripts/write-rejected-findings.sh:41-46

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Empty check uses only rejected-findings.md -s before any full-file handling. If upstream ever leaves the bare file empty but full populated, the script exits empty and skips the durable log copy despite existing detail. Treat non-empty rejected-findings-full.md as sufficient to pass the empty gate when deciding to copy and emit.
- **Suggested revision**: Address the concern above.

### FINDING_27: panel [code-review/accepted]

## risk-integration: scripts/test-hook-anti-read-poll.sh:1-67

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Harness omits time-window and repeat-fire assertions. 30s expiry and repeated PostToolUse emissions can regress without failing CI. Add controlled clock stubs or sleep-based cases for window boundary and fourth-read behavior.
- **Suggested revision**: Address the concern above.

### FINDING_28: panel [code-review/accepted]

## risk-integration: scripts/test-hook-anti-read-poll.sh:1-67

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No test for WINDOW_SECS expiry or post-window streak 30s window semantics and post-expiry warning behavior are unverified; regressions would not be caught Add time override or state-file injection tests
- **Suggested revision**: Address the concern above.

### FINDING_31: panel [code-review/accepted]

## risk-integration: skills/implement/scripts/write-rejected-findings.sh:52-59

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Verbatim copy of rejected-findings-full.md into run logs without redact-secrets / redact-tmpdir pipeline used in compose-review-findings.sh Rejected findings that quote secrets or PII from the codebase are persisted in full in larch-logs and may be committed or synced, increasing accidental leakage versus the old short ledger copy. Run the artifact through the same redaction helpers before writing the log copy, or document strict confidentiality handling for this file.
- **Suggested revision**: Address the concern above.

### FINDING_33: panel [code-review/accepted]

## security: scripts/hook-anti-read-poll.sh:28-48

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Read-poll state file stores full file_path under world-readable /tmp-style TMPDIR by default On a multi-user host, another local user could read state-*.tsv and infer sensitive project paths the agent is polling. chmod 600 the state file after write and/or relocate state to a user-private cache directory.
- **Suggested revision**: Address the concern above.

### FINDING_9: panel [code-review/accepted]

## code-quality: CHANGELOG.md:.agnix.toml:scripts/github-remote-repo.sh

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Bundled agnix AS-014 disable, 29.3.11 changelog slice, and GitHub URL regex edits are outside the stated P+Q feature and the implementation plan’s file list. Reviewers must untangle unrelated policy/lint churn from run-log and hook behavior; bisecting a regression on hook or compose logic also blames unrelated commits. Split unrelated hygiene into its own PR or document an explicit dependency in the same issue if it cannot be decoupled.
- **Suggested revision**: Address the concern above.

### FINDING_10: panel [code-review/accepted]

## code-quality: scripts/hook-anti-read-poll.sh:193-198

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Warning emits on every Read while count stays &gt;=3 within the window. Long identical read sequences flood additionalContext repeatedly until 30s window lapses. Fire only on first crossing of threshold or add cooldown between emissions.
- **Suggested revision**: Address the concern above.

### FINDING_11: panel [code-review/accepted]

## code-quality: scripts/test-hook-anti-read-poll.sh:32-38

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] First test block uses real time; window tests use injected now. Rare CI pause &gt;30s between hook runs could make call 3 not fire. Use HOOK_ANTI_READ_POLL_NOW for all streak assertions.
- **Suggested revision**: Address the concern above.

### FINDING_13: panel [code-review/accepted]

## correctness: scripts/compose-review-findings.sh:127-145

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Inner-heading guard only treats FINDING_/OOS_ ### lines as in-body; other ### subsections inside a rejected block hit the generic flush. rejected-findings-full.md containing e.g. ### Notes inside a block loses that heading and splits the record early. Broaden in-body ### handling while pending_id is set for code-review-rejected, or document supported subsection shapes only.
- **Suggested revision**: Address the concern above.

### FINDING_16: panel [code-review/accepted]

## correctness: scripts/test-hook-anti-read-poll.sh:31-63

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Wall-clock dependent assertions for the 3-hit warning without pinning HOOK_ANTI_READ_POLL_NOW. If CI pauses &gt;30s between the first and third simulated Read, hook resets the streak and the test fails intermittently. Use run_hook with synthetic timestamps (as in lines 79-93) or inject HOOK_ANTI_READ_POLL_NOW for all streak assertions.
- **Suggested revision**: Address the concern above.

### FINDING_17: panel [code-review/accepted]

## correctness: skills/implement/scripts/write-rejected-findings.sh:45-76

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] REJECTED_COUNT is derived from summary_file via a regex that does not match emit-tally compact grep lines; zero matches force count=1. Multi-reject rounds: log shows full detail for N rejections but quiet stream still reports count=1 (common when bare md is grep-n ledger). Count from detail_file markers (e.g. ### [rejected]) or from tally/review-summary counts aligned with emit-tally.
- **Suggested revision**: Address the concern above.

### FINDING_18: panel [code-review/accepted]

## correctness: skills/implement/scripts/write-rejected-findings.sh:65-71

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Redact pipeline for log copy discards stderr and uses || true on the whole write. Failed redaction or broken pipe can yield empty rejected-findings.md in the run log while STATUS=ok still reports success. Validate output size after write or use controlled error handling instead of silent || true; fall back to cp with visible failure.
- **Suggested revision**: Address the concern above.

### FINDING_19: panel [code-review/accepted]

## risk-integration: CHANGELOG.md:14-20 vs .claude-plugin/plugin.json

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] CHANGELOG section is [29.3.11] while plugin.json version is 29.3.12 and changelog never mentions 29.3.12. Operators and release notes readers cannot map the installed plugin version to a changelog entry; version truth diverges from docs. Add or retitle a ## [29.3.12] section aligned with plugin.json (or document intermediate versioning explicitly).
- **Suggested revision**: Address the concern above.

### FINDING_2: panel [code-review/accepted]

## **Important** `security` — `scripts/hook-anti-read-poll.sh:65`: the hook injects `basename "$file_path"` directly into `additionalContext`, which is treated as a system-reminder-style message. Concrete scenario: a repo contains a filename with a newline and instruction-like text; after three repeated reads, the hook emits that attacker-controlled basename inside high-priority context, creating a prompt-injection path. Suggested fix: omit the filename from the reminder or sanitize it to a short printable allowlist before interpolation.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `security` — `scripts/hook-anti-read-poll.sh:65`: the hook injects `basename "$file_path"` directly into `additionalContext`, which is treated as a system-reminder-style message. Concrete scenario: a repo contains a filename with a newline and instruction-like text; after three repeated reads, the hook emits that attacker-controlled basename inside high-priority context, creating a prompt-injection path. Suggested fix: omit the filename from the reminder or sanitize it to a short printable allowlist before interpolation.
- **Suggested revision**: Address the concern above.

### FINDING_23: panel [code-review/accepted]

## risk-integration: scripts/hook-anti-read-poll.sh:64-68

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Warning re-fires on every subsequent identical read while still in the 30s window. Sustained polling floods additionalContext. Fire only on transition to threshold or throttle repeats.
- **Suggested revision**: Address the concern above.

### FINDING_24: panel [code-review/accepted]

## risk-integration: scripts/test-hook-anti-read-poll.sh:2362-2374

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Opening trio uses wall-clock time across three hook runs. If wall time between calls exceeds 30s the hook resets and the third call may not emit additionalContext; CI could flake sporadically. Use HOOK_ANTI_READ_POLL_NOW for the first three calls like the window-reset tests.
- **Suggested revision**: Address the concern above.

### FINDING_25: panel [code-review/accepted]

## risk-integration: skills/implement/scripts/write-rejected-findings.sh:2595-2627

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Log copy uses rejected-findings-full.md but REJECTED_COUNT still comes from bare rejected-findings.md when both exist. Bare ledger can under-report vs the copied full markdown; no harness asserts REJECTED_COUNT for the both-files case. Align counting with detail_file when full is chosen, or document and test the split contract explicitly.
- **Suggested revision**: Address the concern above.

### FINDING_27: panel [code-review/accepted]

## risk-integration: skills/implement/scripts/write-rejected-findings.sh:66-71

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Redaction/copy pipeline errors are swallowed with || true and stderr redirected away. Run log can omit rejected-findings content while emit lines report STATUS=ok and a count, hiding tool/permission/disk failures. Propagate pipeline failure: emit STATUS failed or omit ok until verify -s output; avoid silencing stderr for the redact chain.
- **Suggested revision**: Address the concern above.

### FINDING_14: panel [code-review/accepted]

## correctness: scripts/hook-anti-read-poll.sh:47-64

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Negative age not handled when now &lt; first_ts Clock skew or corrupt state can satisfy the 30s window test with negative elapsed time and skew streak resets Clamp negative age to treat as window expired or reset when first_ts &gt; now
- **Suggested revision**: Address the concern above.

### FINDING_25: panel [code-review/accepted]

## risk-integration: skills/implement/scripts/write-rejected-findings.sh:103-108

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Persist failure path emits REJECTED_COUNT=0 despite prior successful count from non-empty detail_file. Downstream consumers or grep-only transcripts can read REJECTED_COUNT=0 while tmpdir still holds rejected findings; Step 16 uses || true so exit status may be ignored. Emit the computed count on the failure path (or add a separate persist-failure field) and assert it in test-write-rejected-findings.sh.
- **Suggested revision**: Address the concern above.

### FINDING_28: panel [code-review/accepted]

## security: scripts/hook-anti-read-poll.sh:60-61

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Hook persists tool_input.file_path into a tab-delimited state line without delimiter escaping. A file_path value containing TAB or newline corrupts TSV parsing and breaks consecutive-read detection. Strip or reject control characters in file_path before writing state, or persist state as JSON with jq.
- **Suggested revision**: Address the concern above.

### FINDING_7: panel [code-review/accepted]

## code-quality: scripts/compose-review-findings.md:5-8

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Contract lists only round-*/rejected-findings.md while the script prefers rejected-findings-full.md when present. Operators or tests following only the markdown contract may omit full.md and see different composed output than production. Document rejected-findings-full.md first, then bare rejected-findings.md (and parent tmpdir fallback) to match compose-review-findings.sh:163-176.
- **Suggested revision**: Address the concern above.

