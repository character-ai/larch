# design-step5c.sh

## Purpose

Bgjob launcher for the `/design` Step 5c Python entrypoint.

## Primary callers

- `skills/design/SKILL.md`

## Invariants

- Derives and exports `CLAUDE_PLUGIN_ROOT` when needed.
- Accepts prompt-side wrapper flags and forwards them unchanged to child `python/cli.py design step5c`.
- Fresh launcher stdout is exactly `BGJOB_STATUS=STARTED STEP=design-step5c PGID=<n>`.
- Before fresh `bgjob start`, reuses only a live identity-valid `design-step5c` registry row; stale or terminal result envs are cleared before fresh start.
- Recreates `$DESIGN_TMPDIR/.design-step5c-status.env`, removes stale `$DESIGN_TMPDIR/bgjob/design-step5c.result.env`, then passes that merge env to `bgjob start`.
- The Python entrypoint owns source-env rehydration, pause-save handling, publish-tail orchestration, final-summary markers, status artifacts, `.completed/step-5c`.
- `.design-step5c-status.env` remains the legacy status sidecar and is also the bgjob merge-result env.
- `$DESIGN_TMPDIR/bgjob/design-step5c.result.env` is completion truth after `bgjob wait` `DONE`.
- `python/cli.py design publish` remains the library/legacy publish-tail verb.

## Harness

Covered by `make test-design-structure`, `skills/design/scripts/test-design-step5c.sh`, and `python/test_design_lifecycle.py`.
