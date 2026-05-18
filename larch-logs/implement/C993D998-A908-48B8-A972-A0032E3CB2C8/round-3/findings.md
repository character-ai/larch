### FINDING_1: [OUT_OF_SCOPE] architecture: Branch vs merge-base diff (e.g. .agnix.toml scripts/github-remote-repo.sh CHANGELOG 29.3.11)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Additional changes not enumerated in the supplied P+Q implementation plan. Plan-fidelity review of P+Q cannot treat those hunks as required deliverables. None for this review; split or document bundled scope if traceability is required.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] architecture: larch-logs/implement/** (diff)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Large committed run-log directories in same PR Noise for reviewers focused on hook and writer logic only None per project policy; split PRs if desired for review ergonomics
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] code-quality: scripts/github-remote-repo.sh:25-32
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Regex-only tweak escaping dots in github.com. No functional tie to rejected-findings or Read-poll work. None required for this feature.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] correctness: scripts/compose-review-findings.sh:77-151
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] REJ_C* ids restart per parse_artifact invocation, so duplicate headings across rounds are possible. Pre-existing counter scoping; unchanged by this branch. None for this review scope.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] risk-integration: skills/implement/SKILL.md:1768
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Step 16 documentation still describes only bare rejected-findings.md copy. Orchestrator text may diverge from write-rejected-findings.sh behavior for operators reading SKILL only. Update Step 16 prose when editing SKILL for a related change.
- **Suggested revision**: Address the concern above.

### FINDING_6: architecture: scripts/hook-anti-read-poll.sh:2247-2250
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] State file lives under larch-read-poll/state-<hash>.tsv instead of the plan’s flat larch-read-poll-<hash>.tsv filename. None beyond doc/plan drift; isolation and permissions behavior still match design. Update the plan reference or rename paths for literal alignment if that matters to operators.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: scripts/compose-review-findings.md:5-8
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Contract lists only round-*/rejected-findings.md while the script prefers rejected-findings-full.md when present. Operators or tests following only the markdown contract may omit full.md and see different composed output than production. Document rejected-findings-full.md first, then bare rejected-findings.md (and parent tmpdir fallback) to match compose-review-findings.sh:163-176.
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: scripts/hook-anti-read-poll.sh:13-20
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Five jq invocations per hook run on the same JSON. Extra fork/exec on every Read in busy sessions. Parse tool_name, file_path, offset, cwd in one jq call.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: skills/implement/scripts/write-rejected-findings.sh:43-51
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Full artifact preference applies whenever full exists, not only when --run-id and --log-root are set as the plan described. REJECTED_COUNT/details= follow full.md even when no log copy runs, a broader behavior change than the written plan. Gate detail_file on log args or update plan and write-rejected-findings.md to state global preference explicitly.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/hook-anti-read-poll.sh:19-20
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Non-digit offset strings become 0 Distinct non-integer offsets could collapse into one counter bucket Document contract or parse offset via jq as integer only
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: scripts/hook-anti-read-poll.sh:19-20;scripts/hook-anti-read-poll.sh:47-48
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] String equality on offset allows 10 vs 010 to reset the streak. Third consecutive read with semantically identical offset but different string form never reaches threshold=3. Normalize offsets numerically before comparison.
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: scripts/hook-anti-read-poll.sh:40-61
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Unlocked read/modify/write of the per-cwd state TSV. Concurrent hook invocations corrupt state lines; counter may reset or jump so the warning fires late or not at all. Use flock or write-to-temp-then-mv with doc on residual risk.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: scripts/hook-anti-read-poll.sh:41-44
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] last_offset read from state is not normalized like incoming offset. Stale last_offset 01 vs new offset 1 resets the counter and can suppress the third-read warning. Normalize last_offset with the same digit-only case stanza used for offset.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: scripts/hook-anti-read-poll.sh:47-64
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Negative age not handled when now < first_ts Clock skew or corrupt state can satisfy the 30s window test with negative elapsed time and skew streak resets Clamp negative age to treat as window expired or reset when first_ts > now
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: scripts/hook-anti-read-poll.sh:63-68
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] age=(now-first_ts) is not clamped for clock skew or test clocks. Negative age keeps -le 30 true so the threshold branch can fire after long real gaps if first_ts > now. Use max(0,now-first_ts) or reset streak when now < first_ts.
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: skills/implement/scripts/write-rejected-findings.sh:2726-2763
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Item P required REJECTED_COUNT from bare rejected-findings.md while copying full detail; implementation counts from detail_file (full when present). Downstream logic that expects the ledger count to match the compact summary while the run log shows the full artifact can see mismatched counts if full and summary diverge. Compute count from rejected-findings.md as the plan states, or formally amend the plan/docs if full-derived counts are the intended contract.
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: skills/implement/scripts/write-rejected-findings.sh:43-77;skills/implement/scripts/write-rejected-findings.md:12-17
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] REJECTED_COUNT is taken from detail_file (prefers full) instead of bare rejected-findings.md as the implementation plan specified. If bare ledger count and full ### block count diverge, emitted REJECTED_COUNT follows full, contradicting the plan's split heuristic. Either implement bare-only counting per plan or formally amend the plan and linked issue text.
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: skills/implement/scripts/write-rejected-findings.sh:62-74
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] count_rejected_findings defaults to 1 when no header/ledger pattern matches in a non-empty detail file Non-empty full artifact with unexpected formatting yields REJECTED_COUNT=1 and STATUS=ok, overstating rejections for downstream consumers of the quiet stream. Return 0 on no match or add a validated tally-based fallback.
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: skills/implement/scripts/write-rejected-findings.sh:62-74
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Unknown-format nonempty file yields count 1 Corrupt or future-format rejected artifact mis-reported as exactly one finding Return 0 or explicit unknown status instead of defaulting to 1
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: .agnix.toml:25-26
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Repository-wide disable of agnix AS-014 for bash regex false positives. Future real AS-014 violations could be masked until the rule is re-enabled or narrowed. Prefer scoped suppression if tooling allows; otherwise document periodic agnix rule review.
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: .agnix.toml:41
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] AS-014 added to global disabled_rules in agnix config. Later edits that would have failed AS-014 for patterns the rule is meant to catch can pass agent-lint until caught elsewhere. Re-evaluate removing AS-014 from disabled_rules if agent-lint passes with only the github[.]com regex rewrites; use narrower suppression if agnix supports it.
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: scripts/compose-review-findings.sh:127-132
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Reviewer slot now carries finding id for tally format Consumers expecting human reviewer names in composed markdown may mis-parse emitted sections Document contract or separate reviewer vs finding id in output
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: scripts/hook-anti-read-poll.sh:13-17
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Hook requires tool_input.file_path; unknown/alternate payload shapes skip all logic. Host JSON rename drops file_path; anti-poll warning never fires though reads repeat. Add defensive field aliases or a fixture from a real PostToolUse Read payload.
- **Suggested revision**: Address the concern above.

