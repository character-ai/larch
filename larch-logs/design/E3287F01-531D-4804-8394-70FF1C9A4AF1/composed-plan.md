## Plan

## Approach

Use the approved narrow scope.

Keep behavior stable except where the issue asks for hardening:

- Keep float `closure_estimated_tokens` rows skipped.
- Keep duplicate `skill` rows last-wins.
- Add stderr warnings and short code comments for those two decisions.
- Clear vanished targets from `_build_revisions()` so reappearing targets have no stale previous value.
- Parse `git log --format=%H%x00%s` rows with a first-delimiter split, not an all-delimiter split.

## Files to modify/create

### UPDATED: python/larch/lint/skill_closure_ledger.py

- In `_parse_snapshot()`:
  - When `target` is a string and `tokens` is a JSON float, skip the row as today.
  - Print a warning to stderr with the existing `skill-closure ledger:` prefix and the snapshot `label`.
  - Add a brief comment that floats stay skipped to avoid inventing historical integer token values.
  - When a valid integer row repeats a `skill`, keep last-wins as today.
  - Print a warning to stderr with the existing `skill-closure ledger:` prefix, the label, and target.
  - Add a brief comment that last-wins is retained for compatibility but no longer silent.
- In `_build_revisions()`:
  - Track the targets present in the current `BaselineSnapshot`.
  - Remove any `last_values` keys absent from the current snapshot before moving to the next revision, or otherwise ensure the next revision cannot diff against a value from before a gap.
  - Preserve current first-seen behavior: `previous`, `delta`, and `is_raise` stay blank or false when the target appears with no immediate prior value.
- Do not add flags, output columns, or summary semantics beyond the stale-value correction.

### UPDATED: python/larch/git/git.py

- In `log_path_commits()`:
  - Replace `line.split("\x00")` with `line.split("\x00", 1)` — not `partition("\x00")`, which on a delimiter-free row returns an empty separator and empty tail and would silently defeat the malformed-line check.
  - Keep the existing check `len(parts) != 2 or not parts[0]` to raise `ShipError` for rows with no delimiter or an empty SHA; `split(sep, 1)` still yields exactly 1 part when no delimiter is present, so the missing-delimiter case stays caught.
  - Preserve embedded `\x00` bytes inside the subject instead of treating them as extra fields.
  - Keep argv order and `rev_range` behavior unchanged.

### UPDATED: python/tests/lint/test_skill_closure_ledger.py

Add focused tests in the existing file.

- Invalid `--root`:
  - Call `ledger.ledger_main(["--root", str(tmp_path / "missing")])`.
  - Assert rc `2`.
  - Assert stderr contains `skill-closure ledger: --root is not a directory`.
- Unresolved `--since-tag`:
  - Use the existing temp git history fixture.
  - Call `ledger_main(["--root", str(repo), "--since-tag", "missing-tag"])`.
  - Assert rc `2` (do not rely on the stderr substring alone to pin the exit-2 contract).
  - Assert stderr contains `--since-tag does not resolve to a commit: missing-tag`.
- Float warning:
  - Call `_parse_snapshot()` directly with a float-valued row.
  - Assert the float row is skipped.
  - Assert stderr includes the prefix, label, target, and `closure_estimated_tokens`.
- Duplicate warning:
  - Call `_parse_snapshot()` directly with duplicate valid `skill` rows.
  - Assert last-wins value is retained.
  - Assert stderr includes the prefix, label, target, and duplicate warning text.
- Stale target clearing:
  - Extend or add a small fixture where `panel-tier` appears, disappears for one revision, then reappears.
  - Run detailed ledger output.
  - Assert the reappearing `panel-tier` row has empty `previous` and `delta`, and `raise` is `false`.

### UPDATED: python/tests/git/test_git.py

Add two unit tests beside the existing `log_path_commits` tests.

- Embedded-NUL subject:
  - Stub `git log` stdout with one row like `abc123\x00Subject with \x00 embedded nul\n`.
  - Assert `log_path_commits()` returns one `PathCommit` with `sha="abc123"` and the full subject after the first delimiter.
- Empty-SHA malformed row:
  - Stub `git log` stdout with one row like `\x00Subject only\n` (delimiter present, SHA empty).
  - Assert `log_path_commits()` raises `ShipError` matching `"malformed line"`, the same contract as the existing no-delimiter case.
- Keep the existing malformed-output test unchanged to pin the no-delimiter failure.

## Edge cases

- JSON booleans must still be rejected as token values. Do not let `bool` pass through the `int` branch.
- Missing or non-string `skill` rows should remain silent skips unless the row also matches the explicit float decision path.
- Duplicate warnings should fire only when a valid integer row overwrites an earlier valid value.
- A target absent for one or more revisions should not contribute a cross-gap raise when it returns.
- `log_path_commits()` should still reject empty SHA rows and rows without the SHA-subject delimiter, including after the `split(sep, 1)` change.

## Failure modes

- Warning text that lacks the existing prefix can break operator greps and test expectations.
- Removing stale values too early or too late can alter normal adjacent-revision deltas.
- Direct `_parse_snapshot()` stderr tests can become brittle if they over-pin wording. Assert stable substrings, not the whole warning line.
- Using `partition()` instead of `split(sep, 1)`, or omitting the empty-separator/empty-SHA check, would silently accept delimiter-free or empty-SHA malformed rows instead of raising `ShipError`.

## Testing strategy

Run only changed-file relevant tests:

```bash
python3 -m pytest python/tests/lint/test_skill_closure_ledger.py python/tests/git/test_git.py
```

If lint is requested for changed files, run:

make py-lint

No repository docs, CLI flags, or security policy changes are expected.

difficulty: MODERATE

## Acceptance

- Each item above either has a fix + test, or an explicit documented behavior decision (e.g. a code comment or docs note explaining the chosen tradeoff), backed by a test that pins the chosen behavior.

review_status: ok
rounds_completed: 3
difficulty: MODERATE
diff_lines: 120
