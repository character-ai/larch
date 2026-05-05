# skills/implement/scripts/test-oos-file-conflict-deps.sh — contract

This fixture-driven harness pins executable behavior for
`skills/implement/scripts/oos-file-conflict-deps.sh`. It writes synthetic
merged OOS batch inputs, runs the helper with explicit `--input-file` and
`--output` paths, compares exact TSV bytes, checks stderr substrings where
relevant, and verifies failure atomicity.

The harness intentionally covers behavior, not structural grep pins: same-file
serialization, disjoint and overlapping range handling, whole-file fallback,
malformed item index preservation, root-level file forms from
`scripts/file-line-regex-lib.sh`, cluster chain degradation, global-cap failure,
and parse-input edge cases involving pending headings and generic fallback
items.

When the helper's path grammar, cap policy, parse-input integration, or TSV
shape changes, update this harness in the same PR. The Makefile target is
`test-oos-file-conflict-deps`.
