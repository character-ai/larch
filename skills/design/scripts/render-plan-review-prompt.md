# render-plan-review-prompt.sh

**Purpose**: Render `/design` Step 3 plan-review prompts for external reviewer slots. The renderer accepts an archetype (`arch`, `edge`, `innovation`, or `pragmatic`), a vendor (`codex` or `cursor`), and a plan file path, then writes the complete prompt to stdout.

## Invariants

- `--vendor claude` is intentionally unsupported; Claude fallback reviewers use `skills/shared/reviewer-templates.md` through `skills/design/references/plan-review.md`.
- Every prompt includes the slash-separated focus-area enum `code-quality / risk-integration / correctness / architecture / security`.
- Every prompt includes `NO_ISSUES_FOUND` as the no-findings sentinel instruction.
- Codex prompts stay terse and command-like; Cursor prompts stay path/file-list-centric.
- Invalid arguments exit 2 with diagnostics on stderr.

## Primary Callers

- `skills/design/SKILL.md` Step 3 primary external plan-review launch blocks.
- `skills/design/SKILL.md` Step 3 external fallback launch blocks.

## Harness

Run `make test-plan-review-prompt` or `bash skills/design/scripts/test-plan-review-prompt.sh`.

## Edit In Sync

Update `skills/design/SKILL.md`, `skills/design/references/plan-review.md`, `skills/design/scripts/test-plan-review-prompt.sh`, `Makefile`, and `docs/linting.md` when changing the renderer interface, vendor styles, archetype names, or output invariants.
