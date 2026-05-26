### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: correctness: scripts/parse-codex-usage.sh:37-51
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] has_tokenish ignores total_tokens-only token_usage events. Stream only has {"type":"token_usage","total_tokens":N} without per-bucket fields: fail-closed, zero Codex cost in reports. Extend probes if Codex ships total-only rollups, or keep fail-closed with an explicit diagnostic.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: risk-integration: scripts/parse-codex-usage.sh:79-92
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Last token_usage event wins over summed per-turn usage. Future CLI emitting a partial final token_usage after richer per-turn events would under-report Codex cost silently. Document and fixture-test multi token_usage behavior; assert chosen rollup policy explicitly.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: risk-integration: skills/implement/scripts/test-codex-implementer.sh:647-756
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Test 10 skipped entirely when jq is missing. Local make test-codex-implementer without jq passes without exercising --json or fail-closed ledger behavior. Split jq-independent argv/ledger-absence checks from jq JSONL row assertions.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_19: **No command injection**: `EVENTS_FILE` is passed as a quoted `jq` input path; parsed values are digit-validated before `printf`/ledger writes; `token-ledger.sh` additionally enforces `is_uint` on bucket fields.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **No command injection**: `EVENTS_FILE` is passed as a quoted `jq` input path; parsed values are digit-validated before `printf`/ledger writes; `token-ledger.sh` additionally enforces `is_uint` on bucket fields.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_20: **Fail-closed accounting**: Parse failure writes no ledger row / leaves `${OUTPUT}.token-record` empty; review launcher only records on `EXIT_CODE == 0`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Fail-closed accounting**: Parse failure writes no ledger row / leaves `${OUTPUT}.token-record` empty; review launcher only records on `EXIT_CODE == 0`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_21: **Secret / prompt leakage**: `*.events.jsonl` is excluded from `larch-log.sh` and `design-log-publish.sh`; `SECURITY.md` documents session-local-only handling; `test-design-log-publish.sh` asserts denied basenames (including `render-cache/`) do not publish.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Secret / prompt leakage**: `*.events.jsonl` is excluded from `larch-log.sh` and `design-log-publish.sh`; `SECURITY.md` documents session-local-only handling; `test-design-log-publish.sh` asserts denied basenames (including `render-cache/`) do not publish.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_22: **Fixtures**: Checked-in JSONL contains only synthetic token counts, no credentials.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Fixtures**: Checked-in JSONL contains only synthetic token counts, no credentials.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_28

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_28: architecture: scripts/launch-review.sh:560-561
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Review records tokens only on success; implement/CI record whenever parse succeeds Failed codex review with JSONL usage writes no vendor row; failed implement/CI with same JSONL would still record; session totals diverge Document lane policy or align exit-code gating across launchers
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_29

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_29: correctness: scripts/parse-codex-usage.sh:79
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Multiple token_usage events use last only, not sum If CLI emits incremental non-cumulative token_usage snapshots, reported totals undercount Document cumulative assumption; add fixture when CLI shape is known
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_30

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_30: risk-integration: scripts/parse-codex-usage.sh:78
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] jq slurps entire events file into memory Very long --json runs could use large RAM before parsing Consider streaming reduce if large sidecars appear in production
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_31

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_31: correctness: scripts/parse-codex-usage.sh:78-91
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Parser uses last type==token_usage rollup instead of summing all usage-bearing events as the plan requires. A Codex run whose JSONL contains per-call msg.usage rows plus a final token_usage line will bill only the rollup (or diverge from tests that assume full summation), conflicting with the plan edge case Multiple usage events per run summed across events. Align summation with the plan or formally change the contract in plan/docs/tests and add a mixed-stream regression for the chosen rule.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: code-quality: scripts/parse-codex-usage.sh:34-92
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Monolithic ~60-line jq with dual rollup/reduce paths is hard to maintain. Future Codex schema changes require editing fragile inline jq; higher risk of subtle double-count or last-wins bugs. Split into staged jq filter or documented filter file plus bash bucket math.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: correctness: scripts/parse-codex-usage.sh:79-82
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Last token_usage event wins; no test for multiple token_usage lines. If Codex emits more than one token_usage rollup per run, earlier usage is dropped and cost under-reports. Validate real CLI behavior; add multi-token_usage fixture and document policy.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_6: code-quality: scripts/parse-codex-usage.sh:83-88,119-122
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate cached_tokens > input_tokens guard in jq and bash. Redundant logic increases drift risk if one site changes. Keep jq-only enforcement unless a non-jq fallback exists.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_8: correctness: scripts/launch-review.sh:560-562
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Review records Codex usage only when EXIT_CODE is 0; implement and CI record whenever JSONL parses. Codex review exits 1 with valid token_usage in .events.jsonl: no codex_review ledger row, session cost omits Codex while implement/CI would record the same events. Document asymmetry in launcher docs or align all three launchers on the same exit-code vs parse-success rule.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: correctness: scripts/parse-codex-usage.sh:79-82
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] When token_usage events exist, parser uses last row only instead of summing multiple token_usage rows. Multiple incremental token_usage events (non-cumulative): TOTAL reflects last delta only; cost understated. Validate against real CLI; if incremental rows are possible, sum token_usage events or detect monotonic cumulative rollups.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

