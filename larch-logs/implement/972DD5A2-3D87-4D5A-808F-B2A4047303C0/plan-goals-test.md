## Goal
Emit fractional-second timings from harness-timer.sh using Python time.time()

## Implementation Plan
## Objective
Emit fractional-second timings (2 decimal places) from `scripts/harness-timer.sh` so data-driven shard rebalancing can distinguish sub-second tests. Currently `date +%s` gives integer-only resolution; > 50% of tests on sampled CI shards report `0s`.


### 1. Modify `scripts/harness-timer.sh`

Replace the integer `date +%s` approach with Python `time.time()` (Option A from the issue). Python3 is already a hard dependency of the harness. Keep the rest of the wrapper identical (pass-through argv, mirror exit code, print LARCH_HARNESS_TIMING line).

No `set -euo pipefail` — the script intentionally captures `$?` from the inner command after a non-zero exit, which is incompatible with `set -e`.

New content:
```bash
#!/usr/bin/env bash
name="$1"; shift
start=$(python3 -c 'import time; print(time.time())')
"$@"
rc=$?
end=$(python3 -c 'import time; print(time.time())')
elapsed=$(python3 -c "print(f'{$end - $start:.2f}')")
printf 'LARCH_HARNESS_TIMING\t%s\t%ss\n' "$name" "$elapsed"
exit "$rc"
```

### 2. Create `scripts/test-harness-timer.sh`

New regression harness with three test cases:
1. `sleep 0.5` — assert timing output matches `^0\.[4-6][0-9]s$` (allows slop for sleep precision)
2. `sleep 2` — assert timing output matches `^[12]\.[0-9]{2}s$`
3. `false` — assert exit code 1 is mirrored AND a LARCH_HARNESS_TIMING line is still emitted

Pattern: capture stdout, grep for LARCH_HARNESS_TIMING line, extract the timing field, match against regex. Use `set -euo pipefail`. Follow the same structure as peer harnesses (SCRIPT_DIR, REPO_ROOT, cleanup_tmpdir, PASS/FAIL counters, non-zero exit on failure).

### 3. Create `scripts/test-harness-timer.md`

Sibling stub doc (required by `.claude/rules/script-md-siblings.md`): one paragraph pointing to `scripts/harness-timer.md` as the primary contract doc, naming what this harness tests.

### 4. Update `scripts/harness-timer.md`

- Change the "Duration uses `date +%s` (second granularity)" invariant to document fractional-second output
- Document the new output shape: `<N>` token is now `^[0-9]+(\.[0-9]+)?s$` (integer-or-float)
- Add parser-acceptance contract note
- Update `## Regression Harness` section to name `scripts/test-harness-timer.sh`
- Update "Edit-In-Sync" note (remove reference to `docs/linting.md "Refreshing harness shard balance"` only if needed; keep it otherwise)

## Edge Cases / Testing Strategy
- sleep precision on Linux CI vs macOS: the `^0\.[4-6][0-9]s$` regex gives ±100ms slop
- exit code mirroring for failing inner command: explicit `false` test
- The LARCH_HARNESS_TIMING sentinel stays identical; only the numeric field widens
- Parser-acceptance note: existing integer logs in committed history don't get rewritten; analyzers must accept both integer and float shapes matching `^[0-9]+(\.[0-9]+)?s$`

## Files Changed
- `scripts/harness-timer.sh` — rewrite timing approach (~7 lines, same line count)
- `scripts/test-harness-timer.sh` — new (~55 lines)
- `scripts/test-harness-timer.md` — new stub (~15 lines)
- `scripts/harness-timer.md` — update invariant, add parser contract, update harness section (~10 line changes)

## Test plan
(no test plan section in plan-file)
