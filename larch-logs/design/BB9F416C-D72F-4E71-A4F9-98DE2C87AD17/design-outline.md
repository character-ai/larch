## Proposed Design Outline

### Goals
- Wire `scripts/lint-bash32.sh` into pre-commit so every commit that touches a tracked `*.sh` / `*.inc.bash` file fails the commit on a Bash 4+ construct.
- Inherit CI coverage automatically via the existing `lint` job (which runs `make lint-only` → `pre-commit run --all-files`); no `.github/workflows/ci.yaml` change.
- Restrict each pre-commit invocation to the staged file list (incremental), not the whole repo.

### Non-goals
- Do not add or modify the set of detected Bash 4+ constructs.
- Do not add a dedicated CI job for bash3.2.
- Do not change `make lint-bash32`'s whole-repo default behavior.
- Do not edit any submodule paths or `larch-logs/` runtime contracts.

### Approach sketch
- Extend `scripts/lint-bash32.sh` to accept positional `*.sh` / `*.inc.bash` file paths in addition to the existing `--root PATH` whole-repo mode. Positional args take precedence over `--root`. When no positional args and no `--root`, the existing whole-repo default applies (preserves `make lint-bash32` contract).
- Add a `lint-bash32` local hook to `.pre-commit-config.yaml` with `entry: bash scripts/lint-bash32.sh`, `language: system`, `types: [shell]` (covers `*.sh`; `*.inc.bash` files are linted via the same hook through a complementary `files:` regex or `types_or` if needed), and `pass_filenames: true`.
- Remove `lint-bash32` from the `lint:` Makefile umbrella (line 23) since `lint-only` now executes it through pre-commit.
- Update `scripts/test-lint-bash32.sh` to cover the new positional-file invocation in addition to the existing whole-repo and `--root` cases.
- Update `scripts/lint-bash32.md` to document the new positional-file mode and pre-commit integration.

### Surfaces in scope
- `scripts/lint-bash32.sh` (extend argv parsing; preserve git-ls-files default).
- `scripts/lint-bash32.md` (sibling doc update).
- `scripts/test-lint-bash32.sh` (harness update).
- `.pre-commit-config.yaml` (add new hook).
- `Makefile` (drop `lint-bash32` from `lint:` umbrella).

### Open questions
- None.
