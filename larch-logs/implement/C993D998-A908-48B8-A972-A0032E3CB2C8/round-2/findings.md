### FINDING_1: **Important** `security` — `scripts/hook-anti-read-poll.sh:28-60`: the hook writes a predictable state file under shared `${TMPDIR:-/tmp}` and continues even if `chmod 700 "$state_dir"` fails. Concrete scenario: on a multi-user machine, another local user pre-creates `/tmp/larch-read-poll` as writable and places `state-<cwd_hash>.tsv` as a symlink to a victim-writable file; the victim’s next `Read` hook invocation follows the symlink at line 60 and overwrites that file with the TSV state. Suggested fix: fail open unless the state directory is owned by the current user with private permissions, reject symlink state files, and write via a private temp file plus atomic rename.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `security` — `scripts/hook-anti-read-poll.sh:28-60`: the hook writes a predictable state file under shared `${TMPDIR:-/tmp}` and continues even if `chmod 700 "$state_dir"` fails. Concrete scenario: on a multi-user machine, another local user pre-creates `/tmp/larch-read-poll` as writable and places `state-<cwd_hash>.tsv` as a symlink to a victim-writable file; the victim’s next `Read` hook invocation follows the symlink at line 60 and overwrites that file with the TSV state. Suggested fix: fail open unless the state directory is owned by the current user with private permissions, reject symlink state files, and write via a private temp file plus atomic rename.
- **Suggested revision**: Address the concern above.

### FINDING_2: **Important** `security` — `scripts/hook-anti-read-poll.sh:65`: the hook injects `basename "$file_path"` directly into `additionalContext`, which is treated as a system-reminder-style message. Concrete scenario: a repo contains a filename with a newline and instruction-like text; after three repeated reads, the hook emits that attacker-controlled basename inside high-priority context, creating a prompt-injection path. Suggested fix: omit the filename from the reminder or sanitize it to a short printable allowlist before interpolation.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `security` — `scripts/hook-anti-read-poll.sh:65`: the hook injects `basename "$file_path"` directly into `additionalContext`, which is treated as a system-reminder-style message. Concrete scenario: a repo contains a filename with a newline and instruction-like text; after three repeated reads, the hook emits that attacker-controlled basename inside high-priority context, creating a prompt-injection path. Suggested fix: omit the filename from the reminder or sanitize it to a short printable allowlist before interpolation.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] architecture: .agnix.toml:26
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Agnix disables AS-014 for repo regex false positives Slightly weaker static guardrails; not a runtime trust boundary change Accept as tooling tradeoff or replace with narrower suppression
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] architecture: .claude-plugin/plugin.json;CHANGELOG.md;.agnix.toml;scripts/github-remote-repo.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Branch bundles agnix/regex/version-bump changes not listed in the P+Q implementation plan. Plan-fidelity traceability for the bundle is incomplete relative to the pasted Items 1–10 only. Treat as separate PR metadata or extend the written plan when merging narratives.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] code-quality: scripts/github-remote-repo.sh:68-75
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Regex-only change to github host spelling in character class. Unrelated to Items P/Q; increases review surface without functional tie to the feature. Keep such churn isolated in separate commits/PRs when possible.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] correctness: scripts/compose-review-findings.sh:77-151
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] REJ_C counter resets per parse_artifact file; IDs can repeat across rounds in one output. Multi-round composed output can contain multiple ### REJ_C1 sections keyed differently downstream. Pre-existing design; consider a global counter or round-prefixed ids if consumers need uniqueness.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] correctness: skills/implement/scripts/write-rejected-findings.sh:62-63
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] grep count pattern still misses emit-tally compact ledger lines of the form LINE:FINDING_n_OUTCOME=rejected. Multi-reject rounds still emit REJECTED_COUNT=1 whenever only the compact file supplies the summary. Add an _OUTCOME=rejected$ alternative (and tests) or derive count from structured markers in the full file when present.
- **Suggested revision**: Address the concern above.

