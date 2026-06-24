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
- It emits `NEXT_ACTION=skip-pipeline|file-issues` on stdout for deterministic Step 5b routing. Every skip status (`skip-sentinel`, `skip-already-filed-sentinel`, `skip-no-items`, `skip-all-security`) emits `NEXT_ACTION=skip-pipeline`. `ready` emits `NEXT_ACTION=file-issues`.
- It emits `OOS_SKIP_BREADCRUMB=` for known skip statuses. Prompt-side Step 5b reprints this breadcrumb when non-empty.
- `STEP5B_NEEDS_ANNOTATE=true` remains the annotate routing key. It is always emitted for `ready`.
- For `skip-already-filed-sentinel`, `STEP5B_NEEDS_ANNOTATE=true` is emitted only when `oos-issue.stdout.txt` exists and is non-empty.
- The prepare entrypoint writes `.completed/step-5b` for terminal skip paths and for `skip-already-filed-sentinel` when annotate is not needed. When `STEP5B_NEEDS_ANNOTATE=true`, prepare defers completion to annotate.
- It relays `WARN=` rows for skip-already recovery diagnostics.
- Prepare failure emits `NEXT_ACTION=skip-pipeline`, keeps the existing warning path, and writes `.completed/step-5b`.
- When `NEXT_ACTION` is absent from degraded output, prompt-side Step 5b falls back to `FILE_DESIGN_OOS_STATUS=` per `skills/design/references/oos-step5b-dispatch.md`.

## Harness

Covered by `python/test_design_oos.py`, `python/test_design_cli_ports.py`, and `scripts/test-design-structure.sh`.
