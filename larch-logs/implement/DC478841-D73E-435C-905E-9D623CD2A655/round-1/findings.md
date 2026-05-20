### FINDING_1: **Important** `correctness` [skills/review/scripts/tally-code-votes.sh:451](<OPERATOR_REPO_PATH>/skills/review/scripts/tally-code-votes.sh:451): Now that dynamic manifest entries are no longer skipped at [skills/review/scripts/tally-code-votes.sh:462](<OPERATOR_REPO_PATH>/skills/review/scripts/tally-code-votes.sh:462), the `seen` map needs the same fallback basename normalization used for manifest rows. Concrete failing scenario: the existing fallback-normalization fixture shape in `skills/review/scripts/test-tally-code-votes.sh:412-448` uses reviewer `dyn-foo-output-phase2.txt` with manifest output `dyn-foo-output.txt`; `seen` records the raw phase2 basename, then the manifest pass treats `dyn-foo-output.txt` as unseen and appends an extra zero-count `dyn-foo` row with `STATUS=OK`. Normalize `f[1]` through `norm_base()` before setting `seen[...]`, and add a regression asserting a dynamic phase2 finding does not also get a dead-slot row.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` [skills/review/scripts/tally-code-votes.sh:451](<OPERATOR_REPO_PATH>/skills/review/scripts/tally-code-votes.sh:451): Now that dynamic manifest entries are no longer skipped at [skills/review/scripts/tally-code-votes.sh:462](<OPERATOR_REPO_PATH>/skills/review/scripts/tally-code-votes.sh:462), the `seen` map needs the same fallback basename normalization used for manifest rows. Concrete failing scenario: the existing fallback-normalization fixture shape in `skills/review/scripts/test-tally-code-votes.sh:412-448` uses reviewer `dyn-foo-output-phase2.txt` with manifest output `dyn-foo-output.txt`; `seen` records the raw phase2 basename, then the manifest pass treats `dyn-foo-output.txt` as unseen and appends an extra zero-count `dyn-foo` row with `STATUS=OK`. Normalize `f[1]` through `norm_base()` before setting `seen[...]`, and add a regression asserting a dynamic phase2 finding does not also get a dead-slot row.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] architecture: scripts/lib-vote-tally.sh:37-46
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Awk FS=: plus clearing $1 can lose embedded colons in rare reviewer strings. Long reviewer tokens containing extra ':' characters may print a corrupted attribution; unchanged extraction logic in this PR. If needed later, join $2..NF with ':' instead of rebuilding $0 from fields.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] code-quality: scripts/lib-vote-tally.sh:37-47
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] FS=: splits on all colons in a line; unusual reviewer strings with extra colons may parse poorly. Rare malformed or pathological attribution values could truncate or skew extracted text. Only change if you decide to support multi-colon values; out of scope for this anchoring fix.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] code-quality: skills/review/scripts/tally-code-votes.sh:419-428 and skills/review/scripts/tally-code-votes.sh:477-487
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate basename normalization helpers (norm_base vs norm) in one script. Increases drift risk if normalization rules ever diverge. Refactor to a single shared awk snippet or shell-sourced fragment; not required for this PR.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] correctness: scripts/lib-vote-tally.sh:37-47
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Colon inside reviewer attribution truncates remainder when FS is : Attribution value like foo:bar prints only foo Pre-existing; fix by parsing first : only or joining fields if ever required
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] risk-integration: skills/design/scripts/tally-plan-review.sh:222
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Plan-review tally uses reviewer_for_block without a dedicated harness in this PR Non-canonical plan ballot attribution would map to unknown in the plan scoreboard; not exercised beyond unit tests Accept protocol-enforced format or add a small tally-plan-review fixture if drift is a concern
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] risk-integration: skills/review/scripts/tally-code-votes.sh:456-459
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Fragile NDJSON output path extraction via regex. Unusual JSON shapes could mis-parse output basenames for dead-slot rows. Pre-existing; consider a real JSON filter if this becomes security- or integrity-critical.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] security: skills/review/scripts/tally-code-votes.sh:320
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] reviewer TSV field is not normalized for embedded tabs/newlines. Malicious or accidental attribution text could break TSV structure for downstream tools. Not introduced by this diff; sanitize or reject control characters when writing score_rows if you harden this path later.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: scripts/lib-vote-tally.sh:32-34
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Function header comment overclaims generic asterisk tolerance vs anchored **Reviewer**: matching Maintainer may edit patterns assuming looser *-wrapper rules Match comment text to lib-vote-tally.md anchored contract
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: scripts/lib-vote-tally.sh:32-34
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Header comment claims generic '*' emphasis tolerance but matcher is anchored to **Reviewer(s)** or plain Reviewer(s):. Maintainers may re-widen the regex thinking single-* forms are still supported. Update the comment to match scripts/lib-vote-tally.md and the awk patterns.
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: scripts/lib-vote-tally.sh:32-34
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] reviewer_for_block header comment still describes generic * emphasis tolerance and vague matching; behavior is anchored **Reviewer(s)** or line-start Reviewer(s): only. A reader updating ballots or tests from the shell comment alone may expect old loose /Reviewer/ semantics and ship mismatched reviewer lines or false unknown/known splits. Reword the comment block above reviewer_for_block() to describe only the anchored bold and unbolded line-start forms documented in scripts/lib-vote-tally.md.
- **Suggested revision**: Address the concern above.

