### FINDING_1: **[`scripts/token-cost.md`](scripts/token-cost.md)** — The `/research` note is expanded into an explicit divergence table (callers, rate env vars, N/A vs omitted column, display format, output shape), consistent with [`scripts/token-cost.sh`](scripts/token-cost.sh) (`rate_or_na`, Claude fallback to `LARCH_TOKEN_RATE_PER_M`, per-vendor rates, `%.2f`, `TOTAL_COST` summation).
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 2. **[`scripts/token-cost.md`](scripts/token-cost.md)** — The `/research` note is expanded into an explicit divergence table (callers, rate env vars, N/A vs omitted column, display format, output shape), consistent with [`scripts/token-cost.sh`](scripts/token-cost.sh) (`rate_or_na`, Claude fallback to `LARCH_TOKEN_RATE_PER_M`, per-vendor rates, `%.2f`, `TOTAL_COST` summation).
- **Suggested revision**: Address the concern above.

### FINDING_2: **[`scripts/token-tally.md`](scripts/token-tally.md)** — A symmetric “`/implement` and `/fix-issue`” section was added with the inverted table, consistent with [`scripts/token-tally.sh`](scripts/token-tally.sh) (single `LARCH_TOKEN_RATE_PER_M`, regex + positive check, `$%.4f`, omit `$` column when unsupported).
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 3. **[`scripts/token-tally.md`](scripts/token-tally.md)** — A symmetric “`/implement` and `/fix-issue`” section was added with the inverted table, consistent with [`scripts/token-tally.sh`](scripts/token-tally.sh) (single `LARCH_TOKEN_RATE_PER_M`, regex + positive check, `$%.4f`, omit `$` column when unsupported). Secondary scan: nothing in the diff contradicts a stated plan constraint.
- **Suggested revision**: Address the concern above.

### FINDING_3: **`RUN_ID` guard in [`skills/implement/scripts/write-final-report.sh`](skills/implement/scripts/write-final-report.sh)** — A `case "$RUN_ID" in */*|*'..'*) … esac` block runs immediately after `RUN_ID` is resolved from `parent-issue.md` or `session-id` (lines 74–81), before `run_dir` and `mkdir -p` (lines 110–116). It matches [`scripts/refresh-run-logs.sh`](scripts/refresh-run-logs.sh) lines 39–41. Emitting `COMMENT_URL` before `STATUS`/`ERROR` aligns with `fail_usage` and the `mkdir -p` failure path; exit code is `1` like the other hard failures in that script. This meets the plan’s ordering and intent.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 1. **`RUN_ID` guard in [`skills/implement/scripts/write-final-report.sh`](skills/implement/scripts/write-final-report.sh)** — A `case "$RUN_ID" in */*|*'..'*) … esac` block runs immediately after `RUN_ID` is resolved from `parent-issue.md` or `session-id` (lines 74–81), before `run_dir` and `mkdir -p` (lines 110–116). It matches [`scripts/refresh-run-logs.sh`](scripts/refresh-run-logs.sh) lines 39–41. Emitting `COMMENT_URL` before `STATUS`/`ERROR` aligns with `fail_usage` and the `mkdir -p` failure path; exit code is `1` like the other hard failures in that script. This meets the plan’s ordering and intent.
- **Suggested revision**: Address the concern above.

### FINDING_4: **architecture** `scripts/token-cost.md:25-45` — The unchanged Environment blurb still says unset, empty, or zero rates yield `N/A` “for that vendor’s cost,” which is easy to read as unconditional per vendor, while the new divergence table correctly explains that **Claude** can still produce a numeric `CLAUDE_COST` when only `LARCH_TOKEN_RATE_PER_M` is set (because `token-cost.sh` applies that fallback before `rate_or_na`). The new table therefore **amplifies** an internal inconsistency for readers who skim the Environment section and the Note separately. **Suggested fix:** Tighten the Environment paragraph (or add a one-line pointer) so it states costs are computed **after** the Claude-specific `LARCH_TOKEN_RATE_PER_M` fallback, matching both `token-cost.sh` and the new table.
- **Reviewer**: dyn-doc-consistency-output.txt
- **Concern**: - **architecture** `scripts/token-cost.md:25-45` — The unchanged Environment blurb still says unset, empty, or zero rates yield `N/A` “for that vendor’s cost,” which is easy to read as unconditional per vendor, while the new divergence table correctly explains that **Claude** can still produce a numeric `CLAUDE_COST` when only `LARCH_TOKEN_RATE_PER_M` is set (because `token-cost.sh` applies that fallback before `rate_or_na`). The new table therefore **amplifies** an internal inconsistency for readers who skim the Environment section and the Note separately. **Suggested fix:** Tighten the Environment paragraph (or add a one-line pointer) so it states costs are computed **after** the Claude-specific `LARCH_TOKEN_RATE_PER_M` fallback, matching both `token-cost.sh` and the new table.
- **Suggested revision**: Address the concern above.

