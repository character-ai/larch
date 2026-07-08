# design-step5c.sh

## Purpose

Bgjob launcher for the `/design` Step 5c Python entrypoint.

## Primary callers

- `skills/design/SKILL.md`

## Invariants

- Derives and exports `CLAUDE_PLUGIN_ROOT` when needed.
- Accepts prompt-side wrapper flags and forwards them unchanged to child `python/cli.py design step5c`.
- Fresh launcher stdout is exactly `BGJOB_STATUS=STARTED STEP=design-step5c PGID=<n>`.
- Before fresh `bgjob start`, reuses a live identity-valid `design-step5c` registry row or regular `$DESIGN_TMPDIR/bgjob/design-step5c.result.env`; stale or dead rows are cleared.
- Recreates `$DESIGN_TMPDIR/.design-step5c-status.env`, removes stale `$DESIGN_TMPDIR/bgjob/design-step5c.result.env`, then passes that merge env plus sentinel `$DESIGN_TMPDIR/.completed/step-5c-terminal` to `bgjob start`.
- The Python entrypoint owns source-env rehydration, pause-save handling, publish-tail orchestration, final-summary markers, status artifacts, `.completed/step-5c`, and `.completed/step-5c-terminal`.
- `.design-step5c-status.env` remains the legacy status sidecar and is also the bgjob merge-result env.
- `$DESIGN_TMPDIR/bgjob/design-step5c.result.env` is completion truth after `bgjob wait` `DONE`.
- `python/cli.py design publish` remains the library/legacy publish-tail verb.

## Harness

Covered by `scripts/test-design-structure.sh`, `skills/design/scripts/test-design-step5c.sh`, and `python/test_design_lifecycle.py`.
