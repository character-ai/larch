### [rejected] FINDING_10

### FINDING_10: correctness: scripts/measure-md-cost.sh:95
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Python literal path\ttier splits as path + TAB + ier so header column is wrong. Next run writes second column name ier; parsers expecting tier break; committed 2026-05-18.tsv header does not match script output (artifact drift). Use explicit tabs around tier e.g. fh.write("path\t" + "tier\tbytes\ttokens\tlines\th2_count\n") or equivalent so tier is not glued to escape.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 NEUTRAL=0

### [rejected] FINDING_12

### FINDING_12: correctness: scripts/measure-ngram-duplication.sh:52-61
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] N-grams are word-token 6-grams, not character 6-grams. Character-level duplication signals can rank differently or be absent from the top-50 list versus a character shingle definition. Align spec with word n-grams or implement character n-grams if required.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 NEUTRAL=0

### [rejected] FINDING_13

### FINDING_13: correctness: scripts/measure-ngram-duplication.sh:64-69
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Ranking score uses occurrences times ngram word count not character shingle length. Stakeholders interpreting shingle_length as characters get a different top-50 order. Define score explicitly in docs or code and lock with a small golden test.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_17

### FINDING_17: correctness: scripts/measure-realized-cost.sh:52-87
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] per_run set dedupes multiple per_step rows for same skill. Multi-step implement runs count as one invocation; realized_tokens is a lower bound vs per-step loads. Document invocations=runs_with_skill or count len(per_step rows) per skill if per-step cost is intended.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_18

### FINDING_18: correctness: scripts/measure-realized-cost.sh:56-86
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Invocations increment once per skill per run because skills_in_run is a set. If invocations are meant to follow timing-report rows (multiple per_step entries per skill), realized_tokens is far too low versus repeated steps in a single run. Define whether an invocation is per run or per timing step; if per step, count rows (or another explicit rule) instead of set membership.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_19

### FINDING_19: correctness: scripts/measure-references-heatmap.sh:68-76
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Read tool name matched case-sensitively only. Transcripts using different casing for the Read tool under-count. Compare normalized tool names or allow a case-insensitive match.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 NEUTRAL=0

### [rejected] FINDING_22

### FINDING_22: risk-integration: scripts/measure-md-cost.sh:1-101 scripts/measure-ngram-duplication.sh:1-80 scripts/measure-realized-cost.sh:1-118 scripts/measure-references-heatmap.sh:1-94
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No CI job executes the measurement scripts; only static linters may touch the bash surface. Embedded Python can regress (JSONL shape timing reports session transcripts) while PR stays green. Add a minimal smoke test or Makefile target invoked by the existing test-harness workflow.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_25

### FINDING_25: risk-integration: scripts/measure-realized-cost.sh:52
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Scans all larch-logs/*/* run-shaped dirs, broader than implement/* in the plan text. Future non-implement subtrees with manifest/timing files could be included unintentionally. Restrict glob to implement/ and explicitly listed siblings.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_26

### FINDING_26: risk-integration: scripts/measure-realized-cost.sh:52-74
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Scanner globs all larch-logs/*/* run directories not only larch-logs/implement/*/. Future alternate log trees could skew aggregates versus the issue #2241 wording. Narrow the glob or document intentional inclusion of all run families.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_28

### FINDING_28: risk-integration: scripts/measure-realized-cost.sh:68-74
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] timing-report.md skill extraction is regex-coupled to a specific pipe-table shape. Table format drift yields empty skills_in_run for MD-only runs, skewing aggregates. Keep JSON-first and document or validate MD format.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_5

### FINDING_5: architecture: implementation_plan measure-realized-cost bullet vs scripts/measure-realized-cost.sh:104-105
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan text says SKILL.md byte counts; code and docs use tiktoken token counts. Readers following only the plan narrative may expect byte-based columns or validations. Align the implementation plan wording with token-based measurement.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_8

### FINDING_8: code-quality: scripts/measure-ngram-duplication.sh:29-30
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] git ls-files stderr not redirected unlike sibling measure-md-cost.sh. Noisy or confusing errors when git metadata is missing in edge environments. Match stderr handling to measure-md-cost.sh if desired.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_9

### FINDING_9: correctness: feature_description (2) vs scripts/measure-ngram-duplication.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Ticket text still requires a shell/awk helper; implementation uses embedded Python. Strict ticket acceptance that insists on awk could reject the PR despite working Python. Update the ticket or document that the implementation plan superseded the shell/awk requirement.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

