## Goal
Eliminate fragile two-step prose contract for tally writes by consolidating into write-tally.sh

## Implementation Plan

Create `scripts/write-tally.sh` — a single script that wraps `compose-tally-record.sh` + `larch-log.sh write` atomically, eliminating the fragile two-step prose contract in SKILL.md. Also create its sibling doc and test harness, and wire into Makefile.

### Files to create

1. **`scripts/write-tally.sh`** (executable, follows lib-quiet.sh discipline):
   - Source `lib-quiet.sh`, call `larch_quiet_init`, redirect stdout to FD 3 (same pattern as `compose-tally-record.sh`)
   - Parse all flags: `--log-root`, `--skill`, `--run-id`, `--phase plan-review|code-review`, `--mode simple|hard`, `[--rounds N]`, `[--accepted N]`, `[--rejected N]`, `--body-file <path>`
   - Required: `--log-root`, `--skill`, `--run-id`, `--phase`, `--mode`, `--body-file`; optional (default 0): `--rounds`, `--accepted`, `--rejected`
   - Derive batch slug: `plan-review` → `plan-review-tally`; `code-review` → `code-review-tally`
   - Validate `--phase`, `--mode`, `--body-file` (exists, not a symlink)
   - mktemp to `${TMPDIR:-/tmp}/write-tally-record.XXXXXX`, trap EXIT for cleanup
   - Run `compose-tally-record.sh --phase "$PHASE" --mode "$MODE" --rounds "$ROUNDS" --accepted "$ACCEPTED" --rejected "$REJECTED" --body-file "$BODY_FILE" > "$RECORD_FILE"` — on failure: `emit_kv FAILED true`, `emit_kv ERROR "compose-tally-record.sh failed"`, exit 2
   - Run `larch-log.sh write --log-root "$LOG_ROOT" --skill "$SKILL" --run-id "$RUN_ID" --batch "$BATCH" --input-file "$RECORD_FILE"` — capture stdout, forward all KV lines via `emit_kv`, propagate exit code
   - Use `larch_err` for all validation diagnostics (never raw `echo >&2`)

2. **`scripts/write-tally.md`** — sibling contract per `.claude/rules/script-md-siblings.md`:
   - Purpose, primary callers (SKILL.md Step 1 and Step 5), invariants, harness location

3. **`scripts/test-write-tally.sh`** — 11 pinned test cases (follow `test-compose-plan-goals-test.sh` pattern):
   1. Happy path — plan-review hard (verify LOG_WRITTEN=true, JSON valid, schema_version=1, phase, batch, mode, rounds, accepted_count, rejected_count, body)
   2. Happy path — code-review simple (verify batch slug = code-review-tally)
   3. Defaults (omit --rounds/--accepted/--rejected; assert they default to 0 in output JSON)
   4. Missing required flag (omit --phase; exit 2, diagnostic)
   5. Invalid phase value (--phase code-search; exit 2)
   6. Invalid mode (--mode quick; exit 2)
   7. Missing body file (--body-file /does/not/exist; exit 2)
   8. Composer failure passthrough (stub compose-tally-record.sh; verify FAILED=true ERROR=...)
   9. Writer failure passthrough (bogus --log-root; verify non-zero exit + envelope)
   10. Atomicity (verify no partial batch file on failure)
   11. Channel discipline (machine output on stdout only; diagnostics to stderr)
   Use a real temporary log root for integration paths (not stub larch-log.sh), consistent with how `test-larch-log.sh` works.

4. **`Makefile`** — add `test-write-tally` to:
   - `.PHONY` line
   - `test-harnesses-4` shard (alongside `test-compose-plan-goals-test`)
   - New target `test-write-tally:\n\tbash scripts/test-write-tally.sh`

### Edge cases
- `--body-file` symlink → `compose-tally-record.sh` already rejects; `write-tally.sh` passes through
- tmpfile cleanup on EXIT trap catches all exit paths including signal
- `larch-log.sh write` forwards its full KV envelope via emit_kv; caller sees the same output as direct invocation


## Test plan
Run `bash scripts/test-write-tally.sh` — all 11 cases pass.
Run `make lint` — green (pre-commit + agent-lint).
