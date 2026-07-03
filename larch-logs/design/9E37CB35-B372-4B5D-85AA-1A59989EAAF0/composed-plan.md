## Plan

## Approach

Implement the smallest hard cutover from `design parse-argv` to `design parse-flags`.

- Keep the existing parser state machine in `python/larch/design/design_argv.py`.
- Rename only the public CLI entrypoint and consumer-facing prose.
- Add a sourceable `ERROR_MESSAGE` field on validation failures.
- Make Step 0-pre print that message verbatim, before session setup.
- Preserve existing acceptance and rejection behavior, including rc `3` and `VALIDATION_ERROR`.
- Remove the eager `flags.md` read from `skills/design/SKILL.md`.
- Update `flags.md` header text only, plus stale `parse-argv` references.
- Regenerate the design skill closure baseline after the eager file drops out.

## Files to modify/create

### UPDATED: python/larch/design/design_argv.py

- Replace `parse_argv_main` with `parse_flags_main` as the public main.
- Keep parsing semantics unchanged.
- Add one helper that formats the exact ready-to-print Step 0-pre error line:
  - `**⚠ /design: unrecognized or disallowed public flag — aborting before session setup.** <token>`
- On validation failure, emit both:
  - `VALIDATION_ERROR=<token>`
  - `ERROR_MESSAGE=<ready-to-print line>`
- Write both fields to `--output` when provided.
- Preserve newline redaction to `newline-in-value`.
- Preserve hidden `--output` behavior and rc values.

### UPDATED: python/larch/design/design_step0_env.py

- Keep the private helper name `_run_parse_argv` unchanged. Renaming it would force collateral churn with no product-visible gain: a re-export update in `python/larch/design/design_lifecycle.py`, six `monkeypatch.setattr(..., "_run_parse_argv", ...)` sites in `python/tests/design/test_design_lifecycle.py`, and a regen of `python/subprocess-via-runner-baseline.json`. Change only the subprocess argv token it invokes, from `("design", "parse-argv")` to `("design", "parse-flags")`, plus user-facing/diagnostic prose.
- Invoke `python/cli.py design parse-flags --output ...`.
- Allow `ERROR_MESSAGE` in the parsed env file.
- On rc `3`, print `ERROR_MESSAGE` exactly when present.
- Keep fallback diagnostics for malformed parser output or unexpected rc.
- Do not start session setup after any parse failure.

### UPDATED: python/larch/cli.py

- Replace the registry entry:
  - old: `("design", "parse-argv")`
  - new: `("design", "parse-flags")`
- Replace the machine-stdout allowlist key the same way.
- Do not keep a `parse-argv` registry shim.

### UPDATED: skills/design/SKILL.md

- Change Step 0-pre and flag intro text to `python/cli.py design parse-flags`.
- Remove the mandatory pre-parse read of `skills/design/references/flags.md`.
- Fix the Step 0-pre subsection's own `**When**: immediately after reading references/flags.md and before Step 0a.` line so it no longer names `flags.md` as a prerequisite (for example: `**When**: immediately before Step 0a.`). Leaving that line unchanged would still nominally require the read even after the mandatory-read directive above it is removed.
- State that Python owns validation and ready-to-print error rendering.
- Keep the compact flag table as a non-normative user-facing index.
- Change `flags.md` references to conditional background where needed.
- Fix stale package path mentions from flat `python/design_argv.py` to `python/larch/design/design_argv.py`.

### UPDATED: skills/design/references/flags.md

- Update the header only for authority and load semantics:
  - consumer becomes conditional background prose for `/design` flags and adjacent non-argv notes.
  - contract stops claiming normative validation authority.
  - when-to-load stops saying invocation start.
- Replace `parse-argv` mentions with `parse-flags`.
- Leave plan-size thresholds, Step 3 review env vars, validator summary, and legacy branch-info prose unchanged.

### UPDATED: python/tests/design/test_design_argv.py

- Point helper invocations at `design parse-flags`.
- Rename test names where useful.
- Preserve the existing acceptance/rejection matrix.
- Add assertions for `ERROR_MESSAGE` on validation failures.
- Add a sourceable-output assertion for quoted `ERROR_MESSAGE`.
- Assert `design parse-argv` is no longer accepted only if the dispatcher test style supports that without brittle help text matching.

### UPDATED: python/tests/test_cli.py

- Update the registry and quiet-mode test from `parse-argv` to `parse-flags`.
- Update mocked module function name to `parse_flags_main`.

