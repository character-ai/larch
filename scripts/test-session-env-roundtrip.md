# scripts/test-session-env-roundtrip.sh — contract

Offline regression harness for issue #1513 covering two defensive fixes in the
session-env script pair:

- **A. `read-session-env-key.sh`** — values containing `=` characters must not
  truncate at the first separator. The corrected awk extraction matches
  whole-key + `=` and prints the substring after the first `=` (parallel to
  `value="${line#*=}"` in `session-setup.sh`'s caller-env parser). The harness
  locks the corrected behavior with fixtures for multi-`=` values, empty
  values, trailing `=`, comma-separated KV-lists, and KEY-prefix collisions
  (e.g., `FOO` vs `FOOBAR` on adjacent lines).
- **B. `write-session-env.sh`** — `--timing-ledger` paths must pass the same
  regex/length guard as the existing `--token-session-id` and
  `--claude-source-file` checks (defense-in-depth complementing #1463's
  session-setup-side validation; protects direct callers like test harnesses
  and future skills).
- **C. `write-session-env.sh`** — `--prev-implement-tmpdir` accepts absolute
  handoff paths, persists `PREV_IMPLEMENT_TMPDIR`, and rejects relative paths.
- **D. `write-session-env.sh`** — `CLAUDE_PLUGIN_ROOT` from the environment
  accepts absolute plugin-root paths, persists `LARCH_CLAUDE_PLUGIN_ROOT`, and
  rejects unsafe or relative paths.
- **E. `write-session-env.sh`** — `--dynamic-archetypes` accepts `0..8`,
  persists `LARCH_DYNAMIC_ARCHETYPES_MAX`, and rejects out-of-range values.
- **F. `write-design-current-env.sh`** — `CLAUDE_PLUGIN_ROOT` rejects unsafe or
  relative values.

## Inputs / outputs

Bash test runner. Exits non-zero on any failed assertion. Prints a final
`test-session-env-roundtrip.sh: <P> passed, <F> failed` line.

## Primary scripts under test

- `scripts/read-session-env-key.sh`
- `scripts/write-session-env.sh`
- `scripts/write-design-current-env.sh`

## Wiring

Invoked by `make test-session-env-roundtrip` and listed in one of the
`test-harnesses-*` shards in the Makefile. `scripts/test-harness-shards-coverage.sh`
asserts every `test-*` recipe is covered by exactly one shard.

## When to update

- Reading grammar changes (quoted values, multi-line values, comments) — extend
  fixtures in section A.
- New validated flags or environment-derived keys on `write-session-env.sh` —
  extend the writer sections with the same accept / reject pattern.
- `write-design-current-env.sh` `CLAUDE_PLUGIN_ROOT` validation changes — update section F.
