## Plan

## Approach

Apply in-place prose compression to `skills/implement/SKILL.md`.

- Keep structure intact.
- Keep every Bash fence byte-exact.
- Keep all step markers, comments, headings that tests or workflows may anchor on.
- Keep all `KEY=value` grammars and exact warning strings.
- Keep every `require(skill, ...)` target from `scripts/test-implement-structure.sh`.
- Avoid editing references, scripts, tests, or `skills/design/SKILL.md`.

Use line-level edits only:

- Shorten long prose.
- Split dense sentences only when it improves scanning.
- Prefer active voice.
- Remove filler and duplicated non-load-bearing explanation.
- Preserve deliberate compaction-resilience duplication when it states a workflow guard, a NEVER rule, or a recovery boundary.

## Files to modify/create

### UPDATED: skills/implement/SKILL.md

Compress prose across the always-loaded body.

Target areas:

- Opening summary and protocol directive.
- Anti-halt and skill-name fallback reminders.
- Load-bearing invariants.
- NEVER list prose, while preserving each rule, WHY, and HOW meaning.
- Macro descriptions.
- Flags and Preflight prose.
- Step 0 through Step 18 instructions.
- Step 8+ state-machine prose, without changing branch semantics.
- Final-summary and cleanup prose, without changing marker bindings.

Preserve exactly:

- Frontmatter keys and values unless a sentence can be shortened without changing the field value.
- All `<!-- step:... -->` markers.
- All `##` / `###` headings that are referenced by tests or docs.
- Every Bash fence body.
- Fence count and shape: old=2, new=20.
- Exact launcher strings required by `scripts/test-implement-structure.sh`.
- Exact required text such as:
  - `one \`KEY=value\` record per line`
  - `Split each envelope line at the first \`=\` only`
  - `Do not parse or require an envelope on non-zero exit.`
  - `Run \`admission fork-env\`, then the preflight helper, then Step 0 bootstrap.`
  - `NEVER call \`ScheduleWakeup\``
  - `Do not spawn a Monitor`
  - `Bootstrap edit gate (NEVER #21)`
  - marker bindings for `---LARCH-SUMMARY-FINAL-BEGIN---` / `---LARCH-SUMMARY-FINAL-END---`
  - Step 18 missing-marker warning strings.

Do not:

- Move content into references.
- Add new references.
- Remove load-bearing duplication.
- Change workflow ordering.
- Change branch labels, exit-code meanings, or `NEXT_ACTION` routing.
- Touch `scripts/test-implement-fence-shape.sh`.
- Touch `scripts/test-implement-structure.sh`.
- Touch `skills/design/SKILL.md`.

## Edge cases

- Some prose is duplicated by design. Keep it when it reinforces anti-halt, no-polling, Step 8 handoff, Step 17 marker, or Step 18 cleanup behavior.
- Some long strings are test-pinned. Preserve them verbatim.
- Markdown comments may be functional anchors. Preserve them.
- Bash fences may include old-shape guards or one-line launchers. Do not rewrap them.
- Backticked paths, flags, env vars, and `KEY=value` records are protocol tokens. Do not paraphrase inside the backticks.

## Failure modes

- A compressed sentence drops a required `require(skill, ...)` substring.
- A forbidden legacy substring is accidentally reintroduced.
- A Bash fence gains whitespace, comments, wrapping, or command changes.
- A step branch changes meaning while appearing stylistic.
- A removed repetition weakens a halt-prevention guard.

## Testing strategy

Run only the existing unchanged harnesses for this surface:

```bash
make test-implement-fence-shape
make test-implement-structure
```

If either fails:

- Restore exact required strings or fence shape.
- Do not update `EXPECTED_OLD` or `EXPECTED_NEW`.
- Do not weaken the tests to match the edit.

Optional sanity check:

```bash
git diff -- skills/implement/SKILL.md
```

Review the diff for semantic drift, especially around Preflight, Step 8+, Step 16-18, and the NEVER list.

## Acceptance

Run only the existing unchanged harnesses for this surface:

```bash
make test-implement-fence-shape
make test-implement-structure
```

If either fails:

- Restore exact required strings or fence shape.
- Do not update `EXPECTED_OLD` or `EXPECTED_NEW`.
- Do not weaken the tests to match the edit.

Optional sanity check:

```bash
git diff -- skills/implement/SKILL.md
```

Review the diff for semantic drift, especially around Preflight, Step 8+, Step 16-18, and the NEVER list.

review_status: ok
rounds_completed: 1
diff_added: 90
diff_deleted: 170
mechanical_churn: false
diff_lines: 260
