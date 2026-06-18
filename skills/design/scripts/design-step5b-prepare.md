# design-step5b-prepare.sh

## Purpose

Thin launcher-compat wrapper for the `/design` Step 5b prepare block.

## Primary callers

- `skills/design/SKILL.md`
- `skills/design/scripts/design-step5.sh` for deprecated compatibility delegation

## Invariants

- The `.sh` file only derives and exports `CLAUDE_PLUGIN_ROOT`, then execs `python/cli.py design step5b-prepare`.
- `python/cli.py design step5b-prepare` owns the Step 5 prelude and OOS prepare behavior.
- The Python entrypoint binds `env = _rehydrate_wrapper_env(parsed)` before reading session keys.
- The `DESIGN_TMPDIR` guard rejects only an empty value, matching the retired Bash prelude.
- The prepare entrypoint creates `$DESIGN_TMPDIR/.completed` before writing `.completed/step-4b`.
- The prepare entrypoint returns immediately through pause-save when `.pause-requested` exists.
- It marks `design Step 5 — finalize` timing after the pause check.
- It captures OOS prepare stdout to `oos-filing-prepare.env` and stderr to `oos-filing-prepare.stderr.log`.

## Harness

Covered by `python/test_design_oos.py`, `python/test_design_cli_ports.py`, and `scripts/test-design-structure.sh`.
