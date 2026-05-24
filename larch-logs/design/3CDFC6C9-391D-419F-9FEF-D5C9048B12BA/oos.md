### OOS_1: Update topology.tsv projection counts
- **Description**: After this PR lands, `skills/shared/topology.tsv` may need a projection row for the new `review-findings-classification` batch slug per the AGENTS.md topology-when-batches-change convention. Not required for runtime correctness; avoids doc drift in topology counts.
- **Reviewer**: Cursor-Requirements


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_2: Document TSV redaction posture in SECURITY.md
- **Description**: If `findings-classification.tsv` carries raw judge tokens (even after Finding 8's sanitization), confirm whether it should pass the same redaction boundary as `compose-review-findings.sh` for JSONL. The committed TSV may contain unexpected reviewer-supplied strings; align with `SECURITY.md:62`.
- **Reviewer**: Cursor-Innovation, Cursor-dyn-tsv


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_3: Forward FINDINGS_CLASSIFICATION_TSV_FILE through review-and-fix.sh for parity
- **Description**: `skills/review-and-fix/scripts/review-and-fix.sh:1348-1355` flushes scout KVs after `review-core` round. If future nested flows want classification path parity, the same forwarding should apply. Not required if all publish paths already copy from `$REVIEW_TMPDIR` under the implement round dir.
- **Reviewer**: Cursor-Arch, Codex-Edge, Codex-Pragmatic


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_4: Add scout-archetype-yield.tsv to round_artifact_included allowlist (pre-existing gap)
- **Description**: `scripts/larch-log.sh round_artifact_included` (~lines 67-101) doesn't list `scout-archetype-yield.tsv` in its allowlist; the `*.tsv` exclusion suppresses it. This predates the L6 PR but is the same mechanism L6 relies on for `findings-classification.tsv`. Worth tracking as a separate issue if round dirs should also carry yield bytes.
- **Reviewer**: Codex-Pragmatic


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_5: docs/run-logs-required-files.tsv update if classification becomes completeness-gated
- **Description**: If org policy later treats `findings-classification.tsv` as part of the run-completeness manifest, `docs/run-logs-required-files.tsv` would need a row. Not implied by this plan; track separately if/when the audit consumer requires it.
- **Reviewer**: Cursor-dyn-artifact


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### OOS_6: review-core.md emitted-KV bullet list update
- **Description**: `skills/review/scripts/review-core.md:76-88` lists scout fields + `YIELD_TSV_FILE` as wrapper-consumed KVs. After item 3 of the plan lands, this list should include `FINDINGS_CLASSIFICATION_TSV_FILE`. Conceptually covered by plan item 3 (which says "+ sibling .md"), so this OOS may already be in scope; track as cleanup if missed.
- **Reviewer**: Cursor-Innovation, Cursor-dyn-artifact

Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

