# Review Round 2

- Mode: `diff`
- Accepted findings: 6
- Rejected findings: 0
- Exonerated findings: 11
- Neutral findings: 0

## Accepted Findings

### FINDING_1: **architecture** `docs/run-logs.md:144-148` — The updated contract describes only the new per-finding key set (`schema_version` / `reviewer_slots`) as if it were universal for `review-findings-full.jsonl`, but the repository still contains many historical committed rows under `larch-logs/**/review-findings-full.jsonl` that use the legacy `reviewer` string and omit `schema_version` (and at least one stub line uses yet another envelope shape). A whole-repo or cross-run miner that keys strictly off the documented v2 fields will silently drop reviewer attribution on older lines or mis-handle mixed streams. **Suggested fix:** Add an explicit backward-compatibility note in this section (and optionally a one-liner in `scripts/compose-review-findings.md` near the field table) stating that consumers must treat `reviewer_slots`+`schema_version` as v2 when present, and fall back to legacy `reviewer` (and absence of `schema_version`) for older committed batches, or branch on `has("reviewer_slots")` / `has("reviewer")`.
- **Reviewer**: dyn-schema-consumers-output.txt
- **Concern**: - **architecture** `docs/run-logs.md:144-148` — The updated contract describes only the new per-finding key set (`schema_version` / `reviewer_slots`) as if it were universal for `review-findings-full.jsonl`, but the repository still contains many historical committed rows under `larch-logs/**/review-findings-full.jsonl` that use the legacy `reviewer` string and omit `schema_version` (and at least one stub line uses yet another envelope shape). A whole-repo or cross-run miner that keys strictly off the documented v2 fields will silently drop reviewer attribution on older lines or mis-handle mixed streams. **Suggested fix:** Add an explicit backward-compatibility note in this section (and optionally a one-liner in `scripts/compose-review-findings.md` near the field table) stating that consumers must treat `reviewer_slots`+`schema_version` as v2 when present, and fall back to legacy `reviewer` (and absence of `schema_version`) for older committed batches, or branch on `has("reviewer_slots")` / `has("reviewer")`.
- **Suggested revision**: Address the concern above.


### FINDING_12: architecture: skills/review/SKILL.md:10
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Opening Skill prose still documents gather→dispatch→collect→vote→emit with no aggregate stage. Operators and orchestrators relying on SKILL.md for the round pipeline get a stage list that does not match review-core (aggregate between collect and voters). Update the pipeline string to include aggregate (and when it is skipped), consistent with review-core.md and aggregate-findings.md.
- **Suggested revision**: Address the concern above.


### FINDING_18: correctness: skills/review/scripts/collect-findings.sh:1485-1486
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Removing sort -u drops identical-row dedupe before findings are numbered. Two identical TSV rows from overlapping collectors produce duplicate FINDING blocks and inflated counts until aggregation; aggregation may leave duplicates if they are not semantically merged. Dedupe stable keys with first-seen order preserved or add a targeted regression if double-emission is impossible by construction.
- **Suggested revision**: Address the concern above.


### FINDING_19: risk-integration: SECURITY.md:58-72
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] New pre-vote LLM aggregation dispatches full findings.md through external tools but SECURITY.md only tweaks compose wording; no explicit trust/telemetry bullet for aggregate-findings + dispatch-with-waterfall. Compliance reviews and on-call triage lack a documented statement that aggregator prompts live under the session tmpdir, inherit the same argv/.meta visibility model as other launch-review lanes, and feed untrusted reviewer prose into another model pass before mechanical validation. Add a concise SECURITY.md subsection describing aggregator prompt construction, dispatch surface, tmpdir containment, validation-before-replace, and pointer to execution-issues warnings on fallback.
- **Suggested revision**: Address the concern above.


### FINDING_21: risk-integration: scripts/compose-review-findings.sh:169-189
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] JSONL schema replaces reviewer string with schema_version plus reviewer_slots. External tooling that still expects .reviewer on review-findings-full.jsonl breaks after upgrade without code changes. Announce breaking schema in CHANGELOG and optionally dual-write for one release if external compatibility is required.
- **Suggested revision**: Address the concern above.


### FINDING_27: security: skills/review/scripts/aggregate-findings.sh:40-41,137-141,294-303
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Symlink-following reads of findings and aggregator output before external LLM dispatch A symlinked findings.md (or output path) can pivot reads to another local regular file; contents are embedded into aggregator-prompt.md and sent to external review tools, leaking unintended file bytes to the vendor. Reject symlinks; resolve paths and require they remain under the session review tmpdir; or use non-following open semantics before building the prompt.
- **Suggested revision**: Address the concern above.


