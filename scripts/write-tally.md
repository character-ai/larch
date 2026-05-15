# write-tally.sh contract

`scripts/write-tally.sh` composes and writes the implement plan-review or
code-review tally run-log batch in one helper call. It wraps
`scripts/compose-tally-record.sh` and `scripts/larch-log.sh write`, so callers
never pass a raw markdown tally body directly to a `.json` tally batch.

Primary callers:

- `skills/implement/SKILL.md` Step 1, for the `plan-review-tally` batch.
- `skills/implement/SKILL.md` Step 5, for the `code-review-tally` batch.

Inputs:

```text
--log-root D
--skill S
--run-id R
--phase plan-review|code-review
--mode simple|hard
[--rounds N]
[--accepted N]
[--rejected N]
--body-file PATH
```

The phase determines the target batch: `plan-review` maps to
`plan-review-tally`, and `code-review` maps to `code-review-tally`. Count flags
default to `0`. The body file must be a regular non-symlink file. The helper
uses a temporary record file under `${TMPDIR:-/tmp}` and removes it on exit.

On composer failure, stdout receives:

```text
FAILED=true
ERROR=compose-tally-record.sh failed
```

On writer success or failure, the helper forwards the `larch-log.sh write` KV
envelope unchanged. Validation diagnostics are emitted with `larch_err`, not
raw stderr writes, and the script follows the `lib-quiet.sh` stdout contract.

Harness: `scripts/test-write-tally.sh`, wired through `make test-write-tally`
and the `test-harnesses-4` shard.

Test-only override environment variables:

- `LARCH_WRITE_TALLY_COMPOSER` points at an alternate composer executable.
- `LARCH_WRITE_TALLY_LOGGER` points at an alternate logger executable.
