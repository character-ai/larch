# render-plan-review-prompt.sh

**Purpose**: Render `/design` Step 3 plan-review prompts for external reviewer slots. The renderer accepts an archetype (`arch`, `edge`, `innovation`, `pragmatic`, or `requirements`), a vendor (`codex` or `cursor`), a plan file path, and a design tmpdir, then writes the complete prompt to stdout.

## Invariants

- `--vendor claude` is intentionally unsupported; Claude fallback reviewers use `skills/shared/reviewer-templates.md` through `skills/design/references/plan-review.md`.
- Every prompt includes the slash-separated focus-area enum `code-quality / risk-integration / correctness / architecture / security`.
- Every prompt includes `{"no_issues_found": true}` as the canonical no-findings sentinel instruction. `NO_ISSUES_FOUND` remains validator-supported only for backward compatibility.
- Both Cursor and Codex prompts include the full `full_role` personality prose and a TSV structured-record block contract so all archetype outputs can pass through `collect-agent-results.sh --structured-reviewer-validation`.
- `--design-tmpdir <path>` or `DESIGN_TMPDIR` is required. The renderer reads `run-params.json` through `scripts/read-design-classification.sh`.
- The renderer reads `skills/design/references/readability-style.md` (or `READABILITY_STYLE_FILE` in tests) and substitutes every `<READABILITY_STYLE>` token before writing stdout. If the file is missing or empty, it warns on stderr and leaves the prompt otherwise valid.
- The output order is `<role-line>\n<tier-emphasis>\n<rest-of-prompt>`. `dispatch-plan-review-panel.sh` strips only line 1 with `tail -n +2`, preserving the tier emphasis for dynamic prompts.
- If `run-params.json` is missing or invalid, classification defaults to HARD and the reader prints a warning to stderr.
- Invalid arguments exit 2 with diagnostics on stderr.

### Plan-vs-current-state invariant

The rendered prompt body MUST contain the paragraph "The plan describes the codebase AFTER this PR lands. …" between the "Review the implementation plan file at" sentence and the "Walk five focus areas" sentence. This paragraph instructs plan reviewers that the plan describes post-implementation state — preventing the systematic false-positive class where reviewers flag current-code behaviors as bugs even when the plan itself addresses them. The invariant is enforced by `skills/design/scripts/test-plan-review-prompt.sh` (substring assertion).

## Primary Callers

- `skills/design/SKILL.md` Step 3 primary external plan-review launch blocks.
- `skills/design/SKILL.md` Step 3 external fallback launch blocks.

## Harness

Run `make test-plan-review-prompt` or `bash skills/design/scripts/test-plan-review-prompt.sh`.

## Edit In Sync

Update `skills/design/SKILL.md`, `skills/design/references/plan-review.md`, `skills/design/references/readability-style.md`, `skills/design/scripts/test-plan-review-prompt.sh`, `Makefile`, and `docs/linting.md` when changing the renderer interface, vendor styles, archetype names, structured-output contract, readability substitution, or output invariants.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.
