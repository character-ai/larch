# invoke-plan-validator.sh

Pipes `ACTION=VALIDATE_PLAN_COMMANDS ARGS=--plan-file <PATH>` into `design-driver.sh` for the supplied plan file.

Required environment:

- `DESIGN_TMPDIR`
- `CLAUDE_PLUGIN_ROOT`

The helper runs on both SIMPLE and HARD. It does not read `run-params.json` and does not skip based on tier.
