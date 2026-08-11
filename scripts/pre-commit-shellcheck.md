# scripts/pre-commit-shellcheck.sh - contract

## Purpose

`scripts/pre-commit-shellcheck.sh` is the parallel shellcheck wrapper invoked by the local `shellcheck` pre-commit hook in `.pre-commit-config.yaml`. It replaces the upstream `shellcheck-py` hook to reduce wall-clock from about 21s to about 6s on 4-core runners. The engine binary is still `shellcheck-py==0.10.0.1`, pinned via `additional_dependencies` on the local hook, so per-file behavior matches the prior pinned hook.

## Invariants

- Consumes only `"$@"` from pre-commit; file selection stays in `.pre-commit-config.yaml`.
- Always passes `-x` to shellcheck, matching the prior `args: [-x]` follow-source semantics required for scoped `--files` runs per release notes #178.
- Zero-args input exits 0 because BSD xargs has no `-r`.
- Forwards filenames as NUL-delimited records via `printf '%s\0' | xargs -0`.
- Uses portable CPU-count fallback order: `nproc`, `sysctl -n hw.ncpu`, `getconf _NPROCESSORS_ONLN`, then `1`, with a defensive clamp to `>= 1`.
- Fails fast with a directive message if shellcheck is missing on PATH.
- Exits non-zero if any shellcheck invocation fails.

## Callers

- `.pre-commit-config.yaml` `repo: local` `id: shellcheck` hook (`entry: scripts/pre-commit-shellcheck.sh`).
- Indirectly: `make shellcheck`, `make lint`, `pre-commit run shellcheck`, `python3 python/cli.py checks run-relevant --site <site> --tmpdir <tmpdir>`, and the GitHub Actions `shellcheck` job.

## Edit-in-sync rules

- Changing `-x` semantics, file-selection assumptions, or the parallelism scheme requires updating this file, the hook stanza in `.pre-commit-config.yaml`, the shellcheck CI job in `.github/workflows/ci.yaml`, and `docs/linting.md`.
- `larch lint` is a Rust workspace command; do not add a Python dependency when editing shellcheck hook dependencies.
- shellcheck-py pin: bumping `shellcheck-py==0.10.0.1` requires updating `.pre-commit-config.yaml` (`additional_dependencies` on the local shellcheck hook). The wrapper itself is version-agnostic; bumps should be validated by running the wrapper against `main` before merging.

## Local test wiring

- `pre-commit run shellcheck --all-files`
- `pre-commit run shellcheck --files <some.sh>`
- `time make shellcheck`

All three should pass on a clean tree. `time make shellcheck` should be substantially faster than the prior upstream `shellcheck-py` run.

## E3 residual scope

This check reads the residual Bash manifest through `scripts/larch.sh residual-bash paths --root "$ROOT"` or the equivalent root-local manifest read. The manifest covers kept hooks, linters, thin wrappers, `scripts/sleep-seconds.sh`, the combine-issues helper, manifest-listed includes when present, and residual harnesses. Terminal shared libraries and retired non-thin helpers are out of scope.
