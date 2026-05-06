# scripts/round-trip-detect.sh — contract

`scripts/round-trip-detect.sh` is the pure detector for the managed `[ROUND-TRIP] ` title marker. Primary callers are `/implement` Step 0.5, Step 12a/12b, `scripts/implement-finalize.sh` Step 18, `/fix-issue` Step 3/6, and `skills/fix-issue/scripts/finalize-umbrella.sh`.

## Contract

The title marker grammar is strict ASCII and is documented canonically in `scripts/tracking-issue-write.md`: exactly `[ROUND-TRIP] `, with uppercase text, ASCII hyphen, and one trailing space. This detector does not mutate titles; it emits only `ROUND_TRIP=true` or `ROUND_TRIP=false` on stdout and always exits 0. Any read or invocation error emits `ROUND_TRIP=false` plus a stderr warning so callers degrade safely.

Inputs are concatenated with newlines. `--text-file PATH` is the required transport for issue bodies, PR bodies, and feature descriptions because those can be large or sensitive; callers should write temp files under their run tmpdir and clean them with their existing traps. `--text-string STR` is restricted to short trusted strings such as issue titles. `--stdin` is available for tests or callers with a pipe-friendly text source. The detector performs case-insensitive body matching with POSIX explicit boundaries, not `\b`, so GNU/BSD grep behavior remains aligned.

The grep is intentionally in an `if printf ... | grep -qiE ...; then` form. Do not replace it with `grep ... || true` or `set +e`; the current shape preserves `set -euo pipefail` without a carve-out and remains Bash 3.2 compatible. The script performs no network IO and never raises to callers.

Negative fixtures are vendored locally in `scripts/test-round-trip-detect-negative-fixtures.txt`; they cite #1239 as provenance but are not fetched from live issue text. The harness is `scripts/test-round-trip-detect.sh`, wired through `make test-round-trip-detect` and the `test-harnesses-3` shard.

## Edit In Sync

When changing marker phrases, update this contract, `scripts/test-round-trip-detect.sh`, `scripts/test-round-trip-detect-negative-fixtures.txt`, and every caller contract that documents its round-trip detection hook. If the strict title token changes, update `scripts/tracking-issue-write.md` and its tests in the same PR.
