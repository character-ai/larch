### FINDING_1: code-quality: skills/review/scripts/aggregate-findings.sh:682-690
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Grep-filtered repair telemetry drops the sidecar when stderr is non-empty but lacks recognized prefixes, hiding unexpected Python stderr during --repair-attestation. A DeprecationWarning or other one-line stderr noise during repair yields an empty aggregator-repair.stderr even though the temp captured output, complicating postmortems. If repair_err_tmp is non-empty and grep finds no matching lines, retain or summarize the remainder under a fixed machine-prefixed diagnostic path or line.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: agents/orchestrator-aggregator.md:52
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Model-facing prompt uses Python strip() jargon alongside mechanical whitespace rules. Minor cognitive mismatch for non-Python models or copy-paste confusion with implementation terms. Rewrite in plain language about trimming leading and trailing whitespace on the line.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/review/scripts/aggregate-findings.md:27-30
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] New contract bullets are very long single entries. Future edits to one invariant risk accidental conflation or merge conflicts. Break into shorter bullets or a dedicated recovery/telemetry subsection.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] architecture: skills/review/scripts/aggregate-findings.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Validator heredoc remains a large multi-responsibility surface. Pre-existing structure amplified only by continuation of the same pattern. Defer any module split unless the team standards require it.
- **Suggested revision**: Address the concern above.

### FINDING_5: correctness: skills/review/scripts/aggregate-findings.sh:322-334
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Broad pseudo-heading detector (^###\s+FINDING_) suppresses synthesis for prose lines like '### FINDING_ids are stable' without digits after FINDING_ Empty-merge vendor text has zero real FINDING blocks and no attestation but mentions FINDING_ids on its own line; synthesis skipped; validation fails; findings.md unchanged (#2563 symptom persists) Narrow nonconforming detection (e.g. require FINDING_[0-9]+ and stricter broken-heading shape) and add regression test for FINDING_ids prose
- **Suggested revision**: Address the concern above.

### FINDING_6: correctness: skills/review/scripts/aggregate-findings.sh:322-334
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Digit-gated heading drift cannot distinguish harness stub '### FINDING_1 not-a-...' from plausible narrative '### FINDING_1 in the input...' Same as #2563 failure when model cites prior finding ids on a standalone line without ':' heading form Refine heuristic or add disambiguation tests; document allowed narrative patterns for empty-merge
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: skills/review/scripts/test-aggregate-findings.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] empty_merge_existing_token_passthrough does not assert explicit false telemetry or absence of repair file per plan optional clause Minor gap vs plan; low runtime risk Strengthen assertions if you want strict telemetry contract
- **Suggested revision**: Address the concern above.