### FINDING_8: architecture: scripts/hook-anti-read-poll.sh:170-199
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Single TSV state file updated non-atomically per Read. Concurrent PostToolUse invocations can race and corrupt count/first_ts, causing missed or spurious warnings. Document best-effort semantics or add atomic write locking if guarantees matter.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: scripts/hook-anti-read-poll.sh:143-149
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Three separate jq passes over the same JSON input. Extra process spawns on every Read PostToolUse event. Combine field extraction into one jq call.
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: scripts/hook-anti-read-poll.sh:193-198
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Warning emits on every Read while count stays >=3 within the window. Long identical read sequences flood additionalContext repeatedly until 30s window lapses. Fire only on first crossing of threshold or add cooldown between emissions.
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: scripts/test-hook-anti-read-poll.sh:32-38
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] First test block uses real time; window tests use injected now. Rare CI pause >30s between hook runs could make call 3 not fire. Use HOOK_ANTI_READ_POLL_NOW for all streak assertions.
- **Suggested revision**: Address the concern above.

### FINDING_12: code-quality: scripts/test-hook-anti-read-poll.sh:96-104
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Path-reset test uses a new cwd rather than same-cwd path alternation. Regression may miss bugs in per-project state keyed only by cwd_hash when paths alternate within one session. Add a same-cwd multi-path sequence assertion per the original plan text.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: scripts/compose-review-findings.sh:127-145
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Inner-heading guard only treats FINDING_/OOS_ ### lines as in-body; other ### subsections inside a rejected block hit the generic flush. rejected-findings-full.md containing e.g. ### Notes inside a block loses that heading and splits the record early. Broaden in-body ### handling while pending_id is set for code-review-rejected, or document supported subsection shapes only.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: scripts/compose-review-findings.sh:127-148
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Generic ### lines inside a code-review-rejected block flush pending and split records. Extra markdown sub-headings inside a rejected tally block truncate or duplicate composed findings. Treat unknown ### lines inside open rejected blocks as body, or whitelist flush separators.
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: scripts/hook-anti-read-poll.sh:28-31
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] State file path layout differs from implementation plan Item Q §6 literal (${TMPDIR}/larch-read-poll-${CWD_HASH}.tsv vs larch-read-poll/state-${cwd_hash}.tsv). Anyone following only the plan’s path string could look for the wrong file when debugging hook state; runtime behavior and sibling doc match the code, not the old path string. Update the plan archive or cross-link hook-anti-read-poll.md as the canonical path contract.
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

### FINDING_20: risk-integration: scripts/hook-anti-read-poll.md
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Doc implies different offsets never trigger warnings. Operators misconfigure expectations vs per-offset third-read behavior. Clarify per-(path,offset) streak and third-read-at-that-offset semantics.
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: scripts/hook-anti-read-poll.sh:28-31
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Implementation state path layout differs from the implementation_plan prose (subdir state-*.tsv vs flat larch-read-poll-${hash}.tsv). No runtime bug; operators following only the old plan sentence may look for the wrong filename. Align docs/plan snippet with scripts/hook-anti-read-poll.md or vice versa.
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: scripts/hook-anti-read-poll.sh:41-61
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Unlocked read-modify-write on shared state.tsv for the same cwd. Concurrent hook runs could corrupt count/first_ts and skew warnings. Use flock or atomic replace writes for state updates if concurrency is plausible.
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

### FINDING_26: risk-integration: skills/implement/scripts/write-rejected-findings.sh:62-71
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Redaction pipeline errors swallowed with || true after truncating output; fallback cp can copy full findings without redaction Partial or empty log file on redactor failure; missing +x on redactors copies larger raw review text than old bare ledger Write temp then mv on success only; surface failures; tighten fallback when detail_file is the full artifact
- **Suggested revision**: Address the concern above.

### FINDING_27: risk-integration: skills/implement/scripts/write-rejected-findings.sh:66-71
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Redaction/copy pipeline errors are swallowed with || true and stderr redirected away. Run log can omit rejected-findings content while emit lines report STATUS=ok and a count, hiding tool/permission/disk failures. Propagate pipeline failure: emit STATUS failed or omit ok until verify -s output; avoid silencing stderr for the redact chain.
- **Suggested revision**: Address the concern above.

### FINDING_28: security: scripts/hook-anti-read-poll.sh:10
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Unbounded stdin slurp into memory for hook JSON Hostile huge PostToolUse payload could spike hook memory Bound input size or stream jq
- **Suggested revision**: Address the concern above.

### FINDING_29: security: scripts/hook-anti-read-poll.sh:28-61
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Predictable state path under world-writable TMPDIR with redirect write and non-fatal chmod on state_dir Shared-host attacker may race a symlink so the hook truncates or follows an unintended target file for the same uid Fail closed on mkdir/chmod errors; use exclusive temp+mv; or relocate state under user-private cache
- **Suggested revision**: Address the concern above.

