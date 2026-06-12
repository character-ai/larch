# invoke-plan-validator.sh

Pipes `ACTION=VALIDATE_PLAN_COMMANDS ARGS=--plan-file <PATH>` into `design-driver.sh` for the supplied plan file.

Required environment:

- `DESIGN_TMPDIR`
- `CLAUDE_PLUGIN_ROOT`

The helper runs unconditionally. It does not read `run-params.json`.