### UPDATED: python/larch/implement/checks_run_relevant.py

- Fix only the stale direct target rule for the design argv parser.
- Use real package paths:
  - `python/larch/design/design_argv.py`
  - `python/tests/design/test_design_argv.py`
- Keep the existing focused make target unless renaming it is needed by tests.

### UPDATED: python/tests/implement/test_checks.py

- Update the relevant-checks focused-target case from the dead flat path to the real package path.
- Keep expected target coverage for the design flag parser.

### MAY_UPDATE: Makefile

- Rename `test-parse-design-argv` only if the implementer chooses to remove the stale name from focused-check output.
- If renamed, update every relevant-checks expectation and any cached target references in the same commit.
- Prefer leaving the target name stable if it avoids unrelated churn.

### MAY_UPDATE: scripts/test-design-structure.sh

- Update only if a structural pin names `parse-argv` or requires `flags.md` as eager closure.
- Direct inspection found no explicit `parse-argv` pin, so this may stay unchanged.

### UPDATED: python/skill-closure-baseline.json

- Regenerate with `python3 python/cli.py lint skill-closure-growth --write`.
- Confirm the design eager closure no longer lists `skills/design/references/flags.md`.
- Confirm the token drop is roughly the file's former contribution.

## Edge cases

- No args still yields `POSITIONAL_KIND=none`.
- Numeric issue may appear before or after supported flags.
- Unknown or retired flags after a numeric issue still fail.
- A non-numeric first positional keeps later flag-like tokens literal.
- `--` stops flag parsing.
- Duplicate `--per-round-approval` and duplicate `--skip-approve` still fail.
- `--per-round-approval` plus `--skip-approve` remains allowed.
- Missing `--run-id` and missing or invalid `--difficulty` still fail with the same token.
- Newlines in values still normalize to `newline-in-value`.
- Public `--output` remains rejected after the hidden internal `--output` is stripped.

## Failure modes

- A lingering `parse-argv` call would make Step 0-pre fail before session setup.
- A missing `ERROR_MESSAGE` would force Step 0-pre back to synthesized prose and weaken exact-string coverage.
- Keeping `flags.md` in eager closure would fail the acceptance goal even if parsing works.
- Updating non-argv sections in `flags.md` could drift threshold or validator semantics, which is out of scope.
- A stale relevant-checks path would skip the focused parser test on future edits.

## Testing strategy

Run focused checks only.

1. Parser matrix:
   - `make test-parse-design-argv`
2. CLI registry:
   - `python3 -m pytest python/tests/test_cli.py`
3. Relevant-checks mapping:
   - `python3 -m pytest python/tests/implement/test_checks.py -k 'direct_targets_design_module_focused_targets or design_step2b_routes or design_lifecycle'`
4. Design structure and closure:
   - `bash scripts/test-design-structure.sh`
   - `python3 python/cli.py lint skill-closure-growth --skill design`
   - `python3 python/cli.py skill-closure report`
5. Manual smoke:
   - `python3 python/cli.py design parse-flags --brainstorm 123`
   - `python3 python/cli.py design parse-flags --hard`
   - confirm `VALIDATION_ERROR=--hard`, `ERROR_MESSAGE=... --hard`, and rc `3`.
   - confirm `python3 python/cli.py design parse-argv --brainstorm 123` is not a registered command.

## Acceptance

Run focused checks only.

1. Parser matrix:
   - `make test-parse-design-argv`
2. CLI registry:
   - `python3 -m pytest python/tests/test_cli.py`
3. Relevant-checks mapping:
   - `python3 -m pytest python/tests/implement/test_checks.py -k 'direct_targets_design_module_focused_targets or design_step2b_routes or design_lifecycle'`
4. Design structure and closure:
   - `bash scripts/test-design-structure.sh`
   - `python3 python/cli.py lint skill-closure-growth --skill design`
   - `python3 python/cli.py skill-closure report`
5. Manual smoke:
   - `python3 python/cli.py design parse-flags --brainstorm 123`
   - `python3 python/cli.py design parse-flags --hard`
   - confirm `VALIDATION_ERROR=--hard`, `ERROR_MESSAGE=... --hard`, and rc `3`.
   - confirm `python3 python/cli.py design parse-argv --brainstorm 123` is not a registered command.

review_status: complete
rounds_completed: 2
difficulty: MODERATE
diff_lines: 260
