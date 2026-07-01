## Goal
Implement issue #5943: [IMPLEMENTING] [BUG] UserPromptSubmit hook 10s timeout: unbounded larch-* marker scan (#5868 recurrence).

## Implementation Plan
## Summary

The larch `UserPromptSubmit` hooks can exceed their 10s Claude Code hook timeout, producing "UserPromptSubmit hook timed out after 10s — output discarded. Raise the hook's timeout to allow more time." Root cause: marker discovery (`marker_candidates` in `hook-no-progress-guard.sh`, shared with `hook-bg-poll-guard.sh`) spawns a `find -maxdepth 2` per `$TMPDIR/larch-*` (and `claude-design-*` / `claude-implement-*`) directory, and the number of those dirs is unbounded and accumulates across sessions. #5868 scoped the scan by prefix but not by count; with ~1,972 `larch-*` dirs the `find` sweep alone takes ~6s and blows the 10s budget under load. This is a recurrence / incompleteness of #5868, aggravated by the tmpdir leak tracked in #5923.

## Original report

Observed the harness error "UserPromptSubmit hook timed out after 10s — output discarded. Raise the hook's timeout to allow more time." during a busy session.

## Reproduction scenario

1. In a long-lived clone, accumulate many `larch-*` scratch dirs under `$TMPDIR` (normal across many `/design` and `/implement` runs; the leak in #5923 accelerates this). The repro environment had **1,972** `$TMPDIR/larch-*` dirs.
2. Submit a prompt (fires the `UserPromptSubmit` hooks).
3. `marker_candidates()` globs `$TMPDIR/larch-*` (+ `claude-design-*` / `claude-implement-*`) and runs `find -maxdepth 2 -name .bg-wait-active` per matched dir. Measured **~5.99s** for the `find` sweep alone (cold), before the hook's marker parsing and under concurrent session load → exceeds the 10s hook budget.
4. The harness prints the timeout message and discards the hook's output. The no-progress guard fails open (safe), but it stops functioning and the message alarms the user.

## Expected behavior

The `UserPromptSubmit` hooks complete well under 10s regardless of how many `larch-*` dirs exist. Marker-discovery cost should be bounded and independent of the accumulated dir count — a single bounded walk or an index lookup, not O(N) `find` subprocess spawns.

## Observed behavior

Discovery cost grows linearly with the number of `larch-*` dirs; at ~2k dirs the `find` sweep alone (~6s) plus the rest of the hook exceeds 10s and the hook times out.

## Root cause analysis

- `scripts/hook-no-progress-guard.sh` `marker_candidates()` loops `for _lmc_d in "$TMPDIR"/larch-* "$TMPDIR"/claude-design-* "$TMPDIR"/claude-implement-*; do ... find "$_lmc_d" -maxdepth 2 -name .bg-wait-active ...; done`. Its own comment notes the #5868 scoping away the full ~77k-dir `$TMPDIR` walk, but it does not bound the number of matched `larch-*` dirs, which is unbounded.
- The same discovery logic is shared with `scripts/hook-bg-poll-guard.sh` (PreToolUse on `Read|Bash|Monitor|TaskOutput`, timeout 10) per the in-file "Same discovery logic as hook-bg-poll-guard.sh marker_candidates" comment, so the cost affects that hook too (and it fires on every matching tool call).
- Contributing factor: `larch-*` scratch dirs are not reaped, so the population grows without bound (see #5923 tmpdir leak and the `/cleanup` skill).
Measured directly: `find` sweep over 1,972 `larch-*` dirs at `-maxdepth 2` ≈ 5.99s cold.

## Evidence

- `hooks/hooks.json` — `UserPromptSubmit` registers `hook-progress-report.sh` (timeout 10) and `hook-no-progress-guard.sh` (timeout 10); `PreToolUse` registers `hook-bg-poll-guard.sh` (timeout 10).
- `scripts/hook-no-progress-guard.sh` — `marker_candidates()` glob-loop + per-dir `find` (function near the `# Same discovery logic as hook-bg-poll-guard.sh marker_candidates` comment).
- Repro environment: `find "$TMPDIR" -maxdepth 1 -name 'larch-*' | wc -l` = 1972; deep `find -maxdepth 2` sweep timed at ~5.99s.
- Predecessor: #5868 (scoped prefix + maxdepth 2 + raised timeout 5→10). Related: #5923 (tmpdir leak — the accumulation source).

## Affected files

- `scripts/hook-no-progress-guard.sh` — `marker_candidates()` discovery (the O(N) sweep).
- `scripts/hook-bg-poll-guard.sh` — shares the discovery logic; same exposure on every tool call.
- `hooks/hooks.json` — hook timeouts (raising them is a band-aid, not the fix).

## Suggested fix(es)

- Make marker discovery bounded and independent of accumulated dir count. Options: (a) treat `$HOME/.cache/larch/sessions` (already the first discovery source, a bounded index) as authoritative and drop the `$TMPDIR` glob sweep; (b) restrict the `$TMPDIR` sweep to the current session's clone-tagged dir(s) — `hook-bg-poll-guard.sh` already computes a clone-tag for its plausibility gate; (c) replace the per-dir `find` spawns with a single bounded `find` over the relevant prefixes in one process.
- Independently, reap stale `larch-*` tmpdirs (coordinate with #5923 and the `/cleanup` skill) so the population stays small.
- Raising the `hooks.json` timeout past 10s is a mitigation only; the scan must be bounded so it does not regrow past any fixed timeout.

## Open questions

- Can marker discovery rely solely on `$HOME/.cache/larch/sessions` (bounded) and drop the `$TMPDIR` glob sweep entirely, or are there marker types that only ever land in `$TMPDIR`?
- Should discovery restrict to the current session's clone-tag (like `hook-bg-poll-guard`'s plausibility gate) rather than scanning every clone's dirs?

## Test plan
(no test plan section in plan-file)
