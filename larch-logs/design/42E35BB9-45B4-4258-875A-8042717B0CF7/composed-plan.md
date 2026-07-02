## Plan

## Approach

- Treat `NO_SKETCHES` as authoritative: draft from direct repo inspection and the approved outline.
- Make a contract-preserving density pass only:
  - Remove repeated prose, filler, and duplicate rubric wording.
  - Keep headings, generated markers, `{PLACEHOLDER}` tokens, dual-list headings, severity labels, JSONL/TSV schemas, and KV grammars byte-identical where they are contract text.
  - Preserve all `<!-- BEGIN GENERATED_BODY -->` / `<!-- END GENERATED_BODY -->` markers.
  - Dedupe only by shortening text in place inside each `GENERATED_BODY` block and inside each hand-maintained `agents/reviewer-*.md` file. Never hoist or cross-reference shared rubric, necessity-gate, "Do NOT report", or output-format prose out of those boundaries: `_extract_generated_body` (`python/larch/rendering/_rendering_generators.py:213-214`) copies only intra-marker text into the three generated agents, so hoisting would silently drop that guidance at runtime while `python/cli.py generate check` still passes. Accept residual duplication across blocks/files rather than hoist it out.
- Respect the non-goal for other `panel-tier` files:
  - Do not change `agents/code-reviewer.md`, `agents/_implementer-base.md`, implementer agents, orchestrator aggregator, or `skills/shared/voting-protocol.md`.
  - Avoid editing the `## Reviewer: Code Reviewer` generated body in `skills/shared/reviewer-templates.md` unless the design owner explicitly expands scope, because it would require regenerating `agents/code-reviewer.md`.
- Compress these template sections in `skills/shared/reviewer-templates.md`:
  - Top-level explanatory prose where it does not alter renderer or generator contracts.
  - `## Reviewer: Plan Fidelity`.
  - `## Reviewer: Code Robustness`.
  - `## Reviewer: Security + Structure + Tests`.
  - Update-trigger prose if it can be shortened without changing instructions.
- Regenerate generated reviewer agents from the compressed template:
  - `python3 python/cli.py generate reviewer-plan-fidelity-agent`
  - `python3 python/cli.py generate reviewer-code-robustness-agent`
  - `python3 python/cli.py generate reviewer-security-structure-tests-agent`
- Manually compress the five hand-maintained reviewer specialist agents:
  - Keep each specialist's distinct lens.
  - Align shared rubric, Do NOT report, prose length cap, output format, and structured TSV wording with the compressed template wording.
- Regenerate pre-rendered reviewer prompt bodies after any `agents/reviewer-*.md` change:
  - `python3 python/cli.py generate pre-rendered-reviewer-prompts`
- Regenerate the skill-closure baseline after the prompt source changes:
  - `make regen-skill-closure-baseline`
- Check the panel-tier metric before and after:
  - `python3 python/cli.py skill-closure report`
  - Target a meaningful reduction near 15% across the nine source files, without forcing risky wording changes just to hit a number.

## Files to modify/create

### UPDATED: skills/shared/reviewer-templates.md

Compress in-scope prose. Preserve generated-body markers, section headings used by generators, placeholder tokens, dual-list output headings, severity labels, JSONL schema fields, TSV schema fields, and sidecar instructions.

Do not touch `## Reviewer: Code Reviewer` unless scope is expanded, because `agents/code-reviewer.md` is a binding non-goal.

### UPDATED: agents/reviewer-plan-fidelity.md

Regenerate from `skills/shared/reviewer-templates.md`. Do not hand-edit after regeneration.

### UPDATED: agents/reviewer-code-robustness.md

Regenerate from `skills/shared/reviewer-templates.md`. Do not hand-edit after regeneration.

### UPDATED: agents/reviewer-security-structure-tests.md

Regenerate from `skills/shared/reviewer-templates.md`. Do not hand-edit after regeneration.

### UPDATED: agents/reviewer-correctness.md

Manually compress prose. Preserve frontmatter, specialist focus, dual-list headings, severity labels, TSV header, TSV field order, and the final "Do NOT edit any files" instruction.

### UPDATED: agents/reviewer-edge-cases.md

Manually compress prose. Preserve frontmatter, specialist focus, dual-list headings, severity labels, TSV header, TSV field order, and security-elevation semantics.

### UPDATED: agents/reviewer-security.md

Manually compress prose. Preserve frontmatter, specialist focus, dual-list headings, severity labels, TSV header, TSV field order, and security contract wording.

### UPDATED: agents/reviewer-structure.md

Manually compress prose. Preserve frontmatter, specialist focus, dual-list headings, severity labels, TSV header, TSV field order, and structure/KISS scope.

### UPDATED: agents/reviewer-testing.md

Manually compress prose. Preserve frontmatter, specialist focus, dual-list headings, severity labels, TSV header, TSV field order, and testing/regression scope.

### UPDATED: agents/pre-rendered/reviewer-plan-fidelity-body.txt

