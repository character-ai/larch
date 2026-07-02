## Decision 1: Compression depth
- **Question**: How aggressive should the density pass be on `code-reviewer.md` and `orchestrator-aggregator.md`?
- **Resolution**: Moderate density pass. Tighten wording throughout, cut filler and redundant asides, but keep every behavioral rule, checklist item, and calibration example intact in substance. (No user response within 60s; recommended default applied.)
- **Source**: user

## Decision 2: Reduction target
- **Question**: Should the plan commit to a specific numeric token-reduction target?
- **Resolution**: No fixed numeric target. Land whatever safe reduction the density pass yields, verified with `python3 python/cli.py skill-closure report`, and update the baseline. (No user response within 60s; recommended default applied.)
- **Source**: user

## Decision 3: Edit target for code-reviewer.md
- **Question**: Which file should actually be hand-edited to compress `agents/code-reviewer.md`'s prose?
- **Resolution**: `agents/code-reviewer.md` is auto-generated (header: "Derived from skills/shared/reviewer-templates.md. Do not edit."). The canonical source is the "## Reviewer: Code Reviewer" `GENERATED_BODY` section in `skills/shared/reviewer-templates.md`. Edit that section, then regenerate with `python3 python/cli.py generate code-reviewer-agent`.
- **Source**: codebase

## Decision 4: Side-effect regeneration
- **Question**: Does compressing that template section affect any other generated file?
- **Resolution**: Yes. `skills/shared/reviewer-templates-code-reviewer.md` (the conflict-resolution fragment) is generated from the same `## Variables` + `## Reviewer: Code Reviewer` sections via `python3 python/cli.py generate conflict-resolution-code-reviewer`. It must be regenerated in the same change, or `make agent-sync` (`generate check`) fails with drift.
- **Source**: codebase

## Decision 5: orchestrator-aggregator.md edit approach
- **Question**: Is `orchestrator-aggregator.md` generated or hand-maintained?
- **Resolution**: Hand-maintained (header: "HAND-MAINTAINED: internal orchestration agent, not a reviewer specialist"). Edit `agents/orchestrator-aggregator.md` directly; no generator/regeneration step applies.
- **Source**: codebase

## Decision 6: Scope boundary — other reviewer archetypes
- **Question**: Do the other three generated archetypes in `reviewer-templates.md` (Plan Fidelity, Code Robustness, Security+Structure+Tests) get compressed too?
- **Resolution**: No. The issue names only `code-reviewer.md` and `orchestrator-aggregator.md`. Only the "## Reviewer: Code Reviewer" section is touched; the other three archetype sections, which share near-identical boilerplate, stay untouched this round. This matches md-to-py-XI's per-round scoping.
- **Source**: codebase

## Decision 7: Format-contract literals that must stay byte-exact
- **Question**: What exact tokens must remain byte-identical to avoid breaking `python/larch/review/review_aggregate.py` validation and the JSONL/TSV sidecar contracts?
- **Resolution**: In `orchestrator-aggregator.md`: the `### FINDING_N:` / `### OOS_N:` heading grammar, the `- **Severity**: blocking|important|latent|nit` line and its merge-priority order, the `[OUT_OF_SCOPE]` tag rules, and the exact literal `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` attestation line. In the Code Reviewer template body: severity prefixes (`**Blocking**` / `**Important**` / `**Nit**` / `**Latent**`), focus-area tags, the JSONL sidecar field names and values, section headings `### In-Scope Findings` / `### Out-of-Scope Observations`, the `{REVIEW_TARGET}` / `{CONTEXT_BLOCK}` / `{OUTPUT_INSTRUCTION}` template placeholders, and numeric caps (5 Nits, 3 OOS, sentence caps).
- **Source**: codebase

7 decisions resolved.