### FINDING_5: **architecture** `scripts/token-cost.md:3-5,39-41` — The file header already states `token-cost.sh` is used by `scripts/render-run-summary.sh` and the final-report helpers, but the new table’s **Callers** row lists only `/implement` and `/fix-issue`, omitting the shared renderer (and any direct harness invocations of `token-cost.sh`). That is not a transpose error against `token-tally.md`, but it **introduces** a same-file architectural mismatch between “who calls this script” in the intro versus the table. **Suggested fix:** Rename the row (for example to “Primary skills / workflows”) and name `render-run-summary.sh` in the `token-cost.sh` cell, or add a parenthetical such as “(via `scripts/render-run-summary.sh`; see above).”
- **Reviewer**: dyn-doc-consistency-output.txt
- **Concern**: - **architecture** `scripts/token-cost.md:3-5,39-41` — The file header already states `token-cost.sh` is used by `scripts/render-run-summary.sh` and the final-report helpers, but the new table’s **Callers** row lists only `/implement` and `/fix-issue`, omitting the shared renderer (and any direct harness invocations of `token-cost.sh`). That is not a transpose error against `token-tally.md`, but it **introduces** a same-file architectural mismatch between “who calls this script” in the intro versus the table. **Suggested fix:** Rename the row (for example to “Primary skills / workflows”) and name `render-run-summary.sh` in the `token-cost.sh` cell, or add a parenthetical such as “(via `scripts/render-run-summary.sh`; see above).”
- **Suggested revision**: Address the concern above.

### FINDING_6: **architecture** `scripts/token-tally.md:67-77` — The lead sentence says “`/implement` and `/fix-issue` use `token-cost.sh`,” which skips the documented integration path through `scripts/render-run-summary.sh` (called from both skills’ `write-final-report.sh`), while `scripts/token-cost.md` still presents `render-run-summary.sh` as the primary shell-out. **Suggested fix:** Align wording with the sibling contract—for example state that final summaries pull optional USD lines through `render-run-summary.sh`, which shells `token-cost.sh`, so the table’s “Callers” row stays consistent with how the repo actually wires costs.
- **Reviewer**: dyn-doc-consistency-output.txt
- **Concern**: - **architecture** `scripts/token-tally.md:67-77` — The lead sentence says “`/implement` and `/fix-issue` use `token-cost.sh`,” which skips the documented integration path through `scripts/render-run-summary.sh` (called from both skills’ `write-final-report.sh`), while `scripts/token-cost.md` still presents `render-run-summary.sh` as the primary shell-out. **Suggested fix:** Align wording with the sibling contract—for example state that final summaries pull optional USD lines through `render-run-summary.sh`, which shells `token-cost.sh`, so the table’s “Callers” row stays consistent with how the repo actually wires costs.
- **Suggested revision**: Address the concern above.

### FINDING_7: **architecture** `skills/implement/scripts/write-final-report.md:61-63` — The text says `RUN_ID` values containing `/` or `..` are rejected using “the same path-traversal guard” as `scripts/refresh-run-logs.sh`, but `refresh-run-logs.sh` treats that case as a **non-fatal skip** (`REFRESH_SKIPPED=true REASON=invalid-run-id`, `exit 0`), while `write-final-report.sh` emits **failure KVs** and **`exit 1`**. Only the `case` pattern aligns; outcomes and contracts differ, so “same guard” overstates equivalence for operators comparing the two scripts. **Suggested fix:** Rephrase to say the scripts share the same **character-class rejection** (`*/*` / `*'..'*)`) and point to `refresh-run-logs.sh` only as a pattern reference, explicitly noting that `write-final-report.sh` fails closed with `STATUS=failed` whereas `refresh-run-logs.sh` skips refresh with exit status `0`.
- **Reviewer**: dyn-doc-consistency-output.txt
- **Concern**: - **architecture** `skills/implement/scripts/write-final-report.md:61-63` — The text says `RUN_ID` values containing `/` or `..` are rejected using “the same path-traversal guard” as `scripts/refresh-run-logs.sh`, but `refresh-run-logs.sh` treats that case as a **non-fatal skip** (`REFRESH_SKIPPED=true REASON=invalid-run-id`, `exit 0`), while `write-final-report.sh` emits **failure KVs** and **`exit 1`**. Only the `case` pattern aligns; outcomes and contracts differ, so “same guard” overstates equivalence for operators comparing the two scripts. **Suggested fix:** Rephrase to say the scripts share the same **character-class rejection** (`*/*` / `*'..'*)`) and point to `refresh-run-logs.sh` only as a pattern reference, explicitly noting that `write-final-report.sh` fails closed with `STATUS=failed` whereas `refresh-run-logs.sh` skips refresh with exit status `0`.
- **Suggested revision**: Address the concern above.

