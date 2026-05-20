### FINDING_1: [OUT_OF_SCOPE] code-quality: docs/run-logs.md:148
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] The category blurb still only says best-effort extraction and may be empty, without the whitelist constraint now documented in compose-review-findings.md. Readers of run-logs.md alone may misunderstand downstream JSONL category semantics after this branch. Align the sentence with compose-review-findings.md in a follow-up edit (file not touched by this diff).
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] risk-integration: larch-logs/implement/80C6B507-11E4-4C71-AC42-EC8F3CD604D8/*
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Committed implement run-log tree appears in the diff alongside the feature. Out of scope per review instructions; only note if log content were wrong, which it is not. No action required for CI or test obligations.
- **Suggested revision**: Address the concern above.

### FINDING_3: `07e2a508` — Address code review feedback (round 1)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `07e2a508` — Address code review feedback (round 1) **Traceability (feature + implementation plan vs diff)** | Requirement | Diff evidence | |---------------|----------------| | `extract_category()` validates against the five focus-area tags and returns empty otherwise | [`scripts/compose-review-findings.sh`](scripts/compose-review-findings.sh): `candidate` + whitelist `if` + `exit`; only prints on match. | | Same extraction logic as before (bold vs colon branches), then gate on whitelist | Matches the plan’s AWK structure; adds `gsub` trim on `candidate` (not in plan text; consistent with intent). | | Regression tests for mangled shapes + valid tags | [`scripts/test-compose-review-findings.sh`](scripts/test-compose-review-findings.sh): new block exercises invented heading, file-link-as-title, prose-only title, comma-heavy title, plus `code-quality` / `architecture` / `security` colon forms; `FINDINGS_TOTAL=7` and assertions on `OOS_CR1_*` ids. | | Canonical + bold “already works” | Pre-existing sections unchanged in diff: `=== category is extracted...` (correctness) and `=== OOS bold-markdown ## line...` (risk-integration bold + colon). | | Doc: category field notes validation | [`scripts/compose-review-findings.md`](scripts/compose-review-findings.md) `category` line updated with whitelist + empty-on-unknown. | **Note:** The implementation plan text said a “6 findings” `oos.md` fixture; the branch implements **seven** `### FINDING_*` entries, which matches the feature text (four mangled + three added valid tags) better than the plan’s count. That is a **plan wording slip**, not a missing implementation. `parse_artifact` for OOS still prefixes `## $pending_title` before `extract_category` ([`scripts/compose-review-findings.sh` `flush_pending`](scripts/compose-review-findings.sh)), so the new fixtures do exercise `extract_category()` on the same synthetic leading `##` line as production.
- **Suggested revision**: Address the concern above.

### FINDING_4: `07e2a508` — `Address code review feedback (round 1)`
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `07e2a508` — `Address code review feedback (round 1)` Diff summary: whitelist validation in `extract_category()` ([`scripts/compose-review-findings.sh`](scripts/compose-review-findings.sh)), doc update ([`scripts/compose-review-findings.md`](scripts/compose-review-findings.md)), regression block in [`scripts/test-compose-review-findings.sh`](scripts/test-compose-review-findings.sh), plus committed `larch-logs/implement/80C6B507-.../` artifacts (per repo policy, not treated as scope drift). ---
- **Suggested revision**: Address the concern above.

### FINDING_5: `2d5968e1` — `fix(compose-review-findings): whitelist extract_category focus-area tags`
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `2d5968e1` — `fix(compose-review-findings): whitelist extract_category focus-area tags`
- **Suggested revision**: Address the concern above.

### FINDING_6: `2d5968e1` — fix(compose-review-findings): whitelist extract_category focus-area tags  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `2d5968e1` — fix(compose-review-findings): whitelist extract_category focus-area tags
- **Suggested revision**: Address the concern above.

### FINDING_7: `f9c82468` — `chore(larch-logs): flush implement run 80C6B507-11E4-4C71-AC42-EC8F3CD604D8`
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `f9c82468` — `chore(larch-logs): flush implement run 80C6B507-11E4-4C71-AC42-EC8F3CD604D8`
- **Suggested revision**: Address the concern above.

### FINDING_8: `f9c82468` — chore(larch-logs): flush implement run 80C6B507-11E4-4C71-AC42-EC8F3CD604D8  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `f9c82468` — chore(larch-logs): flush implement run 80C6B507-11E4-4C71-AC42-EC8F3CD604D8
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: scripts/compose-review-findings.sh:83-88
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Five-tag allowlist is duplicated as repeated string equality checks alongside the same roster in compose-review-findings.md. Adding or renaming a focus-area tag risks updating one location and missing the other, producing silent mismatch between docs and runtime. Use an awk associative array for the allowlist or add a prominent cross-reference comment tying the AWK roster to scripts/compose-review-findings.md as the single behavioral spec.
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: scripts/test-compose-review-findings.sh:87-97
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Baseline harness omits category assertions for FINDING_1 and FINDING_2 Accepted/plan category contract can change silently without failing tests Add jq assertions for category on those ids matching the chosen contract
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: scripts/test-compose-review-findings.sh:336-383
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] New regression block omits invalid-token bold-markdown heading A refactor could drop or bypass bold-branch whitelist logic while colon-only cases still pass, letting non-tag tokens leak again undetected Add one OOS fixture with title shaped like **not-a-focus-tag** — … and assert empty category
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/compose-review-findings.sh:63-117
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Five-tag whitelist runs for all emit_record paths via extract_category on every prose body Free-form accepted/plan titles like Architecture boundary or Runtime bug (harness fixtures) used to populate category and now always serialize as empty unless they equal a focus-area tag, which can break downstream consumers expecting the old best-effort label outside OOS Scope validation to code-review out_of_scope only or document breaking change and assert category in baseline harness
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: scripts/test-compose-review-findings.sh:283-330
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Mangled-category harness covers colon-style and prose titles only; no OOS fixture exercises extract_category’s bold `**…**` branch for a non-whitelisted token. A future edit could break bold-path parsing or validation while colon-path tests still pass, weakening the regression signal for dynamic reviewer headings. Add one OOS finding whose composed body starts with `## **<non-tag>** — …` and assert `category` is empty.
- **Suggested revision**: Address the concern above.