Regenerate via `python3 python/cli.py generate pre-rendered-reviewer-prompts`.

### UPDATED: agents/pre-rendered/reviewer-code-robustness-body.txt

Regenerate via `python3 python/cli.py generate pre-rendered-reviewer-prompts`.

### UPDATED: agents/pre-rendered/reviewer-security-structure-tests-body.txt

Regenerate via `python3 python/cli.py generate pre-rendered-reviewer-prompts`.

### UPDATED: agents/pre-rendered/reviewer-correctness-body.txt

Regenerate via `python3 python/cli.py generate pre-rendered-reviewer-prompts`.

### UPDATED: agents/pre-rendered/reviewer-edge-cases-body.txt

Regenerate via `python3 python/cli.py generate pre-rendered-reviewer-prompts`.

### UPDATED: agents/pre-rendered/reviewer-security-body.txt

Regenerate via `python3 python/cli.py generate pre-rendered-reviewer-prompts`.

### UPDATED: agents/pre-rendered/reviewer-structure-body.txt

Regenerate via `python3 python/cli.py generate pre-rendered-reviewer-prompts`.

### UPDATED: agents/pre-rendered/reviewer-testing-body.txt

Regenerate via `python3 python/cli.py generate pre-rendered-reviewer-prompts`.

### UPDATED: agents/pre-rendered/.manifest

Regenerate via `python3 python/cli.py generate pre-rendered-reviewer-prompts`.

### UPDATED: python/skill-closure-baseline.json

Regenerate via `make regen-skill-closure-baseline` after prompt compression. Expect the `panel-tier` row to ratchet downward.

## Edge cases

- The approved outline says eight reviewer derivatives, but the repo has three generated reviewer agents and five hand-maintained reviewer agents. Regenerate the generated three from the template. Edit only the hand-maintained five directly.
- `agents/pre-rendered/*` is a runtime surface. Leaving it stale would make renderer fallback behavior inconsistent with edited agents.
- `agents/code-reviewer.md` is generated from the Code Reviewer template section, but it is out of scope. Keep that generated section stable.
- Blank-line-only changes do not help the content-token ratchet. Prefer real prose compression.
- Do not shorten schema field names, section headings, sidecar instructions, severity labels, or parser-facing literals.

## Failure modes

- **Generated agent drift**: `python3 python/cli.py generate check` fails if generated reviewer agents or pre-rendered bodies are stale. Regenerate the affected artifacts.
- **Contract breakage**: Review collection may fail or misclassify findings if `### In-Scope Findings`, `### Out-of-Scope Observations`, severity labels, TSV headers, or JSONL fields change.
- **Scope creep**: Editing `agents/code-reviewer.md` or other non-goal panel-tier files creates avoidable churn. Revert those changes unless scope is expanded.
- **Insufficient reduction**: If the reduction falls short, make another pass over repeated rubric prose in the in-scope reviewer files before touching any non-goal file.

## Testing strategy

- Run generation checks:
  - `python3 python/cli.py generate check`
- Run rendering tests:
  - `python3 -m pytest python/tests/rendering`
- Run relevant review structure harnesses:
  - `make test-review-structure`
  - `make test-prompt-template-invariants`
- Run the skill closure ratchet:
  - `python3 python/cli.py lint skill-closure-growth --skill panel-tier`
- Run full Python tests if time allows, as requested by acceptance:
  - `make py-test`
- Inspect token metrics:
  - `python3 python/cli.py skill-closure report`
  - Confirm `panel-tier` closure tokens and content tokens decreased and the regenerated baseline reflects the new lower values.

## Acceptance

- `python3 python/cli.py generate check` exits 0: the three generated reviewer agents and their pre-rendered bodies match `skills/shared/reviewer-templates.md`.
- `python3 -m pytest python/tests/rendering` passes clean.
- `make test-review-structure` and `make test-prompt-template-invariants` pass clean.
- `make py-test` passes clean.
- `python3 python/cli.py lint skill-closure-growth --skill panel-tier` passes against the regenerated `python/skill-closure-baseline.json`.
- `python3 python/cli.py skill-closure report` shows `panel-tier` `closure_estimated_tokens` and `closure_content_estimated_tokens` strictly lower than the pre-edit baseline (58101 / 57903), and the committed `python/skill-closure-baseline.json` reflects those lower values.
- `### In-Scope Findings`, `### Out-of-Scope Observations`, severity labels, TSV headers, JSONL fields, `{PLACEHOLDER}` tokens, and every `<!-- BEGIN GENERATED_BODY -->` / `<!-- END GENERATED_BODY -->` marker stay byte-identical to their pre-edit form.
- `agents/code-reviewer.md`, `agents/_implementer-base.md`, the implementer agents, `agents/orchestrator-aggregator.md`, and `skills/shared/voting-protocol.md` are unchanged.

review_status: ok
rounds_completed: 2
diff_lines: 2200
