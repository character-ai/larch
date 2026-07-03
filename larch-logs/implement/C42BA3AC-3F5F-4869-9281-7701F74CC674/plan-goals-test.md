## Goal
Implement issue #5980: [IMPLEMENTING] md-to-py-XI: prose-compress implementer agent prompts (_implementer-base, codex-implementer, cursor-implementer).

## Implementation Plan
## Plan

## Approach

`approach-synthesis.txt` is `NO_SKETCHES`, so draft from direct repo inspection.

Make the smallest density pass that preserves prompt contracts.

1. Read `CLAUDE.md`, `AGENTS.md`, and matching `.claude/rules` before editing.
   - Relevant rules include external-tool launcher parity, markdown code spans, and no direct submodule edits.
2. Capture current prompt size with `python3 python/cli.py skill-closure report`.
   - Current panel-tier baseline is 50,711 estimated tokens and 50,528 content tokens.
3. Tighten prose in `agents/_implementer-base.md`.
   - Preserve headings.
   - Preserve hard-guard numbering and prefixes.
   - Preserve every fenced JSON, jq, Bash, and output grammar block byte-for-byte unless the block contains non-contract prose only.
   - Preserve manifest field names, status values, bail reasons, path tokens, env vars, and CLI commands.
   - Preserve the PLR0911 sentence pinned by `scripts/test-prompt-template-invariants.sh`.
   - Do not touch `skills/implement/references/codex-manifest-schema.md`.
4. Tighten only the kind-specific intro prose in `_implementer_text()` inside `python/larch/rendering/_rendering_generators.py`.
   - Preserve frontmatter shape, auto-generated headers, generator verbs, regex/replace logic, and output paths.
   - Do not fix the pre-existing cursor-strip item-numbering mismatch. It is out of scope.
5. Regenerate:
   - `python3 python/cli.py generate codex-implementer`
   - `python3 python/cli.py generate cursor-implementer`
6. Refresh `python/skill-closure-baseline.json` with `python3 python/cli.py lint skill-closure-growth --write`.
   - Inspect the diff.
   - Accept only the expected panel-tier ratchet changes and stable ordering churn, if any.
   - Investigate any unrelated target change before proceeding.

## Files to modify/create

### UPDATED: agents/_implementer-base.md

Compress shared implementer prompt prose.

Keep byte-stable:

- JSON manifest template.
- jq predicates.
- QA JSON examples.
- status table field names.
- KV/output grammar.
- command literals.
- hard-guard identifiers.
- PLR0911 checklist sentence.

Prefer deletion and sentence tightening over reorganization.

### UPDATED: python/larch/rendering/_rendering_generators.py

Compress only the Codex and Cursor intro prose in `_implementer_text()`.

Do not change:

- `AUTO_HEADER_BY_VERB`.
- frontmatter keys.
- generator entrypoints.
- regex anchors or replacements.
- `_diff_or_write`.
- target paths.

### UPDATED: agents/codex-implementer.md

Regenerate from `agents/_implementer-base.md` and `_implementer_text("codex")`.

Do not hand-edit after generation.

### UPDATED: agents/cursor-implementer.md

Regenerate from `agents/_implementer-base.md` and `_implementer_text("cursor")`.

Do not hand-edit after generation.

### UPDATED: python/skill-closure-baseline.json

Regenerate after the prompt compression.

Expected change: lower `panel-tier` closure token counts and possibly line counts. No unrelated ratchet growth.

## Edge cases

- Generated files can drift if only the base prompt changes. Always regenerate both implementer prompts.
- Prompt compression can break machine contracts if it touches JSON, jq, status strings, field names, or command literals. Treat those as immutable.
- Markdown lint can fail on code spans with inner spaces. Avoid adding new code spans around boundary whitespace.
- The panel-tier scanner includes all `agents/*.md`, not just these three files. Verify the baseline diff stays scoped.
- The cursor-strip regex mismatch is known and out of scope. Do not renumber or restructure hard guards to “fix” it.

## Failure modes

- `generate ... --check` fails: regenerated agent files are stale or the generator changed unexpectedly.
- `lint skill-closure-growth` fails after baseline refresh: baseline was not updated or another target grew.
- Implementer launcher tests fail: intro compression changed a pinned prompt literal, launch prompt path, or manifest contract.
- Token reduction is too small: make a second prose-only pass in `_implementer-base.md`, still avoiding grammar and fence changes.

## Testing strategy

Run focused checks first:

- `python3 python/cli.py generate codex-implementer --check`
- `python3 python/cli.py generate cursor-implementer --check`
- `python3 python/cli.py generate check`
- `python3 python/cli.py skill-closure report`
- `python3 python/cli.py lint skill-closure-growth`
- `make test-codex-implementer`
- `make test-cursor-implementer`
- `make test-implement-structure`
- `make test-prompt-template-invariants`

Then satisfy acceptance with:

- `make py-test`

For the smoke `/implement` dispatch path, run the local dispatch harnesses:

- `make test-run-step2-dispatch`
- `make test-step2-dispatch`

## Acceptance

Run focused checks first:

- `python3 python/cli.py generate codex-implementer --check`
- `python3 python/cli.py generate cursor-implementer --check`
- `python3 python/cli.py generate check`
- `python3 python/cli.py skill-closure report`
- `python3 python/cli.py lint skill-closure-growth`
- `make test-codex-implementer`
- `make test-cursor-implementer`
- `make test-implement-structure`
- `make test-prompt-template-invariants`

Then satisfy acceptance with:

- `make py-test`

For the smoke `/implement` dispatch path, run the local dispatch harnesses:

- `make test-run-step2-dispatch`
- `make test-step2-dispatch`

diff_added: 40
diff_deleted: 180
mechanical_churn: true
diff_lines: 220

## Test plan
(no test plan section in plan-file)
