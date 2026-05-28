## Decision 1: Implementation venue for CI/pre-commit bash3.2 lint
- **Question**: Wire `lint-bash32.sh` into a dedicated CI job, a pre-commit hook (which propagates to CI via `make lint-only`), or both?
- **Resolution**: Pre-commit hook only. CI inherits coverage through the existing `make lint-only` job; no `.github/workflows/ci.yaml` change required.
- **Source**: user

## Decision 2: Cleanup of the `lint` Makefile umbrella
- **Question**: When the lint runs via pre-commit, should `lint-bash32` be removed from the `lint:` umbrella target dependency list to avoid double-execution from local `make lint`?
- **Resolution**: Remove `lint-bash32` from the `lint:` dependency list. The dedicated direct target `make lint-bash32` is preserved for explicit invocation.
- **Source**: user

## Decision 3: Lint scope on pre-commit (staged-only vs whole-repo)
- **Question**: Should the pre-commit hook scan the entire repo (matching the existing `lint-*` repo-wide hook pattern with `pass_filenames: false` + `always_run: true`) or scope to the staged file list (requires extending `lint-bash32.sh` to accept positional file paths)?
- **Resolution**: Incremental — scope to the staged file list. `lint-bash32.sh` must be extended to accept positional `*.sh` / `*.inc.bash` paths from pre-commit, while preserving its existing `--root PATH` mode and whole-repo default. The pre-commit hook must use `pass_filenames: true` with appropriate `types`/`files` filters so only shell files are passed.
- **Source**: user

## Hard constraints
- The existing `make lint-bash32` direct target and the existing harness `scripts/test-lint-bash32.sh` must continue to work.
- Whole-repo invocation (no positional args, or only `--root PATH`) must remain a supported mode so `make lint-bash32` keeps its current contract.
- All bash3.2-incompatible-construct detection rules and the `# lint-bash32: ok <reason>` inline suppression must be preserved.

## Non-goals
- No changes to the set of detected Bash 4+ constructs.
- No changes to `.github/workflows/ci.yaml`.
- No changes to `.markdownlint.json`, agent-lint config, or other linter wiring.
