## Final Design Plan

The plan is very large. Showing the full plan body below.

## Context

`approach-synthesis` is `NO_SKETCHES`, so this plan uses direct code and doc inspection.

The unwanted pause comes from `python/larch/implement/scope_disposition.py`: `compute_coverage()` marks `disposition_required` when `todos_left_count > 0`. Codex can put "full `make py-lint` / `make py-test` suites were not completed" in `todos_left`, even though `/implement` intentionally runs relevant checks and later CI handles broad coverage. That validation-only todo should not count as deferred plan work.

## Approach

- Treat unrun full-suite validation reminders as nonblocking scope-disposition todos.
- Keep real `todos_left` blocking.
- Keep high-band untouched plan coverage blocking.
- Update the implementer prompt contract so Codex and Cursor avoid writing this benign todo.
- Add regression tests at both the helper and Step 2 dispatch level.

## Files to modify/create

### UPDATED: python/larch/implement/scope_disposition.py

Add a small helper near `_read_manifest_todos()` that classifies nonblocking validation todos.

Proposed semantics:

- Normalize todo text to lowercase word tokens.
- Ignore a todo only when it clearly refers to unrun or uncompleted full-suite validation and mentions `make py-lint` or `make py-test`.
- Do not ignore todos about failing checks, missing tests, unimplemented work, docs still to write, or any other actionable follow-up.
- Validate that every raw manifest todo is still a string before filtering, so malformed manifest shape remains fail-closed.
- Return and count only blocking todos from `_read_manifest_todos()`.

Keep `TODOS_LEFT_COUNT` as the count of blocking todos for scope-disposition purposes. Do not add new wire keys unless the implementation finds an existing consumer that needs raw ignored counts.

### UPDATED: python/tests/implement/test_scope_disposition.py

Add focused unit coverage:

- A manifest with only a todo like "make py-lint and make py-test (full suites) were not completed; focused tests passed" yields:
  - `todos_left_count == 0`
  - `todos_left == ()`
  - `disposition_required is False` when plan paths are touched and coverage is advisory.
- A real todo such as "finish docs" still yields `todos_left_count == 1` and requires disposition.
- A todo about a failing `make py-test` or an unimplemented test remains blocking.
- Non-string `todos_left` entries still fail closed.

### UPDATED: python/tests/implement/test_implement_dispatch.py

Add a Step 2 regression near the existing plan coverage tests:

- Fake launcher edits all firm plan paths.
- Fake manifest contains the benign full-suite validation todo.
- Assert dispatcher stdout includes `STATUS=complete`.
- Assert `PLAN_COVERAGE_DISPOSITION_REQUIRED=false`.
- Assert `TODOS_LEFT_COUNT=0`.
- Assert no scope-disposition prompt would be required by the emitted KVs.

This protects the actual bug path, not just the helper.

### UPDATED: agents/_implementer-base.md

Refine the `todos_left` manifest checklist.

Say that `todos_left` is for actionable deferred implementation work only. Tell implementers not to list unrun full-suite validation commands, including full `make py-lint` / `make py-test`, when focused relevant checks passed or `/implement`/CI owns later validation.

### UPDATED: agents/codex-implementer.md

Regenerate from `agents/_implementer-base.md` with:

```bash
python3 python/cli.py generate codex-implementer
```

Do not hand-edit generated prose except through the source template.

### UPDATED: agents/cursor-implementer.md

Regenerate from `agents/_implementer-base.md` with:

```bash
python3 python/cli.py generate cursor-implementer
```

Do not hand-edit generated prose except through the source template.

### UPDATED: skills/implement/references/codex-manifest-schema.md

Clarify the manifest contract for `todos_left`:

- It holds actionable deferred work.
- It excludes validation-only notes for full suites that `/implement` intentionally does not run on the Step 2 green path.

Keep the JSON schema unchanged.

### UPDATED: skills/implement/references/step2-dispatch.md

Update the scope-disposition prose so it matches code:

- High-band untouched firm plan paths still require disposition.
- Blocking actionable `todos_left` still requires disposition.
- Full-suite validation-only reminders are ignored for this gate.

## Edge cases

- If the plan has high untouched coverage, the prompt still appears even when all todos are ignored.
- If the todo says a check failed, do not ignore it.
- If the todo says tests still need to be added or fixed, do not ignore it.
- If `todos_left` has invalid schema, keep fail-closed behavior.
- If a future implementer writes a different benign validation phrase, the classifier may not catch it. That is acceptable. Prefer conservative matching over hiding real work.

## Failure modes

- Overbroad filtering could hide real deferred work. Keep the matcher narrow and add negative tests.
- Prompt-only changes would not fix existing Codex behavior. The Python gate must own the durable fix.
- Changing `TODOS_LEFT_COUNT` semantics could surprise a consumer. Search consumers before implementation and keep docs aligned.

## Testing strategy

Run changed-file checks only:

```bash
python3 -m pytest python/tests/implement/test_scope_disposition.py python/tests/implement/test_implement_dispatch.py
python3 python/cli.py generate codex-implementer --check
python3 python/cli.py generate cursor-implementer --check
python3 python/cli.py checks run-relevant --site manual --tmpdir <tmpdir>
```

If the implementer changes only the listed docs and Python tests pass, do not run full `make py-lint` or `make py-test` locally. CI covers broad suites.

## Difficulty

difficulty: MODERATE
mechanical_churn: true
diff_lines: 140
