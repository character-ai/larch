# design-step5c.sh

## Purpose

Adapter-backed `/design` Step 5c launcher.

## Primary callers

- `skills/design/SKILL.md`

## Invariants

- Resolves a supplied session env through the trusted bgjob resolver before parent routing or tmpdir use. It never sources the file.
- Delegates lifecycle decisions to `bgjob adapt` with step `design-step5c`, explicit tmpdir, 21600-second budget, session path, and optional owner PID.
- Ordinary calls reattach a valid completed result. The wrapper-private `--fresh-attempt` control maps to `--replace-completed-result` only for documented repair and refusal retries.
- Never forwards `--fresh-attempt` to `python/cli.py design step5c`. It preserves all other public argv cells.
- Accepts child mode only as the terminal `--bgjob-child --merge-result-env <path>` suffix.
- The child requires the authoritative `.design-step5c-status.env` to contain publish, validation, final-summary, and cleanup rows, then atomically copies those rows to the adapter merge env.
- Missing Step 5b, pause, publish refusal, validation failure, and success all write the authoritative status envelope before return.
- `$DESIGN_TMPDIR/bgjob/design-step5c.result.env` remains the prompt-side completion source after `bgjob wait` reports `DONE`.

## Harness

Covered by `make test-design-step5c` and `make test-design-structure`.
