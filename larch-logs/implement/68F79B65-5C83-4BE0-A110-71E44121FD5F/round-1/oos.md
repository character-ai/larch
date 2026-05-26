### FINDING_20: [OUT_OF_SCOPE] security: scripts/design-log-publish.sh:337-378
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] render-cache lacks the symlink sweep added for plan-review. Symlinked intermediate dirs under render-cache may still hide files from enumeration without failing publish. Mirror plan-review find -type l sweep for render-cache.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_28: [OUT_OF_SCOPE] architecture: scripts/lib-voter-parse-rate.sh:87+
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Parse-rate does not require forensic axes Judges omit axes pass retry and produce all-uncertain TSV rows Extend check_voter_parse_rate when axis coverage is mandatory
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_29: [OUT_OF_SCOPE] code-quality: scripts/test-render-voter-prompt.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Render voter prompt regression only partially covers new contract Prompt drift on Output ONLY vote lines or finding-only delimiter prose may slip Add remaining plan-listed grep assertions
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_38: [OUT_OF_SCOPE] correctness: skills/design/scripts/tally-plan-review.sh:2064-2066
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Argv validation exits use code 2 not plan exit 1. Callers checking exact exit 1 would mis-handle errors. Align exit codes with plan or document exit 2 in tally-plan-review.md.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_39: [OUT_OF_SCOPE] architecture: scripts/test-render-voter-prompt.md:1442
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Harness doc shard reference may be stale relative to Makefile. Readers may look at wrong test-harnesses-N shard list. Keep test-render doc aligned with Makefile shard assignment.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_44: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-voter-slot-position-output.txt
- **Concern**: - **correctness** `skills/design/scripts/test-tally-plan-review.sh` — The implementation plan lists 13 new `--voter` / TSV cases for this harness; the branch diff does not extend `test-tally-plan-review.sh` (still only `--voter-files`). Regression for the new argv surface relies on `test-findings-classification.sh`, which (per above) does not fully exercise dispatch order.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_45: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-voter-slot-position-output.txt
- **Concern**: - **architecture** `skills/design/scripts/plan-review-loop.sh:87-99` — Zero-findings exits inline-print the 21-column header instead of calling `tally-plan-review.sh` with an empty ballot (plan’s preferred single source of truth). Low risk while the header string is duplicated in `emit_findings_classification_header`, but it is a second definition to drift.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_46: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-voter-slot-position-output.txt
- **Concern**: - **correctness** `docs/run-logs.md` — Layout tree lists `findings-classification.tsv` but the branch does not add the planned paragraph on 21-column schema, dispatch-order vs `vN_tool`, or empty-cell semantics (acceptance item still open).
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_50: [OUT_OF_SCOPE] Scout checklist items **parts[1] axis loop**, **`reset_fields` / last-line-wins**, and **`FINDING_1` vs `FINDING_10` prefix collision** behave as intended; no defect found (verified including `FINDING_10` non-match).
- **Reviewer**: dyn-awk-parser-correctness-output.txt
- **Concern**: - Scout checklist items **parts[1] axis loop**, **`reset_fields` / last-line-wins**, and **`FINDING_1` vs `FINDING_10` prefix collision** behave as intended; no defect found (verified including `FINDING_10` non-match).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_51: [OUT_OF_SCOPE] **Double space before `--`** (e.g. `UNCERTAIN=false  -- reason`) still truncates at the delimiter and keeps `PARSED_QUALITY=good`; not a regression.
- **Reviewer**: dyn-awk-parser-correctness-output.txt
- **Concern**: - **Double space before `--`** (e.g. `UNCERTAIN=false  -- reason`) still truncates at the delimiter and keeps `PARSED_QUALITY=good`; not a regression.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_52: [OUT_OF_SCOPE] `scripts/parse-judge-vote-and-rating.md:34` states the ` -- ` delimiter is the same one `vote_for_id` uses, but `vote_for_id` does not implement `--` scoping—documentation-only inaccuracy.
- **Reviewer**: dyn-awk-parser-correctness-output.txt
- **Concern**: - `scripts/parse-judge-vote-and-rating.md:34` states the ` -- ` delimiter is the same one `vote_for_id` uses, but `vote_for_id` does not implement `--` scoping—documentation-only inaccuracy.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_53: [OUT_OF_SCOPE] Harness case `FINDING_7` (line without `--`, prose `QUALITY=weak`) intentionally parses rationale tokens; that is contract-by-design, not an awk bug.
- **Reviewer**: dyn-awk-parser-correctness-output.txt
- **Concern**: - Harness case `FINDING_7` (line without `--`, prose `QUALITY=weak`) intentionally parses rationale tokens; that is contract-by-design, not an awk bug.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