### FINDING_12: code-quality: scripts/lib-vote-tally.sh:32-34
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Header comment still describes generic * emphasis tolerance vs anchored **Reviewer(s)** patterns. Maintainers may re-loosen the matcher thinking *-wrapped variants are still supported. Update the comment to match the anchored bold and unbolded line-start contract.
- **Suggested revision**: Address the concern above.

### FINDING_13: code-quality: scripts/lib-vote-tally.sh:32-34
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] reviewer_for_block docstring still implies generic emphasis-tolerant parsing. Contributors may assume prose lines containing Reviewer are still parsed. Reword to state anchored canonical line forms only, consistent with lib-vote-tally.md.
- **Suggested revision**: Address the concern above.

### FINDING_14: code-quality: skills/review/scripts/tally-code-votes.sh:411-412
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Dead-slot comment only mentions NOT_SUBSTANTIVE narrative slots Reader may misunderstand when dynamic or other zero-row manifest entries get appended Update comment to include dynamic slots and OK fallback semantics
- **Suggested revision**: Address the concern above.

### FINDING_15: code-quality: skills/review/scripts/tally-code-votes.sh:411-413
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Dead-slot comment only mentions NOT_SUBSTANTIVE narrative slots. After the change, dynamic zero-finding manifest rows and OK-by-default dead rows are also produced from the same block, so the comment understates behavior and can mislead maintainers. Expand the comment to cover dynamic slots and STATUS=OK when collector_status is missing.
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: scripts/lib-vote-tally.sh:37-38
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] reviewer_for_block only accepts case-sensitive canonical bold labels with an immediately attached colon. Variants like '- **Reviewer** : Name' or lowercase '- **reviewer**:' yield unknown and mis-attribute score rows despite a present reviewer line. Allow optional whitespace before the colon and/or case-fold the Reviewer(s) token for the bold branch.
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: skills/review/scripts/tally-code-votes.sh:462-465
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Missing collector_status defaults dead-slot row to STATUS=OK Collector or env truncation omits STATUS for a manifest slot; scoreboard shows OK with zeros implying a successful zero-finding run Use explicit STATUS for missing KV or restrict OK default to cases that provably ran
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: scripts/test-lib-vote-tally.sh:117-126
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Embedded-colon false positive covered only via **Concern** line Still valid for the bug class; slightly narrow vs arbitrary prose lines Add an extra block where a non-field prose line contains Reviewer: mid-line if you want broader regression lock-in
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: skills/review/scripts/tally-code-votes.sh:462-463
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Dead-slot STATUS defaults to OK when collector_status lacks the manifest basename. A manifest slot with no collector row (or a basename/key mismatch) still renders STATUS=OK, which can hide missing or failed collector telemetry while implying a successful run. Use OK only when collector evidence exists; otherwise emit UNKNOWN or a dedicated NO_COLLECTOR_ROW status so the scoreboard cannot be mistaken for verified OK.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: skills/review/scripts/tally-code-votes.sh:462-465
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Dead-slot scoreboard defaults missing collector keys to STATUS=OK. When --collector-results-file is omitted (review-core only passes the flag if the file exists) or a collector KV group for one manifest basename is missing while others parsed, every such row shows STATUS=OK, same as a verified zero-finding run; previously UNKNOWN surfaced the ambiguity. Reserve OK for evidenced cases; use UNKNOWN when the collector file is absent/unreadable or when the map is partial and this basename has no explicit STATUS= record.
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: skills/review/scripts/tally-code-votes.sh:462-465
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Missing collector_status now renders STATUS=OK for dead manifest rows. Collector ingestion bugs that omit a manifest basename no longer surface as UNKNOWN in the scoreboard, which can hide wiring regressions unless other telemetry catches them. Keep documented semantics; add external collector completeness checks or a dedicated warning if UNKNOWN-style diagnostics are still required.
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: skills/review/scripts/tally-code-votes.sh:462-465
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Dead-slot STATUS defaults to OK when collector_status lacks the manifest basename Same scoreboard annotation for a genuinely missing collector record as for a successful zero-finding slot; harder to spot partial collector output or mis-merged env files If you need that signal, emit a distinct STATUS (e.g. MISSING), add a diagnostic line to FD3, or keep UNKNOWN only when collector file is empty or malformed
- **Suggested revision**: Address the concern above.

