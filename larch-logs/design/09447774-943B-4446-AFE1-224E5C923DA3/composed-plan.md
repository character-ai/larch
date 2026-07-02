## Plan

## Approach

Make a moderate prose-density pass only.

- Treat `approach-synthesis.txt` as `NO_SKETCHES`: draft and implement from direct repo inspection.
- Keep the approved outline scope: only the Code Reviewer archetype, its generated artifacts, `agents/orchestrator-aggregator.md`, and the prompt-closure baseline.
- Do not compress the other reviewer archetypes in `skills/shared/reviewer-templates.md`.
- Do not change behavior, scoring incentives, severity definitions, output schemas, aggregation rules, or reviewer slot rules.
- Preserve exact contract literals:
  - `{REVIEW_TARGET}`, `{CONTEXT_BLOCK}`, `{OUTPUT_INSTRUCTION}`
  - `### In-Scope Findings`
  - `### Out-of-Scope Observations`
  - `**Blocking**`, `**Important**`, `**Nit**`, `**Latent**`
  - focus-area values and JSONL field names / enum values
  - `### FINDING_N:`, `### OOS_N:`
  - `- **Severity**: blocking|important|latent|nit`
  - merge priority order `blocking > important > latent > nit`
  - `[OUT_OF_SCOPE]`
  - `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED`
  - all numeric caps: 5 Nits, 3 OOS, sentence caps
  - the render-reviewer sentinel sentence `If no in-scope issues found, say "No in-scope issues found."` (hard-coded lookup used during prompt rendering)
  - the `<!-- BEGIN GENERATED_BODY -->` / `<!-- END GENERATED_BODY -->` marker pair and their wrapping outer ``` fence lines (the generator requires the first inner line to be an opening ``` and the last inner line to be a closing ```).

## Files to modify/create

### UPDATED: skills/shared/reviewer-templates.md

Compress only the `## Reviewer: Code Reviewer` `<!-- BEGIN GENERATED_BODY -->` fenced body.

- Tighten repeated prose in the checklist, scope adaptation, Do NOT report, necessity gate, quality gate, examples, and output format.
- Prefer shorter sentences and fewer explanatory asides.
- Keep every checklist item, gate, calibration example, schema field, severity rule, cap, and final instruction in substance.
- Leave the other `## Reviewer:` sections untouched.
- Keep the `<!-- BEGIN GENERATED_BODY -->` / `<!-- END GENERATED_BODY -->` marker lines and their wrapping outer ``` fence lines exactly in place; only compress prose between them. `_extract_generated_body` requires the first inner line to be an opening ``` and the last captured line to be a closing ```, or `generate code-reviewer-agent` raises `RenderError` before `generate check` surfaces drift.

### UPDATED: agents/code-reviewer.md

Regenerate from the updated template.

- Run `python3 python/cli.py generate code-reviewer-agent`.
- Do not hand-edit this generated file.

### UPDATED: skills/shared/reviewer-templates-code-reviewer.md

Regenerate the conflict-resolution Code Reviewer fragment from the same template source.

- Run `python3 python/cli.py generate conflict-resolution-code-reviewer`.
- This avoids `python3 python/cli.py generate check` drift.

### UPDATED: agents/orchestrator-aggregator.md

Compress direct prose in the hand-maintained aggregator agent.

- Keep the YAML frontmatter and hand-maintained header intact.
- Tighten intro, merge rules, reviewer-slot fidelity, empty-merge checklist, and example prose.
- Keep the output block shape and machine-validated literals unchanged.
- Keep verbatim-fix attribution behavior unchanged.

### UPDATED: python/skill-closure-baseline.json

Refresh the ratchet after prompt compression.

- Run `python3 python/cli.py lint skill-closure-growth --write`.
- Commit only the baseline changes produced by the command.

## Edge cases

- Generated artifacts can drift if only `agents/code-reviewer.md` is regenerated. Regenerate both Code Reviewer outputs.
- The aggregator validation is literal-sensitive. Avoid editing contract headings, severity line shape, OOS tag rules, and the empty-merge attestation token.
- The Code Reviewer template feeds both Claude subagent and external reviewer prompt surfaces. Keep placeholders and sidecar schema exact.
- A blank-line-only reduction may not improve content-token metrics. Prefer real prose compression.
- No fixed reduction target applies. Accept any safe panel-tier reduction verified by the closure report.

## Failure modes

- `generate check` fails if generated artifacts are stale.
- Aggregation tests fail if prompt wording changes required block grammar or attestation behavior.
- `lint skill-closure-growth` fails if the baseline is not refreshed or if another ratcheted target grows.
- Review behavior may regress if compression drops necessity-gate, OOS, or scoring calibration language.
- A blank-line-only or otherwise ineffective edit could still pass `generate check` and get its baseline refreshed, masking a run that achieved no real token reduction; the Testing strategy step 5 gate exists to catch this before `--write`.

## Testing strategy

Run targeted checks after edits:

1. `python3 python/cli.py generate code-reviewer-agent`
2. `python3 python/cli.py generate conflict-resolution-code-reviewer`
3. `python3 python/cli.py generate check`
4. `python3 python/cli.py skill-closure report`
5. Compare the post-edit `panel-tier` row's `closure_content_estimated_tokens` and `closure_lines` against the values already committed in `python/skill-closure-baseline.json`. Require both to strictly decrease. If either does not decrease, continue compressing or stop the run as not accepted; do not proceed to step 6.
6. `python3 python/cli.py lint skill-closure-growth --write` (only after step 5's gate passes)
7. `python3 python/cli.py lint skill-closure-growth`
8. `make test-aggregate-findings`
9. `make test-prune-nit-findings`
10. `make agent-sync`
11. Optionally run `python3 python/cli.py checks run-relevant` as a final changed-file gate.

## Acceptance

Run targeted checks after edits:

1. `python3 python/cli.py generate code-reviewer-agent`
2. `python3 python/cli.py generate conflict-resolution-code-reviewer`
3. `python3 python/cli.py generate check`
4. `python3 python/cli.py skill-closure report`
5. Compare the post-edit `panel-tier` row's `closure_content_estimated_tokens` and `closure_lines` against the values already committed in `python/skill-closure-baseline.json`. Require both to strictly decrease. If either does not decrease, continue compressing or stop the run as not accepted; do not proceed to step 6.
6. `python3 python/cli.py lint skill-closure-growth --write` (only after step 5's gate passes)
7. `python3 python/cli.py lint skill-closure-growth`
8. `make test-aggregate-findings`
9. `make test-prune-nit-findings`
10. `make agent-sync`
11. Optionally run `python3 python/cli.py checks run-relevant` as a final changed-file gate.

review_status: ok
rounds_completed: 2
diff_added: 20
diff_deleted: 140
mechanical_churn: true
diff_lines: 180
