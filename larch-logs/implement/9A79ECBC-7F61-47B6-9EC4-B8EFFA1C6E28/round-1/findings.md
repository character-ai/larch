### FINDING_1: **Important** `correctness` `scripts/measure-references-heatmap.sh:29` — `normalize_path()` only strips the current checkout path or plugin-cache paths, so committed transcripts from other local checkouts are silently dropped. Concrete scenario: `larch-logs/implement/00A7A5AB-F063-45A4-AE92-6248CB151F9F/session-transcript.jsonl:122` records a `Read` of `<OPERATOR_REPO_PATH>/skills/implement/SKILL.md` with `cwd` `/Users/zhupanov/larch6`; when reviewed from `/Users/zhupanov/larch5`, line 41 rejects it as absolute, so `skills/implement/SKILL.md` is omitted from the heatmap. My probe found 418 markdown `Read` calls, with 209 dropped for this absolute-other-checkout reason. Suggested fix: pass each transcript object’s `cwd` into normalization and strip `cwd + "/"` for paths under that run’s repo before rejecting other absolute paths.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `scripts/measure-references-heatmap.sh:29` — `normalize_path()` only strips the current checkout path or plugin-cache paths, so committed transcripts from other local checkouts are silently dropped. Concrete scenario: `larch-logs/implement/00A7A5AB-F063-45A4-AE92-6248CB151F9F/session-transcript.jsonl:122` records a `Read` of `<OPERATOR_REPO_PATH>/skills/implement/SKILL.md` with `cwd` `/Users/zhupanov/larch6`; when reviewed from `/Users/zhupanov/larch5`, line 41 rejects it as absolute, so `skills/implement/SKILL.md` is omitted from the heatmap. My probe found 418 markdown `Read` calls, with 209 dropped for this absolute-other-checkout reason. Suggested fix: pass each transcript object’s `cwd` into normalization and strip `cwd + "/"` for paths under that run’s repo before rejecting other absolute paths.
- **Suggested revision**: Address the concern above.

### FINDING_2: **Important** `risk-integration` `scripts/measure-realized-cost.sh:112` — the realized-cost TSV schema adds `issues_observed` between `invocations` and `tokens_per_invocation`, but the requested contract is `skill,invocations,tokens_per_invocation,realized_tokens`. Concrete breakage: any downstream parser expecting column 3 to be `tokens_per_invocation` will instead read issue counts, and `realized_tokens` shifts from column 4 to column 5. Suggested fix: emit exactly the requested four columns, or put diagnostics in a separate file so the primary TSV contract stays stable.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `risk-integration` `scripts/measure-realized-cost.sh:112` — the realized-cost TSV schema adds `issues_observed` between `invocations` and `tokens_per_invocation`, but the requested contract is `skill,invocations,tokens_per_invocation,realized_tokens`. Concrete breakage: any downstream parser expecting column 3 to be `tokens_per_invocation` will instead read issue counts, and `realized_tokens` shifts from column 4 to column 5. Suggested fix: emit exactly the requested four columns, or put diagnostics in a separate file so the primary TSV contract stays stable.
- **Suggested revision**: Address the concern above.

### FINDING_3: architecture: scripts/measure-realized-cost.sh:441-476
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Run discovery uses larch-logs/*/* instead of implement-only path from implementation_plan If non-implement subtrees later ship manifest+timing with same shape, aggregates mix run families Restrict glob to larch-logs/implement/* (plus explicit similar dirs) if implement-only scope is required
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/measure-md-cost.sh:37-48 scripts/measure-ngram-duplication.sh:33-41
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate CLAUDE @ import parsing Two places to fix if import syntax rules change Extract shared helper
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/measure-ngram-duplication.sh:14-59
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Implementation is Python not shell/awk as phrased in feature_description Mismatch with issue wording only Update spec or doc to say Python
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/measure-realized-cost.sh:112-114
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Output TSV has extra issues_observed column vs feature_description four-column contract Downstream parsers expecting four fields mis-align columns Match spec columns or version and document schema
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: scripts/measure-references-heatmap.sh:89-104
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] JSONL parse instead of grep per feature_description text Spec said grep; implementation differs Update spec or sibling .md to match approach
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: feature_description §(2) vs scripts/measure-ngram-duplication.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Feature text says shell/awk; script is Python per implementation_plan None if implementation_plan is source of truth; confusion only for readers of feature_description alone Update feature text or add one line in sibling .md clarifying Python n-gram core
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/measure-realized-cost.sh:100-102
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Unresolved skill names are omitted entirely Timing lists a skill with no SKILL.md on disk: no row warning; totals miss mass Emit diagnostic rows or stderr for missing SKILL.md
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/measure-realized-cost.sh:500-503
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] TSV schema adds issues_observed fifth column vs plan and feature four-column contract Downstream parsers or docs expecting exactly skill,invocations,tokens_per_invocation,realized_tokens mis-align columns or fail strict imports Match plan (four columns) or formally extend the plan/feature contract to five columns
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: scripts/measure-realized-cost.sh:56-87
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Per-run set dedupes skills so invocations ignore repeated per_step rows Multi-step runs with the same skill many times still add only +1 invocation; realized_tokens can be far below step-based SKILL exposure if that was the intent Count per step (e.g. Counter over timing per_step) or document metric as once-per-run-per-skill
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/measure-md-cost.sh:14-252 scripts/measure-realized-cost.sh:14-115 scripts/measure-ngram-duplication.sh:14-359 scripts/measure-references-heatmap.sh:14-619
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No CI harness or golden output for measure scripts Embedded parsers can drift from log JSON/MD shapes; regressions only found on manual runs Add minimal offline harness and optional Makefile/CI wiring
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: scripts/measure-realized-cost.sh:106-114
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] TSV schema adds issues_observed vs four-column requirement in feature_description Downstream #2241 tooling or imports expecting exactly four columns mis-aligns columns or drops fields Align public contract with five columns or gate extra column behind a flag and default to four columns
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: scripts/measure-realized-cost.sh:52-87
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Scan uses larch-logs/*/* not only larch-logs/implement/* per feature_description Non-implement subtrees with timing/manifest artifacts inflate or skew invocation counts vs described scope Narrow glob to implement plus named peers or document broad scan explicitly
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/measure-realized-cost.sh:59-83
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Bare except pass swallows parse errors Corrupt or evolved timing JSON yields empty skill sets with no signal Add counters or optional verbose logging
- **Suggested revision**: Address the concern above.

