## Plan

## Files to modify/create

### UPDATED: skills/design/references/design-outline.md

Replace em-dashes in user-facing print literals and prose with compliant punctuation.

Planned edits:
- Change outline skip and approval prints such as `outline — skipped`, `outline — auto-approved`, and `outline approved — proceeding` to colon or comma forms.
- Change input bullets from `` `path` — condition `` to `` `path`: condition ``.
- Keep `$DESIGN_TMPDIR`, `.outline-approved`, `design-step2b-drafter.sh`, and other wire tokens byte-stable.
- Do not change code fences, schema headings, or control-flow meaning.
- Do not edit `**MANDATORY — READ ENTIRE FILE**` directives; they are instruction text, not user-facing print literals.

### UPDATED: skills/design/references/finalize-step5.md

Replace em-dashes in warning prints and example warning text.

- Change warning strings such as `annotate skipped ... — ...`, `OOS filing completed ... — ...`, `arch diagram — generation failed`, and `plan-block-write failed — preserving` to colon, comma, or period forms.
- Keep exact paths, status tokens, exit-code references, and Step names intact.
- Do not alter Step 5 ordering or any file-writing instructions.
- Do not edit `**MANDATORY — READ ENTIRE FILE**` directives; they are instruction text, not user-facing print literals. These lines remain byte-stable.

### UPDATED: skills/implement/scripts/write-final-report.md

Replace em-dashes in report-template prose.

- Replace outcome-list separators such as `` `stalled` — ... `` with colons.
- Replace remaining prose em-dashes with commas, colons, semicolons, or short sentences.
- Preserve the backticked `` ## /<skill> run <run-id> — <outcome> `` heading example verbatim on line 7. It documents the live `pr_body.py` renderer contract; the actual heading the renderer emits must not be misrepresented.
- Preserve all other backticked tokens, env vars, `STATUS=...` grammar, flags, paths, and sentinel text.

### UPDATED: scripts/test-design-structure.sh

Update any assertions that pin text changed in `skills/design/references/design-outline.md` or `skills/design/references/finalize-step5.md`. This file pins at least the mandatory-read banner text in finalize-step5.md; confirm whether those lines change and update only the affected assertions.

### MAY_UPDATE: skills/implement/scripts/test-write-final-report.sh

Update only if a harness assertion pins wording changed in `skills/implement/scripts/write-final-report.md`.

### MAY_UPDATE: scripts/test-implement-structure.sh

Update only if existing structural assertions pin changed `write-final-report.md` prose.

## Approach

1. Search only the three approved files for `—`.
2. Classify each hit:
   - User-facing print literal or template prose: replace it.
   - `**MANDATORY — READ ENTIRE FILE**` directive: leave it unchanged (not a print literal).
   - Machine-parsed token, code fence, sentinel, or grammar: leave it unchanged.
3. Preserve the backticked `` ## /<skill> run <run-id> — <outcome> `` heading example in write-final-report.md line 7 exactly as written; edit only surrounding prose.
4. Prefer the smallest wording change for each line.
5. Use `:` for label-like separators, `,` for inline clauses, and short sentences where punctuation would be dense.
6. Re-run targeted greps on the three files scoped to user-facing print literals and template prose to confirm no em-dash remains there.
7. Update scripts/test-design-structure.sh for any assertion that pins changed text; update other conditional harness files only when targeted tests reveal pinned old strings.

## Edge cases

- Backticked examples that document renderer output contracts are not user-facing print literals. The `` ## /<skill> run <run-id> — <outcome> `` heading example must stay byte-stable.
- Do not edit historical run logs or files outside the approved scope, even if they contain em-dashes.
- Do not change the actual renderer output contract in Python during this task.

## Failure modes

- A string rewrite may change an orchestrator instruction if punctuation is too broad. Keep wording and order stable.
- Tests may pin old warning examples. Update only the affected assertion.
- A missed em-dash in user-facing prose of the three target files would fail acceptance. End with a scoped grep.

## Testing strategy

Run targeted validation:
- `grep -n $'—' skills/design/references/design-outline.md skills/design/references/finalize-step5.md skills/implement/scripts/write-final-report.md` — review hits; any hit inside a `**MANDATORY — READ ENTIRE FILE**` directive or in the backticked renderer-contract heading is expected and not a failure.
- `make test-design-structure`
- `make test-implement-structure`
- `make test-write-final-report`

If any conditional test file changes, rerun its matching target.

## Acceptance

Run targeted validation:
- `grep -n $'—' skills/design/references/design-outline.md skills/design/references/finalize-step5.md skills/implement/scripts/write-final-report.md` — review hits; any hit inside a `**MANDATORY — READ ENTIRE FILE**` directive or in the backticked renderer-contract heading is expected and not a failure.
- `make test-design-structure`
- `make test-implement-structure`
- `make test-write-final-report`

If any conditional test file changes, rerun its matching target.

review_status: complete
rounds_completed: 2
difficulty: TRIVIAL
diff_lines: 50
