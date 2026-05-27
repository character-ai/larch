## Decision 1: Caller wiring scope
- **Question**: Should this design include the future multi-round plan-review-loop caller wiring (the call sites that motivated R4/FINDING_2), or strictly the script-side flag?
- **Resolution**: Script-side only. Add `--allow-findings-outside-tmpdir` to `skills/review/scripts/aggregate-findings.sh` and update `skills/review/scripts/aggregate-findings.md`. No `/review` or `/design` caller changes. The future multi-round-loop caller can opt in when that partition lands.
- **Source**: user

## Decision 2: Symlink rejection under relaxation
- **Question**: When `--allow-findings-outside-tmpdir=true`, should the symlink-rejection at line 50 also relax, or remain strict?
- **Resolution**: Keep symlink rejection strict. The new flag relaxes only the containment-under-tmpdir check; symlinks remain rejected regardless of flag value. Symlink-rejection is an independent safety guarantee (no surprise indirection).
- **Source**: user

## Decision 3: Audit signal on relaxation
- **Question**: When the flag is in effect, should the script emit an audit signal (stderr warning, breadcrumb, warnings.md) to make the bypass visible?
- **Resolution**: Quiet — no audit signal. The flag is explicitly named and default-off; the opt-in itself is the audit signal. Matches the silent-relaxation pattern of existing safety flags.
- **Source**: user

## Decision 4: Flag grammar
- **Question**: Should `--allow-findings-outside-tmpdir` take a `true|false` value or be a no-value boolean flag?
- **Resolution**: `true|false` value, matching the dominant convention in `aggregate-findings.sh` (`--codex-present true|false`, `--cursor-present true|false`). Predictable; pairs with default `false`.
- **Source**: user

## Decision 5: Regression test scope
- **Question**: Should `test-aggregate-findings.sh` get regression coverage for the new flag?
- **Resolution**: Add minimal pair in the existing harness — (1) findings-file outside tmpdir + `--allow-findings-outside-tmpdir true` succeeds; (2) same setup with flag false or absent rejects with exit 2.
- **Source**: user

## Decision 6: Error message wording under relaxation OFF
- **Question**: When the flag is off (default) and containment is violated, should the existing error message stay byte-identical or change to mention the new flag?
- **Resolution**: Append a hint mentioning the new flag. The rejection message becomes self-documenting (operator sees the escape hatch in the failure). Mutates existing wording — no existing harness assertion is currently bound to the exact string, so this is safe.
- **Source**: user

## Hard constraints established
- Default behavior (flag absent or `false`) must remain semantically identical to today: containment check still rejects with exit 2, symlinks still rejected.
- All existing `/review` call sites of `aggregate-findings.sh` must continue to function unchanged — none pass `--allow-findings-outside-tmpdir` today.
- Scope is strictly the two files in the issue body (`aggregate-findings.sh`, `aggregate-findings.md`) plus the test harness for regression coverage.