### FINDING_8: risk-integration: SECURITY.md vs feature_description
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Awardness: feature text still claims raw first-write for aggregator-output.txt while SECURITY.md says post-repair staged bytes Operators relying on old acceptance wording misjudge forensic provenance Update feature/acceptance text to match SECURITY.md
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] correctness: skills/review/scripts/aggregate-findings.sh:92-96
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] count_finding_blocks grep pattern may not match Python block parser edge cases Pre-existing INPUT_COUNT vs validator mismatch risk on odd ballots None required for this PR scope
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: skills/review/scripts/aggregate-findings.sh:548-673
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] repair_attestation_main always returns 0 unless Python crashes so the new non-zero repair branch and append_warning path are never exercised by test-harnesses A future refactor could break error handling or argv wiring with no failing CI signal Add a controlled test-only failure or subprocess mock and assert REASON / execution-issues warning for repair non-zero
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: skills/review/scripts/aggregate-findings.sh:555-558
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] synthesis breadcrumb duplicates unique_input_reviewers and input_slots with the same integer Operators or downstream parsers may misread telemetry as two independent counters Emit one field or compute distinct reviewer cardinality
- **Suggested revision**: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] code-quality: <TMPDIR>/round-3/diff.txt
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] empty precomputed diff file caused fallback to git diff Reviewer could not use the supplied artifact as intended Use populated cache or document empty-cache handling
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: skills/review/scripts/aggregate-findings.sh:548-673
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] repair_attestation_main always returns 0 unless Python crashes so the new non-zero repair branch and append_warning path are never exercised by test-harnesses A future refactor could break error handling or argv wiring with no failing CI signal Add a controlled test-only failure or subprocess mock and assert REASON / execution-issues warning for repair non-zero
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: skills/review/scripts/aggregate-findings.sh:555-558
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] synthesis breadcrumb duplicates unique_input_reviewers and input_slots with the same integer Operators or downstream parsers may misread telemetry as two independent counters Emit one field or compute distinct reviewer cardinality
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: skills/review/scripts/aggregate-findings.sh:682-686
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] stderr filter drops aggregator-repair.stderr when repair stderr has no allowed-prefix lines If stderr ever mixes allowed telemetry with other lines in a way grep rejects entirely breadcrumb file is omitted while merge may still succeed Decide contract add test or document drop behavior
- **Suggested revision**: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] code-quality: <TMPDIR>/round-3/diff.txt
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] empty precomputed diff file caused fallback to git diff Reviewer could not use the supplied artifact as intended Use populated cache or document empty-cache handling
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: skills/review/scripts/aggregate-findings.sh:548-673
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] repair_attestation_main always returns 0 on success so the new non-zero repair bash branch is untested A refactor could break repair error handling with no CI failure Add env-guarded repair failure in harness and assert REASON and execution-issues
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: skills/review/scripts/aggregate-findings.sh:555-558
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] telemetry duplicates unique_input_reviewers and input_slots with the same integer Downstream log readers may treat them as independent signals Collapse fields or compute distinct metrics
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: skills/review/scripts/aggregate-findings.sh:682-686
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] grep filter drops aggregator-repair.stderr when stderr has no allowed-prefix lines Unprefixed Python stderr could hide telemetry file while merge still succeeds Document behavior or add a micro-test for the contract
- **Suggested revision**: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] code-quality: <TMPDIR>/round-3/diff.txt
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] precomputed diff file was empty Automated review could not use the provided artifact Regenerate populated session diff
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: skills/review/scripts/aggregate-findings.sh:519-691
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Deterministic empty-merge attestation synthesis lets narrative-only vendor output without the magic token pass validation and replace findings.md, instead of failing closed and preserving the ballot. A compromised or mis-prompted aggregator returns zero valid merged FINDING blocks and no attestation line; the script appends the token, validation succeeds, and voting proceeds on the cleared ballot while only aggregator-repair.stderr records synthesis. Encode policy in outer orchestration or audits (e.g., treat ATTESTATION_SYNTHESIZED=true as a gating signal, require human ack, or persist the flag in run logs you already scan).
- **Suggested revision**: Address the concern above.

### FINDING_22: code-quality: skills/review/scripts/aggregate-findings.sh:563-575
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Redundant impure-attestation scan in validate main() after lines were already dropped. Maintainers may think two different impurity semantics exist when only one path is live. Remove the redundant loop or document a single canonical impurity path.
- **Suggested revision**: Address the concern above.

### FINDING_23: correctness: skills/review/scripts/aggregate-findings.sh:316-334
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Pseudo-heading suppression misses ###FINDING_… without space after ### so synthesis can still rescue zero-block merges. Model returns a line like ###FINDING_1: ... (no space after ###): output_blocks is empty, has_nonconforming_finding_heading_markers is false, attestation is synthesized, REASON=ok, masking the same class of malformed pseudo-headings the doc says should fail closed. Align nonconforming detection with block-split heading rules (e.g. treat ^###\s*FINDING_ lines that fail line_opens_valid_finding_block as suppressing synthesis) and add a stub regression.
- **Suggested revision**: Address the concern above.

### FINDING_24: risk-integration: skills/review/scripts/aggregate-findings.sh:682-686
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Filtered repair stderr drops any non-breadcrumb Python diagnostics. If Python prints warnings or mixed stderr during --repair-attestation, only ATTESTATION_/AGGREGATOR_ lines are persisted; other lines are discarded when the temp file is removed, reducing debuggability versus aggregator-validate.stderr. Persist unmatched repair stderr to a sibling artifact or log file while keeping the filtered breadcrumb file.
- **Suggested revision**: Address the concern above.

### FINDING_25: code-quality: skills/review/scripts/aggregate-findings.sh:567-575
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Redundant impure-attestation scan in main() after drop_impure_empty_merge_attestation_lines. After drop removes all impure lines, the following for-loop should never trip; maintenance readers may assume a second normalization path. Remove the redundant loop or consolidate into one explicit normalization step.
- **Suggested revision**: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] architecture: skills/review/scripts/aggregate-findings.sh:519-544
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Synthesis does not prove intent against a hostile merge; token is still only a mechanical guardrail. Pre-existing security posture; recovery preserves the same string-or-fail contract as manual attestation. No code change required beyond policy/monitoring; document if operators need stronger guarantees.
- **Suggested revision**: Address the concern above.

