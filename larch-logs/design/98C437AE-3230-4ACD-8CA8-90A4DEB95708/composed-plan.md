## Plan

## Approach

Make the smallest coverage fix in the approved scope.

- Treat real launch fences with `<...>` runtime placeholders as lintable.
- Add static bg-wait coverage for the two brainstorm external launches.
- Keep `/research` out of lint scope, but document why.
- Do not change `_nearest_launch_fence` matching rules.
- Do not add runtime marker-writing for brainstorm or `/research`.

## Files to modify/create

### UPDATED: python/larch/lint/lint_bg_wait_coverage.py

- Add a short comment near `SCOPE_PATTERNS` stating that `skills/research/**` is intentionally out of scope because `/research` launches parallel lanes and waits via foreground collection, and has no marker-reading stall-recovery path.
- Remove the broad placeholder skip, or narrow it so a real launch fence that contains `<resolved>`, `<LANE_PROMPT>`, or other runtime-substituted args is still checked.
- Prefer removal unless existing tests reveal a true illustrative in-scope fence that needs a precise exemption.
- Add a `CommandMapping` for brainstorm external launches.
  - Match common stable tokens:
    - `python/cli.py`
    - `agent`
    - `launch-review`
    - `--timing-task-kind`
    - `-brainstorm`
  - Include output-path tokens if needed to keep the match narrow.
  - Use one mapping only if it covers both Framing and Scope safely.
- Do not add `skills/research/**/*.md` to `SCOPE_PATTERNS`.

### UPDATED: skills/design/references/brainstorm.md

- Add one marker directive line directly before the Framing external launch fence.
- Add one marker directive line directly before the Scope external launch fence.
- Use the existing one-directive-per-fence convention: the line must contain `run_in_background: true` and `timeout: 1260000`.
- Keep the existing launch commands unchanged.
- Do not add new runtime `.bg-wait-active` instructions.

### UPDATED: python/tests/lint/test_lint_bg_wait_coverage.py

- Add a regression test proving an unregistered background launch with `<...>` placeholders is rejected.
- Extend or add a positive test proving both brainstorm external launch shapes pass when preceded by their marker directive lines.
- Add a regression test proving a similar `skills/research/...` background fence is not linted, documenting the intentional exemption.
- Keep tests focused on the lint behavior. Use the existing `write()` and `run()` helpers.

## Edge cases

- A command with placeholders but no known mapping must fail.
- Brainstorm Framing and Scope use different output paths and timing kinds. The mapping must cover both without matching unrelated future launch-review calls too broadly.
- `/research` examples may still contain `run_in_background: true`; they must remain out of scope by path, not by accidental placeholder behavior.
- Existing prose mentions of `run_in_background: true` without nearby fences should remain ignored by the current no-fence behavior.

## Failure modes

- If the placeholder skip is removed too broadly, existing illustrative in-scope examples may start failing. Fix with a narrow exemption only for true documentation examples.
- If the brainstorm directive is not within 12 lines before its fence, the current matcher may miss it. Place each directive immediately before its fence.
- If the brainstorm mapping is too broad, future launch-review fences may be incorrectly accepted. Keep required tokens specific to brainstorm timing or outputs.

## Testing strategy

Run changed-surface checks:

- `python3 -m pytest python/tests/lint/test_lint_bg_wait_coverage.py -q`
- `python3 python/cli.py lint bg-wait-coverage`
- `python3 -m ruff check python/larch/lint/lint_bg_wait_coverage.py python/tests/lint/test_lint_bg_wait_coverage.py`

## Acceptance

Run changed-surface checks:

- `python3 -m pytest python/tests/lint/test_lint_bg_wait_coverage.py -q`
- `python3 python/cli.py lint bg-wait-coverage`
- `python3 -m ruff check python/larch/lint/lint_bg_wait_coverage.py python/tests/lint/test_lint_bg_wait_coverage.py`

review_status: ok
rounds_completed: 1
diff_added: 55
diff_deleted: 8
mechanical_churn: false
diff_lines: 63
