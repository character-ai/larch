### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: code-quality: scripts/launch-review.sh:560-576 scripts/launch-codex-implement.sh:357-371 scripts/launch-codex-ci.sh:230-245
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Triplicated parse-codex-usage KV loop and vendor-write logic across three launchers. A future bucket or validation change lands in two launchers but not the third, reintroducing inconsistent Codex ledger rows across review/implement/CI lanes. Extract a shared record-codex-usage-from-events helper (KV parse + fail-closed) with per-launcher sinks for token-ledger vs token-record.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: risk-integration: scripts/launch-review.sh:493-527; scripts/launch-codex-implement.sh:322-337; scripts/launch-codex-ci.sh:193-205
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] After splitting Codex stdout to .events.jsonl, auth/transient classifiers read stderr sidecars only. Codex CLI change or failure mode that prints login/quota/auth text only on the JSON stdout stream will skip auth retries and leave operators with unclassified launcher failures plus no token-ledger row (fail-closed). Add optional stdout auth-regex scan of .events.jsonl on non-zero exit when stderr is non-auth; document stderr-primary contract in SECURITY.md.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: correctness: scripts/parse-codex-usage.sh:36-49
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Parser omits .msg.input_tokens-style coalesce paths. Codex emits TokenUsage fields under msg without a usage wrapper; parser returns 1 and launchers skip ledger rows on successful runs. Add .msg.input_tokens // … to each field probe; add a harness fixture for that shape.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: architecture: scripts/launch-review.sh:494-510
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Retry loops rm events.jsonl each attempt; only final attempt is parsed. Multi-retry runs can drop billable usage from earlier attempts when the final attempt fails before emitting JSONL. Document last-attempt-only semantics in launcher docs, or accumulate usage across attempts if required.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: correctness: scripts/parse-codex-usage.sh:36-76
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Aggregate-only JSONL events (total_tokens only) fail closed. Successful Codex run with only total_tokens in events records nothing; cost line absent despite spend. Emit explicit diagnostic or document requirement for per-bucket fields in CLI output.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: code-quality: scripts/parse-codex-usage.sh:21-24
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Empty and missing events files share one error string. Operators cannot tell “file never created” from “Codex wrote zero bytes” when debugging token gaps. Use distinct stderr messages for missing vs empty files.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: correctness: scripts/launch-codex-implement.sh:357-371
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Per-bucket record-vendor runs even when LAUNCHER_EXIT is non-zero if events parse. Failed implement runs with partial JSONL still add Codex cost to session ledgers and summaries. Gate recording on LAUNCHER_EXIT==0 if success-only billing is intended; else document post-failure recording in launch-codex-implement.md.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_5: correctness: scripts/parse-codex-usage.sh:71-72
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] jq tonumber? output is not validated as integers before bash arithmetic. A JSONL line with fractional input_tokens causes (( )) to fail under set -e; helper exits without a clear diagnostic and launchers skip ledger writes. Validate TSV fields with ^[0-9]+$ before arithmetic or compute totals entirely in jq.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

