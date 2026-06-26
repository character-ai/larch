## Decision 1: Scope is a pure context-relocation move (no behavior change)
- **Question**: Does this issue change any Preflight runtime behavior, or only relocate always-loaded prose?
- **Resolution**: Pure relocation. Move the Preflight item-5 `AUDIT=refuse` clarify-flow prose (clarify state / comment-post / label, partial-failure contract, breadcrumb) from `skills/implement/SKILL.md` into `skills/implement/references/preflight-plan-audit.md`, which is already MANDATORY-loaded at item 4 on the only path that produces `AUDIT=refuse`. No change to clarify-state/comment/label semantics, exit codes, audit rubric, or item 4.
- **Source**: codebase (issue body + SKILL.md items 4-5)

## Decision 2: What stays inline in SKILL.md
- **Question**: Which inline content must be preserved in SKILL.md item 5 / the exit-code table?
- **Resolution**: Keep the `/implement` orchestrator exit-codes table inline (the exit-**3** sub-case A/B/C row is unchanged). Item 5 collapses to a one-line pointer into the relocated flow in `preflight-plan-audit.md`, retaining the exit-3 statement. The forked-target `--repo "$UPSTREAM_REPO"` threading notes must travel with the relocated flow.
- **Source**: codebase (issue body "Mechanism"/"Risk" + SKILL.md exit-code table)

## Decision 3: Verification
- **Question**: What verifies the change and what must not regress?
- **Resolution**: `make test-implement-structure` must pass. Item 5 contains no ```bash fences (only inline-code commands), so the fence-shape harness should be unaffected; confirm during implementation. Savings target ~12 always-loaded lines.
- **Source**: codebase (issue body "Risk")
