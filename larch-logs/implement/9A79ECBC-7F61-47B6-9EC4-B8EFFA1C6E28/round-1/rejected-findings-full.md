### [rejected] FINDING_11

### FINDING_11: correctness: scripts/measure-realized-cost.sh:56-87
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Per-run set dedupes skills so invocations ignore repeated per_step rows Multi-step runs with the same skill many times still add only +1 invocation; realized_tokens can be far below step-based SKILL exposure if that was the intent Count per step (e.g. Counter over timing per_step) or document metric as once-per-run-per-skill
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 NEUTRAL=1

### [rejected] FINDING_12

### FINDING_12: risk-integration: scripts/measure-md-cost.sh:14-252 scripts/measure-realized-cost.sh:14-115 scripts/measure-ngram-duplication.sh:14-359 scripts/measure-references-heatmap.sh:14-619
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No CI harness or golden output for measure scripts Embedded parsers can drift from log JSON/MD shapes; regressions only found on manual runs Add minimal offline harness and optional Makefile/CI wiring
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 NEUTRAL=1

### [rejected] FINDING_14

### FINDING_14: risk-integration: scripts/measure-realized-cost.sh:52-87
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Scan uses larch-logs/*/* not only larch-logs/implement/* per feature_description Non-implement subtrees with timing/manifest artifacts inflate or skew invocation counts vs described scope Narrow glob to implement plus named peers or document broad scan explicitly
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 NEUTRAL=1

### [rejected] FINDING_3

### FINDING_3: architecture: scripts/measure-realized-cost.sh:441-476
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Run discovery uses larch-logs/*/* instead of implement-only path from implementation_plan If non-implement subtrees later ship manifest+timing with same shape, aggregates mix run families Restrict glob to larch-logs/implement/* (plus explicit similar dirs) if implement-only scope is required
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 NEUTRAL=1

### [rejected] FINDING_4

### FINDING_4: code-quality: scripts/measure-md-cost.sh:37-48 scripts/measure-ngram-duplication.sh:33-41
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate CLAUDE @ import parsing Two places to fix if import syntax rules change Extract shared helper
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 NEUTRAL=1

### [rejected] FINDING_5

### FINDING_5: code-quality: scripts/measure-ngram-duplication.sh:14-59
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Implementation is Python not shell/awk as phrased in feature_description Mismatch with issue wording only Update spec or doc to say Python
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 NEUTRAL=1

### [rejected] FINDING_7

### FINDING_7: code-quality: scripts/measure-references-heatmap.sh:89-104
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] JSONL parse instead of grep per feature_description text Spec said grep; implementation differs Update spec or sibling .md to match approach
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 NEUTRAL=1

### [rejected] FINDING_8

### FINDING_8: correctness: feature_description §(2) vs scripts/measure-ngram-duplication.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Feature text says shell/awk; script is Python per implementation_plan None if implementation_plan is source of truth; confusion only for readers of feature_description alone Update feature text or add one line in sibling .md clarifying Python n-gram core
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 NEUTRAL=1