### FINDING_27: architecture: SECURITY.md:57-60; skills/review/scripts/aggregate-findings.sh:668-691
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Supplied plan promised aggregator-output.txt stays byte-identical to raw model output; implementation rewrites staged vendor output before validation and documents post-repair bytes. Operators or audits comparing dispatch-first capture to committed aggregator-output.txt on the synthesis path infer wrong provenance or treat SECURITY/plan text as authoritative and disagree with runtime. Treat plan sentence as superseded; align all consumer docs; add a separate first-write sidecar if forensic byte identity is required.
- **Suggested revision**: Address the concern above.

### FINDING_28: risk-integration: skills/review/scripts/aggregate-findings.sh:555-558; skills/review/scripts/test-aggregate-findings.sh:456
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Breadcrumb telemetry is a superset of the plan’s single-line ATTESTATION_SYNTHESIZED=true input_slots=<N> contract. Monitoring or greps keyed only to the shorter plan line miss synthesis events. Declare the extended line canonical or split optional metrics onto additional filtered lines.
- **Suggested revision**: Address the concern above.

### FINDING_29: code-quality: skills/review/scripts/test-aggregate-findings.sh:437-456
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan-named case empty_merge_synthesis_succeeds is not reflected in the test section title. Manual plan-to-test audits rely on grep for the plan case id. Rename the echoed test section (or add a comment) to the plan’s case identifier.
- **Suggested revision**: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] risk-integration: review request: ~/.cache/larch/.../diff.txt; git merge-base HEAD main
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Precomputed diff empty; local main equals HEAD so merge-base..HEAD log empty; review used origin/main..HEAD. Reviewer confusion about which baseline was used. Regenerate sidecar diff or compare against origin/main when local main is fast-forwarded.
- **Suggested revision**: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] code-quality: acceptance criterion 4 (/relevant-checks)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Static review cannot prove lint/CI passed for this branch. False confidence if merge assumes green without CI. Run /relevant-checks or CI before merge; not inferable from diff.
- **Suggested revision**: Address the concern above.

### FINDING_32: **correctness** `skills/review/scripts/aggregate-findings.sh:322-334` — `has_nonconforming_finding_heading_markers` only treats lines as pseudo-headings when `re.match(r"^###\s+FINDING_", ls)` matches, which **requires** at least one whitespace between `###` and `FINDING_`, so a line like `###FINDING_1: …` (no space) is **not** flagged, while `output_blocks` / the split anchor still see **zero** structured blocks; `_attempt_attestation_repair` can then append `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` and `main()` accepts the empty-merge path, treating narrative with a tight `###FINDING_…` typo as a legitimate empty merge. **Suggested fix:** align the pseudo-heading detector with the strict heading / split contract—for example match `^###\s*FINDING_` (or explicitly detect `###` immediately followed by `FINDING_`) whenever `line_opens_valid_finding_block` is false, so this class of malformed heading fails closed like other nonconforming markers.
- **Reviewer**: dyn-attestation-integrity-output.txt
- **Concern**: - **correctness** `skills/review/scripts/aggregate-findings.sh:322-334` — `has_nonconforming_finding_heading_markers` only treats lines as pseudo-headings when `re.match(r"^###\s+FINDING_", ls)` matches, which **requires** at least one whitespace between `###` and `FINDING_`, so a line like `###FINDING_1: …` (no space) is **not** flagged, while `output_blocks` / the split anchor still see **zero** structured blocks; `_attempt_attestation_repair` can then append `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` and `main()` accepts the empty-merge path, treating narrative with a tight `###FINDING_…` typo as a legitimate empty merge. **Suggested fix:** align the pseudo-heading detector with the strict heading / split contract—for example match `^###\s*FINDING_` (or explicitly detect `###` immediately followed by `FINDING_`) whenever `line_opens_valid_finding_block` is false, so this class of malformed heading fails closed like other nonconforming markers.
- **Suggested revision**: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] `HEAD` and `main` both resolve to `12233fe3eb23911ad18b29a6b4f00cd5ee5fb516`, `git log $(git merge-base HEAD main)..HEAD --oneline` was empty, and `<TMPDIR>/round-3/diff.txt` was empty, so there was no branch-specific diff to attribute changes against; the finding above comes from static review of the current `aggregate-findings.sh` repair/validation interaction.
- **Reviewer**: dyn-attestation-integrity-output.txt
- **Concern**: - `HEAD` and `main` both resolve to `12233fe3eb23911ad18b29a6b4f00cd5ee5fb516`, `git log $(git merge-base HEAD main)..HEAD --oneline` was empty, and `<TMPDIR>/round-3/diff.txt` was empty, so there was no branch-specific diff to attribute changes against; the finding above comes from static review of the current `aggregate-findings.sh` repair/validation interaction.
- **Suggested revision**: Address the concern above.

