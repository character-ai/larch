### FINDING_1: **Important** `risk-integration` `skills/review-and-fix/scripts/review-and-fix.sh:535`  
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `skills/review-and-fix/scripts/review-and-fix.sh:535`      The new run-root aggregate in `rejected-findings.md` is bypassed by the code-review tally body whenever `$IMPLEMENT_TMPDIR/rejected-findings-full.md` is non-empty. Concrete scenario: round 1 rejects finding A and round 2 rejects finding B; `write_rejected_findings_aggregate` builds `rejected-findings.md` with both rounds, but line 535 prefers the latest-round `rejected-findings-full.md`, so the committed `code-review-tally` records only B. Prefer the aggregate `rejected-findings.md` for tally/log consumers after this change, or make `rejected-findings-full.md` contain the same aggregate once multi-round full details exist.
- **Suggested revision**: Address the concern above.

### FINDING_2: **Important** `risk-integration` `skills/review/references/heavy-worker.md:65`  
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `risk-integration` `skills/review/references/heavy-worker.md:65`      The subagent `/review` contract still tells the worker to write `review-summary.json` with `schema_version: 1` and no `panel` object. Concrete scenario: a user runs `/review --diff --subagent`; the inline script path emits schema v2 with `panel.scout_status`, but the subagent path follows this prompt and produces the old schema, so downstream run-log observability is inconsistent by invocation mode. Update the heavy-worker schema and instructions to v2, including `panel.scout_status`, `panel.static_slot_count`, `panel.dynamic_slot_count`, and `panel.total_slot_count`.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] architecture: skills/review/references/heavy-worker.md (not modified on branch)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Doc/schema narrative for review-summary.json may lag emit-tally’s new v2 panel fields. Operators or subagents following heavy-worker only could author or validate the wrong JSON shape; not introduced by edits to this file in the diff. Sync heavy-worker (and related review docs) in a separate doc-only change.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] architecture: skills/review/references/heavy-worker.md:65-83
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Heavy-worker review-summary JSON example is still schema_version 1 without panel while emit-tally now emits v2 with panel. Subagents following heavy-worker.md may author JSON that omits panel or uses the wrong schema_version. Update heavy-worker contract in a follow-up doc pass.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] architecture: skills/review/references/heavy-worker.md:65-83
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Heavy-worker still documents review-summary.json schema_version 1 without panel while emit-tally now emits v2 with panel. Subagent-written summaries may omit fields observability readers expect from script runs. Update heavy-worker contract in a dedicated docs change; not touched by this branch diff.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] code-quality: skills/review/references/heavy-worker.md:65-83
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Canonical heavy-worker JSON example omits schema v2 and panel object. Prompt-side /review subagent instructions can diverge from files emit-tally writes on disk. Update heavy-worker when you want a single cross-path JSON contract (file not touched in this branch).
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] code-quality: skills/review/scripts/review-core.md:68-74
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] review-core.md does not mention review-summary.json schema_version 2 or panel fields added by emit-tally. Readers of review-core.md miss the new structured fields. Update review-core.md when convenient.
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: skills/review/scripts/emit-tally.sh:116-137
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Block comment claims JSON matches heavy-worker.md contract; emit now uses schema_version 2 and panel while heavy-worker example remains v1 without panel. Readers trust the comment and mis-implement or mis-validate review-summary.json against the wrong schema. Retarget the comment to emit-tally.md (or refresh heavy-worker.md in a follow-up).
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: skills/implement/SKILL.md:1674-1676 skills/implement/scripts/write-final-report.sh:47-56
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Step 7a invokes write-final-report.sh before ship-pr-state.sh exists; PR_URL defaults to N/A and is committed via larch-log.sh commit while post-merge refresh cannot commit a corrected batch. On a typical first-pass merge=true run, ship-pr-state.sh is only written at Step 8+ (SKILL.md:1688-1689) after Step 7a; write-final-report.sh reads PR_URL from that file and substitutes N/A (write-final-report.sh:54-71). The pre-bump commit freezes final-summary.md with PR: N/A; after merge the sentinel blocks larch-log commits so the merged PR tree can keep N/A even though a real PR URL exists after Step 8+. Defer GitHub upsert or split file-only emission for Step 7a; or refresh final-summary into larch-log after PR_URL exists but before merge; or read PR from a source populated before Step 7a.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: skills/review-and-fix/scripts/review-and-fix.sh:611-649
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Run-root rejected-findings aggregate omits the latest round’s bare ledger whenever any earlier round still has a non-empty rejected-findings-full.md. Round 1 keeps a non-empty round-1/rejected-findings-full.md; round 2 only writes compact round-2/rejected-findings.md. The aggregate includes only Round 1 full prose and silently drops Round 2 rejections from IMPLEMENT_TMPDIR/rejected-findings.md. Merge per-round: use full markdown when present for that round, otherwise include that round’s compact rejected-findings.md; or include fallback_file for the current round when its full file is missing/empty.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: skills/review-and-fix/scripts/review-and-fix.sh:611-656 skills/review-and-fix/scripts/review-and-fix.sh:849-853
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Full-detail aggregate overwrites run-root rejected-findings.md using only non-empty round-*/rejected-findings-full.md and ignores the current round compact ledger when any older full file exists. Round 1 has non-empty round-1/rejected-findings-full.md; round 2 only produces non-empty round-2/rejected-findings.md. Run-root rejected-findings.md ends with round 1 full prose only and omits round 2 rejections, regressing prior cp of the latest round ledger. When any full files exist, build per-round sections in numeric order using non-empty rejected-findings-full.md when present else non-empty rejected-findings.md for that round; keep bare-only fallback only when no round has non-empty full; add a mixed-round regression test.
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: skills/review-and-fix/scripts/review-and-fix.sh:611-657 skills/review-and-fix/scripts/review-and-fix.sh:853
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] write_rejected_findings_aggregate failures are masked with || true, leaving a stale run-root rejected-findings.md. After round 1 wrote an aggregate, round 2 adds new round-2/rejected-findings-full.md but mktemp or mv fails inside write_rejected_findings_aggregate; the function exits non-zero, || true ignores it, and IMPLEMENT_TMPDIR/rejected-findings.md still shows the round-1-only aggregate. Propagate failures or log and fall back explicitly; avoid blanket || true on the aggregate writer.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: skills/review/scripts/emit-tally.sh:101-102
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Digit-only validation allows leading zeros for slot counts. Dispatch emits `09`; jq `--argjson` may fail and abort emit-tally. Strip leading zeros or validate strict decimal JSON integers before jq.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: skills/implement/SKILL.md:1674-1680
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] New Step 7a `write-final-report.sh` uses bare `|| true` next to text that forbids bare `|| true` without `append-tool-failure` capture for flush-style tools. write-final-report fails (non-zero exit); failure is invisible in execution-issues and the pre-bump log commit may omit final-summary while the operator assumes observability is restored. Wrap the call like other Step 7a tools: `if ! write-final-report.sh ...; then append-tool-failure ...; fi` (or equivalent), aligned with the step’s own rules.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: skills/implement/SKILL.md:1674-1680
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] New write-final-report.sh line in the Step 7a fenced block uses bare || true while the same block instructs operators to capture non-zero pre-bump tool failures via append-tool-failure.sh. write-final-report.sh can fail (non-zero) and leave no execution-issues breadcrumb, contradicting the adjacent capture contract for the flush family. Apply the same append-tool-failure.sh capture used for token-report/timing-report/larch-log, or explicitly carve out write-final-report in the prose if uncaptured failure is intentional.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: skills/implement/scripts/write-final-report.md:218-222
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Documentation of the new Step 7a call omits that PR_URL is still unavailable because ship-pr-state.sh is written only at Step 8+. Operators follow write-final-report.md and still do not expect PR: N/A in the committed run-log artifact. Document ship-pr-state ordering and which fields are provisional at Step 7a vs Step 17/18.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: skills/review-and-fix/scripts/review-and-fix.sh:611-656
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Full-detail aggregate never falls back to the per-round compact ledger once any older round has a non-empty rejected-findings-full.md. If an earlier round keeps a non-empty full file while a later round records new rejections only in rejected-findings.md (missing or empty full), run-root rejected-findings.md can silently omit those newer rejections compared to the old per-round copy behavior. Add a regression test for mixed full vs ledger-only rounds and either document unsupported mixes or append ledger-only sections when full-detail mode is active.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: skills/review-and-fix/scripts/review-and-fix.sh:853
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] write_rejected_findings_aggregate failures are masked with || true. mktemp/mv failure leaves stale or missing implement tmp rejected-findings.md while the round still reports complete. Surface failure via append_log_write_failure or propagate non-zero without swallowing when aggregate is required for observability.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: skills/review-and-fix/scripts/review-and-fix.sh:853;skills/rereview-and-fix/scripts/review-and-fix.sh:write_rejected_findings_aggregate
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] `write_rejected_findings_aggregate ... || true` swallows mktemp/mv/IO failures. Disk full on `mv` to rejected-findings.md; round completes successfully but run-root rejected-findings.md stays stale from a prior round. Narrow `|| true` to expected benign cases or record append-tool-failure when aggregate write fails.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: skills/review/scripts/emit-tally.sh:134-168
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] review-summary.json bumps schema_version from 1 to 2 and adds panel. External scripts or dashboards that require schema_version==1 may mis-handle or ignore new summaries, breaking automated consumers without parallel updates. Update consumer contracts and docs, or retain backward-compatible versioning policy if strict equality checks exist in the wild.
- **Suggested revision**: Address the concern above.