### FINDING_24: risk-integration: scripts/test-hook-anti-read-poll.sh:76-84
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Different-path reset test uses a new cwd so it does not hit the same state file as earlier cases. Less assurance that path switching resets state in the real single-project cwd_hash file. Keep cwd constant and only change file_path in the reset scenario.
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: skills/implement/scripts/write-rejected-findings.sh:103-108
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Persist failure path emits REJECTED_COUNT=0 despite prior successful count from non-empty detail_file. Downstream consumers or grep-only transcripts can read REJECTED_COUNT=0 while tmpdir still holds rejected findings; Step 16 uses || true so exit status may be ignored. Emit the computed count on the failure path (or add a separate persist-failure field) and assert it in test-write-rejected-findings.sh.
- **Suggested revision**: Address the concern above.

### FINDING_26: risk-integration: skills/implement/scripts/write-rejected-findings.sh:104-108
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] On persist failure REJECTED_COUNT is forced to 0 Run summary or automation may record zero rejections while tmpdir still holds rejected content; plausible wrong gating or reporting Preserve computed REJECTED_COUNT on copy failure or add explicit PERSIST/ COPY flags separate from count
- **Suggested revision**: Address the concern above.

### FINDING_27: risk-integration: skills/implement/scripts/write-rejected-findings.sh:2789-2797
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] On log-copy failure the helper emits REJECTED_COUNT=0 with STATUS=failed, hiding the real tally for consumers that ignore STATUS. Automation that only parses REJECTED_COUNT may treat a failed copy as “zero rejections” despite non-empty source files. Preserve the computed count on the failure path or document that REJECTED_COUNT must not be trusted unless STATUS=ok.
- **Suggested revision**: Address the concern above.

### FINDING_28: security: scripts/hook-anti-read-poll.sh:60-61
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Hook persists tool_input.file_path into a tab-delimited state line without delimiter escaping. A file_path value containing TAB or newline corrupts TSV parsing and breaks consecutive-read detection. Strip or reject control characters in file_path before writing state, or persist state as JSON with jq.
- **Suggested revision**: Address the concern above.