### FINDING_8: **correctness** `scripts/token-cost.md:43-44` — The new comparison-table row for “Cost display” nests multiple single-backtick spans (`from `awk` `%.2f` …` and `` `awk` `$%.4f` ``), which is not reliably parseable in GitHub-flavored Markdown table cells and can truncate or mis-render the intended `awk` / format-string text so readers no longer see a faithful description of the scripts’ output. **Suggested fix:** Rewrite those cells without nested inline code (for example plain prose like “awk, two decimal places, no dollar prefix” / “awk, dollar-prefixed four decimal places”), use `<code>…</code>`, or use the usual doubled-backtick outer delimiter with padded inner spaces so every delimiter pair is unambiguous.
- **Reviewer**: dyn-path-guard-logic-output.txt
- **Concern**: - **correctness** `scripts/token-cost.md:43-44` — The new comparison-table row for “Cost display” nests multiple single-backtick spans (`from `awk` `%.2f` …` and `` `awk` `$%.4f` ``), which is not reliably parseable in GitHub-flavored Markdown table cells and can truncate or mis-render the intended `awk` / format-string text so readers no longer see a faithful description of the scripts’ output. **Suggested fix:** Rewrite those cells without nested inline code (for example plain prose like “awk, two decimal places, no dollar prefix” / “awk, dollar-prefixed four decimal places”), use `<code>…</code>`, or use the usual doubled-backtick outer delimiter with padded inner spaces so every delimiter pair is unambiguous.
- **Suggested revision**: Address the concern above.

