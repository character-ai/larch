# test-launch-codex-exec.sh

Black-box harness for `scripts/launch-codex-exec.sh`.

Pinned cases:

- launcher is referenced by `lint-fix-loop.sh`
- `codex-exec` is listed in `lib-timing-kinds.sh`
- happy path exits 0 and emits `LAUNCHER_EXIT=0`
- auth setup failure writes a preflight bundle and emits `LAUNCHER_EXIT=2`
- `agent-model-args.sh` failure writes a preflight bundle
- inner `.inner.done` sentinel is promoted to `.done`
- `.meta` records `OUTER_LAUNCHER_KIND=codex-exec` and retry fields
- repeated `--add-dir` values round-trip into metadata
- temp `CODEX_HOME` is removed after exit
