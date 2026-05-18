### FINDING_10: code-quality: scripts/hook-anti-read-poll.sh:193-198
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Warning emits on every Read while count stays >=3 within the window. Long identical read sequences flood additionalContext repeatedly until 30s window lapses. Fire only on first crossing of threshold or add cooldown between emissions.
- **Suggested revision**: Address the concern above.


### FINDING_11: code-quality: scripts/test-hook-anti-read-poll.sh:32-38
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] First test block uses real time; window tests use injected now. Rare CI pause >30s between hook runs could make call 3 not fire. Use HOOK_ANTI_READ_POLL_NOW for all streak assertions.
- **Suggested revision**: Address the concern above.


### FINDING_13: correctness: scripts/compose-review-findings.sh:127-145
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Inner-heading guard only treats FINDING_/OOS_ ### lines as in-body; other ### subsections inside a rejected block hit the generic flush. rejected-findings-full.md containing e.g. ### Notes inside a block loses that heading and splits the record early. Broaden in-body ### handling while pending_id is set for code-review-rejected, or document supported subsection shapes only.
- **Suggested revision**: Address the concern above.


### FINDING_16: correctness: scripts/test-hook-anti-read-poll.sh:31-63
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Wall-clock dependent assertions for the 3-hit warning without pinning HOOK_ANTI_READ_POLL_NOW. If CI pauses >30s between the first and third simulated Read, hook resets the streak and the test fails intermittently. Use run_hook with synthetic timestamps (as in lines 79-93) or inject HOOK_ANTI_READ_POLL_NOW for all streak assertions.
- **Suggested revision**: Address the concern above.


### FINDING_17: correctness: skills/implement/scripts/write-rejected-findings.sh:45-76
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] REJECTED_COUNT is derived from summary_file via a regex that does not match emit-tally compact grep lines; zero matches force count=1. Multi-reject rounds: log shows full detail for N rejections but quiet stream still reports count=1 (common when bare md is grep-n ledger). Count from detail_file markers (e.g. ### [rejected]) or from tally/review-summary counts aligned with emit-tally.
- **Suggested revision**: Address the concern above.


### FINDING_18: correctness: skills/implement/scripts/write-rejected-findings.sh:65-71
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Redact pipeline for log copy discards stderr and uses || true on the whole write. Failed redaction or broken pipe can yield empty rejected-findings.md in the run log while STATUS=ok still reports success. Validate output size after write or use controlled error handling instead of silent || true; fall back to cp with visible failure.
- **Suggested revision**: Address the concern above.


### FINDING_19: risk-integration: CHANGELOG.md:14-20 vs .claude-plugin/plugin.json
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] CHANGELOG section is [29.3.11] while plugin.json version is 29.3.12 and changelog never mentions 29.3.12. Operators and release notes readers cannot map the installed plugin version to a changelog entry; version truth diverges from docs. Add or retitle a ## [29.3.12] section aligned with plugin.json (or document intermediate versioning explicitly).
- **Suggested revision**: Address the concern above.


### FINDING_2: **Important** `security` — `scripts/hook-anti-read-poll.sh:65`: the hook injects `basename "$file_path"` directly into `additionalContext`, which is treated as a system-reminder-style message. Concrete scenario: a repo contains a filename with a newline and instruction-like text; after three repeated reads, the hook emits that attacker-controlled basename inside high-priority context, creating a prompt-injection path. Suggested fix: omit the filename from the reminder or sanitize it to a short printable allowlist before interpolation.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `security` — `scripts/hook-anti-read-poll.sh:65`: the hook injects `basename "$file_path"` directly into `additionalContext`, which is treated as a system-reminder-style message. Concrete scenario: a repo contains a filename with a newline and instruction-like text; after three repeated reads, the hook emits that attacker-controlled basename inside high-priority context, creating a prompt-injection path. Suggested fix: omit the filename from the reminder or sanitize it to a short printable allowlist before interpolation.
- **Suggested revision**: Address the concern above.


### FINDING_23: risk-integration: scripts/hook-anti-read-poll.sh:64-68
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Warning re-fires on every subsequent identical read while still in the 30s window. Sustained polling floods additionalContext. Fire only on transition to threshold or throttle repeats.
- **Suggested revision**: Address the concern above.


### FINDING_24: risk-integration: scripts/test-hook-anti-read-poll.sh:2362-2374
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Opening trio uses wall-clock time across three hook runs. If wall time between calls exceeds 30s the hook resets and the third call may not emit additionalContext; CI could flake sporadically. Use HOOK_ANTI_READ_POLL_NOW for the first three calls like the window-reset tests.
- **Suggested revision**: Address the concern above.


### FINDING_25: risk-integration: skills/implement/scripts/write-rejected-findings.sh:2595-2627
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Log copy uses rejected-findings-full.md but REJECTED_COUNT still comes from bare rejected-findings.md when both exist. Bare ledger can under-report vs the copied full markdown; no harness asserts REJECTED_COUNT for the both-files case. Align counting with detail_file when full is chosen, or document and test the split contract explicitly.
- **Suggested revision**: Address the concern above.


### FINDING_27: risk-integration: skills/implement/scripts/write-rejected-findings.sh:66-71
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Redaction/copy pipeline errors are swallowed with || true and stderr redirected away. Run log can omit rejected-findings content while emit lines report STATUS=ok and a count, hiding tool/permission/disk failures. Propagate pipeline failure: emit STATUS failed or omit ok until verify -s output; avoid silencing stderr for the redact chain.
- **Suggested revision**: Address the concern above.