### FINDING_9: **correctness** `scripts/token-tally.md:76` — The symmetric “Cost display” cell repeats the same nested-backtick pattern (`Markdown cost suffix from `awk` `$%.4f` …` and `Dollar strings from `awk` `%.2f` …`), so it carries the same Markdown rendering risk as `scripts/token-cost.md:43-44`. **Suggested fix:** Apply the same formatting change as for `scripts/token-cost.md` so both contract docs stay readable where they are meant to clarify intentional divergence.
- **Reviewer**: dyn-path-guard-logic-output.txt
- **Concern**: - **correctness** `scripts/token-tally.md:76` — The symmetric “Cost display” cell repeats the same nested-backtick pattern (`Markdown cost suffix from `awk` `$%.4f` …` and `Dollar strings from `awk` `%.2f` …`), so it carries the same Markdown rendering risk as `scripts/token-cost.md:43-44`. **Suggested fix:** Apply the same formatting change as for `scripts/token-cost.md` so both contract docs stay readable where they are meant to clarify intentional divergence.
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] **Callers** framed as “`/research` only” vs “`/implement`, `/fix-issue`” is product-centric: CI and offline harnesses also execute these scripts directly; that predates this change’s intent and is a general doc precision trade-off, not a mirror defect between the two new tables.
- **Reviewer**: dyn-doc-consistency-output.txt
- **Concern**: - **Callers** framed as “`/research` only” vs “`/implement`, `/fix-issue`” is product-centric: CI and offline harnesses also execute these scripts directly; that predates this change’s intent and is a general doc precision trade-off, not a mirror defect between the two new tables.
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 1. **architecture** `skills/implement/scripts/write-final-report.md:114-116` — The implementation plan’s file list named only `write-final-report.sh`, `token-cost.md`, and `token-tally.md`; the branch also updates the script contract in `write-final-report.md` (`RUN_ID` validation and KV behavior). This is helpful for consumers but was not an enumerated deliverable in that plan. **Suggested fix:** For future runs, include contract docs in the “Files to modify” list when they are part of the intended surface, or treat this as an acceptable doc follow-through with no action required.
- **Suggested revision**: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 2. **correctness** `skills/implement/scripts/write-final-report.sh` (pre-existing adjacent behavior) — Empty `RUN_ID` is still not rejected by this guard and is outside what the plan specified. **Suggested fix:** None required for this plan’s scope; only note if a later hardening pass wants to reject empty IDs before `run_dir` construction.
- **Suggested revision**: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Empty `RUN_ID` still passes the new `case` guard (only `/` and substring `..` are rejected) and was already able to reach `run_dir` / `mkdir -p` before this change; tightening empty IDs would be a separate hardening pass, not introduced by the diff.
- **Reviewer**: dyn-path-guard-logic-output.txt
- **Concern**: - Empty `RUN_ID` still passes the new `case` guard (only `/` and substring `..` are rejected) and was already able to reach `run_dir` / `mkdir -p` before this change; tightening empty IDs would be a separate hardening pass, not introduced by the diff.
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] The `*/*|*'..'*` pattern matches any substring `..` (for example inside `...`), the same tradeoff as [scripts/refresh-run-logs.sh](scripts/refresh-run-logs.sh) lines 39–40; exotic legitimate IDs containing two consecutive dots would still be rejected.
- **Reviewer**: dyn-path-guard-logic-output.txt
- **Concern**: - The `*/*|*'..'*` pattern matches any substring `..` (for example inside `...`), the same tradeoff as [scripts/refresh-run-logs.sh](scripts/refresh-run-logs.sh) lines 39–40; exotic legitimate IDs containing two consecutive dots would still be rejected.
- **Suggested revision**: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] The two Markdown tables are faithful **transposes** of each other on the rows shown in the diff; the substantive script claims checked against `scripts/token-cost.sh` and `scripts/token-tally.sh` (per-vendor rates with Claude-only `LARCH_TOKEN_RATE_PER_M` fallback, single global rate and regex-gated `$` column omission in tally, `%.2f` flat KV vs `$%.4f` markdown suffixes, `report` emitting a `## Token Spend …` section) match the implementation aside from shorthand in the “`## Token Spend`” label versus the full emitted heading string.
- **Reviewer**: dyn-doc-consistency-output.txt
- **Concern**: - The two Markdown tables are faithful **transposes** of each other on the rows shown in the diff; the substantive script claims checked against `scripts/token-cost.sh` and `scripts/token-tally.sh` (per-vendor rates with Claude-only `LARCH_TOKEN_RATE_PER_M` fallback, single global rate and regex-gated `$` column omission in tally, `%.2f` flat KV vs `$%.4f` markdown suffixes, `report` emitting a `## Token Spend …` section) match the implementation aside from shorthand in the “`## Token Spend`” label versus the full emitted heading string.
- **Suggested revision**: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] [AGENTS.md](AGENTS.md) instructs updating [SECURITY.md](SECURITY.md) when security-relevant behavior changes; this branch adds a RUN_ID path-component guard in [skills/implement/scripts/write-final-report.sh](skills/implement/scripts/write-final-report.sh) but does not update `SECURITY.md`, so the security changelog may lag the new fail-closed surface unless that policy is intentionally waived here.
- **Reviewer**: dyn-path-guard-logic-output.txt
- **Concern**: - [AGENTS.md](AGENTS.md) instructs updating [SECURITY.md](SECURITY.md) when security-relevant behavior changes; this branch adds a RUN_ID path-component guard in [skills/implement/scripts/write-final-report.sh](skills/implement/scripts/write-final-report.sh) but does not update `SECURITY.md`, so the security changelog may lag the new fail-closed surface unless that policy is intentionally waived here.
- **Suggested revision**: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] code-quality: skills/fix-issue/scripts/write-final-report.sh:88-91
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] No RUN_ID path guard on the fix-issue script. Low filesystem risk there but asymmetric hardening vs implement. Track separately if parity is desired.
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] correctness: scripts/token-cost.sh:16-22
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Malformed non-numeric rates are not coerced to N/A by rate_or_na. Unusual env values could yield odd cost output; unchanged by this branch. N/A for this PR; tighten validation only if product wants stricter rate parsing.
- **Suggested revision**: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] correctness: skills/implement/scripts/write-final-report.md:40-44
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Outputs table says summary-final and KV Always for paths that early-exit Automation reading Always may mis-handle failure modes Reconcile Outputs table with all early exits in a follow-up doc edit
- **Suggested revision**: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] correctness: skills/implement/scripts/write-final-report.sh:110-116
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Empty RUN_ID still reaches mkdir under implement/ suffix Empty RUN_ID yields run_dir ending with implement/ and shared subtree behavior unchanged Pre-exists; only note if tightening RUN_ID validation further
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] correctness: skills/implement/scripts/write-final-report.sh:73-116
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Empty RUN_ID still reaches mkdir under larch-logs/implement/. Unusual tmpdir state could create surprising paths; unchanged by this diff. Consider validating non-empty RUN_ID in a follow-up if product wants stricter IDs.
- **Suggested revision**: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] risk-integration: SECURITY.md
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] AGENTS.md recommends SECURITY.md updates for security-relevant changes Security changelog may omit the new RUN_ID rejection contract Add a short SECURITY or release note entry if maintainers want traceability
- **Suggested revision**: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] risk-integration: skills/implement/scripts/test-write-final-report.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] No regression test for invalid RUN_ID KV path. Guard could regress without CI signal; not required by this branch plan. Add harness fixture for bad RUN_ID when editing tests.
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] security: skills/implement/scripts/write-final-report.sh:74-115
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Empty RUN_ID still reaches mkdir after the new guard; run_dir collapses to implement/ under the tmpdir tree. Pre-existing awkward directory layout and log placement; not caused by the path-traversal guard. Address upstream writers of RUN_ID/session-id if empty IDs should be invalid; outside this branch’s stated goal.
- **Suggested revision**: Address the concern above.

