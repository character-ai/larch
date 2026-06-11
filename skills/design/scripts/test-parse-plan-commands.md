# test-parse-plan-commands.sh

Offline regression harness for `parse-plan-commands.sh` (golden TSV fixtures).

## Running

`make test-parse-plan-commands` (via `python3 python/cli.py timing harness-mark`).

## Contract

Fixtures live under `skills/design/scripts/fixtures/parse-plan-commands/`. Expected outputs are byte-stable TSV headers plus body rows.
