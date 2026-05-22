# Review Round 3

- Mode: `diff`
- Accepted findings: 6
- Rejected findings: 0
- Exonerated findings: 19
- Neutral findings: 0

## Accepted Findings

### FINDING_23: correctness: skills/review/scripts/aggregate-findings.sh:316-334
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Pseudo-heading suppression misses ###FINDING_… without space after ### so synthesis can still rescue zero-block merges. Model returns a line like ###FINDING_1: ... (no space after ###): output_blocks is empty, has_nonconforming_finding_heading_markers is false, attestation is synthesized, REASON=ok, masking the same class of malformed pseudo-headings the doc says should fail closed. Align nonconforming detection with block-split heading rules (e.g. treat ^###\s*FINDING_ lines that fail line_opens_valid_finding_block as suppressing synthesis) and add a stub regression.
- **Suggested revision**: Address the concern above.


### FINDING_27: architecture: SECURITY.md:57-60; skills/review/scripts/aggregate-findings.sh:668-691
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Supplied plan promised aggregator-output.txt stays byte-identical to raw model output; implementation rewrites staged vendor output before validation and documents post-repair bytes. Operators or audits comparing dispatch-first capture to committed aggregator-output.txt on the synthesis path infer wrong provenance or treat SECURITY/plan text as authoritative and disagree with runtime. Treat plan sentence as superseded; align all consumer docs; add a separate first-write sidecar if forensic byte identity is required.
- **Suggested revision**: Address the concern above.


### FINDING_32: **correctness** `skills/review/scripts/aggregate-findings.sh:322-334` — `has_nonconforming_finding_heading_markers` only treats lines as pseudo-headings when `re.match(r"^###\s+FINDING_", ls)` matches, which **requires** at least one whitespace between `###` and `FINDING_`, so a line like `###FINDING_1: …` (no space) is **not** flagged, while `output_blocks` / the split anchor still see **zero** structured blocks; `_attempt_attestation_repair` can then append `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` and `main()` accepts the empty-merge path, treating narrative with a tight `###FINDING_…` typo as a legitimate empty merge. **Suggested fix:** align the pseudo-heading detector with the strict heading / split contract—for example match `^###\s*FINDING_` (or explicitly detect `###` immediately followed by `FINDING_`) whenever `line_opens_valid_finding_block` is false, so this class of malformed heading fails closed like other nonconforming markers.
- **Reviewer**: dyn-attestation-integrity-output.txt
- **Concern**: - **correctness** `skills/review/scripts/aggregate-findings.sh:322-334` — `has_nonconforming_finding_heading_markers` only treats lines as pseudo-headings when `re.match(r"^###\s+FINDING_", ls)` matches, which **requires** at least one whitespace between `###` and `FINDING_`, so a line like `###FINDING_1: …` (no space) is **not** flagged, while `output_blocks` / the split anchor still see **zero** structured blocks; `_attempt_attestation_repair` can then append `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` and `main()` accepts the empty-merge path, treating narrative with a tight `###FINDING_…` typo as a legitimate empty merge. **Suggested fix:** align the pseudo-heading detector with the strict heading / split contract—for example match `^###\s*FINDING_` (or explicitly detect `###` immediately followed by `FINDING_`) whenever `line_opens_valid_finding_block` is false, so this class of malformed heading fails closed like other nonconforming markers.
- **Suggested revision**: Address the concern above.


### FINDING_34: **risk-integration** `skills/review/scripts/aggregate-findings.sh:668-698` — The repair step always materializes repair stdout into a temp file and then runs `mv -f "$cand_repaired_tmp" "$cand"` **before** `python3 "$validate_py" "$FINDINGS_FILE" "$cand"` (validation) and **before** the strip heredoc that reads `"$cand"`. So the path the dispatcher wrote (typically `aggregator-output.txt` via `out_file` / `ALL_OUTPUT_FILES`) is **no longer guaranteed to match the vendor’s raw bytes** after a failed validation: `findings.md` stays untouched on the `validation-failed` exit at 693–698, but `cand` has already been replaced, which breaks the old symmetry where the on-disk merge artifact stayed vendor-pure until a successful commit path and also conflicts with wording in the attached plan that `aggregator-output.txt` still reflects “raw model output.” **Suggested fix:** keep the dispatch output immutable until validation (and ideally strip) succeed—for example validate and strip against `cand_repaired_tmp` (or a renamed stable temp), then on the success-only path atomically replace `cand` and `FINDINGS_FILE`, or write vendor bytes to a dedicated `aggregator-output-raw.txt` before repair and only update `aggregator-output.txt` after success, and align `aggregate-findings.md` with whichever artifact contract you choose.
- **Reviewer**: dyn-strip-pass-ordering-output.txt
- **Concern**: - **risk-integration** `skills/review/scripts/aggregate-findings.sh:668-698` — The repair step always materializes repair stdout into a temp file and then runs `mv -f "$cand_repaired_tmp" "$cand"` **before** `python3 "$validate_py" "$FINDINGS_FILE" "$cand"` (validation) and **before** the strip heredoc that reads `"$cand"`. So the path the dispatcher wrote (typically `aggregator-output.txt` via `out_file` / `ALL_OUTPUT_FILES`) is **no longer guaranteed to match the vendor’s raw bytes** after a failed validation: `findings.md` stays untouched on the `validation-failed` exit at 693–698, but `cand` has already been replaced, which breaks the old symmetry where the on-disk merge artifact stayed vendor-pure until a successful commit path and also conflicts with wording in the attached plan that `aggregator-output.txt` still reflects “raw model output.” **Suggested fix:** keep the dispatch output immutable until validation (and ideally strip) succeed—for example validate and strip against `cand_repaired_tmp` (or a renamed stable temp), then on the success-only path atomically replace `cand` and `FINDINGS_FILE`, or write vendor bytes to a dedicated `aggregator-output-raw.txt` before repair and only update `aggregator-output.txt` after success, and align `aggregate-findings.md` with whichever artifact contract you choose.
- **Suggested revision**: Address the concern above.


### FINDING_5: correctness: skills/review/scripts/aggregate-findings.sh:322-334
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Broad pseudo-heading detector (^###\s+FINDING_) suppresses synthesis for prose lines like '### FINDING_ids are stable' without digits after FINDING_ Empty-merge vendor text has zero real FINDING blocks and no attestation but mentions FINDING_ids on its own line; synthesis skipped; validation fails; findings.md unchanged (#2563 symptom persists) Narrow nonconforming detection (e.g. require FINDING_[0-9]+ and stricter broken-heading shape) and add regression test for FINDING_ids prose
- **Suggested revision**: Address the concern above.


### FINDING_8: risk-integration: SECURITY.md vs feature_description
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Awardness: feature text still claims raw first-write for aggregator-output.txt while SECURITY.md says post-repair staged bytes Operators relying on old acceptance wording misjudge forensic provenance Update feature/acceptance text to match SECURITY.md
- **Suggested revision**: Address the concern above.


