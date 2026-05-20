# lib-submodule-prohibition.sh

## Purpose

Sourced-only library (no shebang) exposing `emit_submodule_prohibition()`. Centralizes the submodule PROHIBITION block emitted into coder and lint-fix prompts so the prohibition prose is maintained in one place and callers cannot diverge.

## Primary Callers

- `skills/review-and-fix/scripts/review-and-fix.sh::compose_coder_prompt()` — passes `$submodules_list` from `submodule_paths()` output
- `scripts/lint-fix-loop.sh::compose_prompt()` — passes `$forbidden_paths_file`, which includes discovered submodule paths plus `.gitmodules`; the function itself always appends the `.git/` / `.gitmodules` catch-all prohibition line

## Function Contract

```bash
emit_submodule_prohibition [submodules_list_path]
```

Writes the PROHIBITION block to stdout. When `submodules_list_path` is non-empty and the file is non-empty (`-s`), lists the submodule paths as a bullet list. Otherwise emits the "no submodule paths discovered" variant. Always appends the `.git/` / `.gitmodules` catch-all prohibition line.

## Harness

`scripts/test-lib-submodule-prohibition.sh` covers the with-submodules and no-submodules branches. Wired into `make lint` under `test-lib-submodule-prohibition`.

## Edit In Sync

Update `test-lib-submodule-prohibition.sh` and this doc together when the prohibition prose changes. Update all callers (see Primary Callers above) when the function signature changes.
