# test-validate-plan-commands.sh

Offline regression harness for `validate-plan-commands.sh` + `validate-plan.sh` integration (Tier 2 demonstration).

## Running

`make test-validate-plan-commands`.

## Contract

Uses committed plan fixtures under `skills/design/scripts/fixtures/validate-plan-commands/`, including the `launch-context-plan.md` positive regression that `python/cli.py agent launch-claude-review --context-files` is recognized by the launcher's help surface.
