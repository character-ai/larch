### [rejected] FINDING_10

### FINDING_10: correctness: scripts/hook-anti-read-poll.sh:19-20
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Non-digit offset strings become 0 Distinct non-integer offsets could collapse into one counter bucket Document contract or parse offset via jq as integer only
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_12

### FINDING_12: correctness: scripts/hook-anti-read-poll.sh:40-61
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Unlocked read/modify/write of the per-cwd state TSV. Concurrent hook invocations corrupt state lines; counter may reset or jump so the warning fires late or not at all. Use flock or write-to-temp-then-mv with doc on residual risk.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_13

### FINDING_13: correctness: scripts/hook-anti-read-poll.sh:41-44
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] last_offset read from state is not normalized like incoming offset. Stale last_offset 01 vs new offset 1 resets the counter and can suppress the third-read warning. Normalize last_offset with the same digit-only case stanza used for offset.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_15

### FINDING_15: correctness: scripts/hook-anti-read-poll.sh:63-68
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] age=(now-first_ts) is not clamped for clock skew or test clocks. Negative age keeps -le 30 true so the threshold branch can fire after long real gaps if first_ts > now. Use max(0,now-first_ts) or reset streak when now < first_ts.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_17

### FINDING_17: correctness: skills/implement/scripts/write-rejected-findings.sh:43-77;skills/implement/scripts/write-rejected-findings.md:12-17
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] REJECTED_COUNT is taken from detail_file (prefers full) instead of bare rejected-findings.md as the implementation plan specified. If bare ledger count and full ### block count diverge, emitted REJECTED_COUNT follows full, contradicting the plan's split heuristic. Either implement bare-only counting per plan or formally amend the plan and linked issue text.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_19

### FINDING_19: correctness: skills/implement/scripts/write-rejected-findings.sh:62-74
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Unknown-format nonempty file yields count 1 Corrupt or future-format rejected artifact mis-reported as exactly one finding Return 0 or explicit unknown status instead of defaulting to 1
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_21

### FINDING_21: risk-integration: .agnix.toml:41
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] AS-014 added to global disabled_rules in agnix config. Later edits that would have failed AS-014 for patterns the rule is meant to catch can pass agent-lint until caught elsewhere. Re-evaluate removing AS-014 from disabled_rules if agent-lint passes with only the github[.]com regex rewrites; use narrower suppression if agnix supports it.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_23

### FINDING_23: risk-integration: scripts/hook-anti-read-poll.sh:13-17
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Hook requires tool_input.file_path; unknown/alternate payload shapes skip all logic. Host JSON rename drops file_path; anti-poll warning never fires though reads repeat. Add defensive field aliases or a fixture from a real PostToolUse Read payload.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_6

### FINDING_6: architecture: scripts/hook-anti-read-poll.sh:2247-2250
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] State file lives under larch-read-poll/state-<hash>.tsv instead of the plan’s flat larch-read-poll-<hash>.tsv filename. None beyond doc/plan drift; isolation and permissions behavior still match design. Update the plan reference or rename paths for literal alignment if that matters to operators.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_8

### FINDING_8: code-quality: scripts/hook-anti-read-poll.sh:13-20
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Five jq invocations per hook run on the same JSON. Extra fork/exec on every Read in busy sessions. Parse tool_name, file_path, offset, cwd in one jq call.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_9

### FINDING_9: code-quality: skills/implement/scripts/write-rejected-findings.sh:43-51
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Full artifact preference applies whenever full exists, not only when --run-id and --log-root are set as the plan described. REJECTED_COUNT/details= follow full.md even when no log copy runs, a broader behavior change than the written plan. Gate detail_file on log args or update plan and write-rejected-findings.md to state global preference explicitly.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