### FINDING_25: architecture: scripts/token-cost.md:26-41;scripts/token-tally.md:67-79
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Duplicated normative divergence tables in two markdown authorities. Future rate or column contract change updated in only one table yields contradictory operator guidance across docs. Add cross-file keep-in-sync note or single canonical matrix with links.
- **Suggested revision**: Address the concern above.

### FINDING_26: code-quality: scripts/token-cost.md:26-41 and scripts/token-tally.md:67-79
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Near-identical divergence tables in two markdown files. Future edits to rate semantics or output shape may update one doc and leave the other stale. Centralize the table in one contract file and cross-link, or shorten one side to a pointer.
- **Suggested revision**: Address the concern above.

### FINDING_27: code-quality: skills/implement/scripts/write-final-report.md:61-63
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] "Same path-traversal guard" wording overstates parity with refresh-run-logs.sh. Readers may expect identical skip/fail semantics when only the case pattern matches. Clarify same rejection pattern, different exit contract and KV behavior.
- **Suggested revision**: Address the concern above.

### FINDING_28: correctness: skills/implement/scripts/write-final-report.md:114-116
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Doc says same guard as refresh-run-logs.sh without noting skip-vs-fail semantics differ. Operators may expect refresh-style exit 0 skip when RUN_ID is bad. Clarify same rejection pattern only; contrast refresh skip vs final-report hard fail.
- **Suggested revision**: Address the concern above.

### FINDING_29: correctness: skills/implement/scripts/write-final-report.md:61-63
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] RUN_ID validation doc scopes non-mutation to run-log tree only An operator may infer summary-final or upsert could still run on rejection even though the script exits before any writes Clarify exit happens before all run-summary writes and upsert not only under larch-logs/implement
- **Suggested revision**: Address the concern above.

### FINDING_30: correctness: skills/implement/scripts/write-final-report.sh:76-80
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] RUN_ID guard uses substring *'..'*, mirroring refresh-run-logs.sh A legitimate RUN_ID format that includes two adjacent dots for non-path reasons would be rejected and the final report step would fail closed. If such IDs are possible, align both scripts on an allowlist or segment-based rule and document the minted RUN_ID charset; otherwise no change.
- **Suggested revision**: Address the concern above.

### FINDING_31: risk-integration: skills/implement/scripts/write-final-report.md:61-63
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Doc says same guard as refresh-run-logs.sh but outcomes differ (skip vs fail). Operator assumes refresh-run-logs semantics and mis-reads severity or exit-code expectations when triaging write-final-report failures. Clarify same rejection pattern different envelope: skip+exit 0 vs STATUS=failed+exit 1.
- **Suggested revision**: Address the concern above.

### FINDING_32: risk-integration: skills/implement/scripts/write-final-report.sh:76-80
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] New RUN_ID path guard has no regression case in test-write-final-report.sh while CI runs that harness. A future edit could drop or bypass the case pattern; path traversal under larch-logs could return without CI failure. Add harness tmpdir(s) with malicious RUN_ID; assert non-zero exit, failed KV envelope, and no run-log tree writes for that RUN_ID.
- **Suggested revision**: Address the concern above.