### FINDING_34: **risk-integration** `skills/review/scripts/aggregate-findings.sh:668-698` — The repair step always materializes repair stdout into a temp file and then runs `mv -f "$cand_repaired_tmp" "$cand"` **before** `python3 "$validate_py" "$FINDINGS_FILE" "$cand"` (validation) and **before** the strip heredoc that reads `"$cand"`. So the path the dispatcher wrote (typically `aggregator-output.txt` via `out_file` / `ALL_OUTPUT_FILES`) is **no longer guaranteed to match the vendor’s raw bytes** after a failed validation: `findings.md` stays untouched on the `validation-failed` exit at 693–698, but `cand` has already been replaced, which breaks the old symmetry where the on-disk merge artifact stayed vendor-pure until a successful commit path and also conflicts with wording in the attached plan that `aggregator-output.txt` still reflects “raw model output.” **Suggested fix:** keep the dispatch output immutable until validation (and ideally strip) succeed—for example validate and strip against `cand_repaired_tmp` (or a renamed stable temp), then on the success-only path atomically replace `cand` and `FINDINGS_FILE`, or write vendor bytes to a dedicated `aggregator-output-raw.txt` before repair and only update `aggregator-output.txt` after success, and align `aggregate-findings.md` with whichever artifact contract you choose.
- **Reviewer**: dyn-strip-pass-ordering-output.txt
- **Concern**: - **risk-integration** `skills/review/scripts/aggregate-findings.sh:668-698` — The repair step always materializes repair stdout into a temp file and then runs `mv -f "$cand_repaired_tmp" "$cand"` **before** `python3 "$validate_py" "$FINDINGS_FILE" "$cand"` (validation) and **before** the strip heredoc that reads `"$cand"`. So the path the dispatcher wrote (typically `aggregator-output.txt` via `out_file` / `ALL_OUTPUT_FILES`) is **no longer guaranteed to match the vendor’s raw bytes** after a failed validation: `findings.md` stays untouched on the `validation-failed` exit at 693–698, but `cand` has already been replaced, which breaks the old symmetry where the on-disk merge artifact stayed vendor-pure until a successful commit path and also conflicts with wording in the attached plan that `aggregator-output.txt` still reflects “raw model output.” **Suggested fix:** keep the dispatch output immutable until validation (and ideally strip) succeed—for example validate and strip against `cand_repaired_tmp` (or a renamed stable temp), then on the success-only path atomically replace `cand` and `FINDINGS_FILE`, or write vendor bytes to a dedicated `aggregator-output-raw.txt` before repair and only update `aggregator-output.txt` after success, and align `aggregate-findings.md` with whichever artifact contract you choose.
- **Suggested revision**: Address the concern above.

### FINDING_35: [OUT_OF_SCOPE] The precomputed diff at `<TMPDIR>/round-3/diff.txt` was empty, so this review used the current tree contents of `aggregate-findings.sh` only.
- **Reviewer**: dyn-strip-pass-ordering-output.txt
- **Concern**: - The precomputed diff at `<TMPDIR>/round-3/diff.txt` was empty, so this review used the current tree contents of `aggregate-findings.sh` only.
- **Suggested revision**: Address the concern above.

### FINDING_36: [OUT_OF_SCOPE] `git log $(git merge-base HEAD main)..HEAD --oneline` produced no lines in this environment (no commits listed in that range relative to `main`).
- **Reviewer**: dyn-strip-pass-ordering-output.txt
- **Concern**: - `git log $(git merge-base HEAD main)..HEAD --oneline` produced no lines in this environment (no commits listed in that range relative to `main`).
- **Suggested revision**: Address the concern above.

### FINDING_37: [OUT_OF_SCOPE] Within the current script, the **happy-path** ordering for a successful round is repair output applied to `cand`, then validation on that same path, then strip from `cand` into `merged_tmp` with no intermediate branch that skips strip after a passing validate (707–724 follows 693–699 unconditionally on success).
- **Reviewer**: dyn-strip-pass-ordering-output.txt
- **Concern**: - Within the current script, the **happy-path** ordering for a successful round is repair output applied to `cand`, then validation on that same path, then strip from `cand` into `merged_tmp` with no intermediate branch that skips strip after a passing validate (707–724 follows 693–699 unconditionally on success).
- **Suggested revision**: Address the concern above.

