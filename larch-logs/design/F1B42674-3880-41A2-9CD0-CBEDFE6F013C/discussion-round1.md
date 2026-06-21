## Decision 1: Move all six — no standalone exception
- **Question**: Must any of the six scripts stay standalone (the issue's flagged bootstrapping question)?
- **Resolution**: No. All six move into `python/` behind `cli.py`. The only technical blocker (check-topology's third-party `yaml` import) is removed by de-yaml'ing it first (Decision 2). There is no genuine bootstrap-ordering blocker: pre-commit/CI/Makefile callers can invoke `python3 python/cli.py lint <verb>` directly; `cli.py` lazy-imports verb modules so no linter participates in `cli.py` startup.
- **Source**: user + codebase

## Decision 2: check-topology-rule-paths.py — de-yaml, then move
- **Question**: How to reconcile `check-topology-rule-paths.py`'s `import yaml` with the stdlib-only `python/` runtime (enforced by `python/test_stdlib_only.py`, which imports every `python/*.py`; pyyaml is dev/CI-only)?
- **Resolution**: Replace `yaml.safe_load(frontmatter)` with a stdlib parse of the simple `paths:` quoted block list, then move it to `python/` behind `cli.py lint topology-rule-paths` like the rest. Removes the repo's last yaml consumer. The existing `test-check-topology-rule-paths.sh` harness is the parity gate before deletion.
- **Source**: user

## Decision 3: Linter test-*.sh harnesses — port to pytest, delete
- **Question**: How to handle the three linter `scripts/test-*.sh` regression harnesses once the linters move behind cli.py?
- **Resolution**: Port each to colocated `python/test_lint_*.py` pytest (established pattern, e.g. `test_lint_codex_exec_auth.py`), run the old harness once as a parity gate, then delete the bash harness + its `.md` sibling. Matches the migration playbook (steps 3, 5, 6).
- **Source**: user

## Decision 4 (hard constraint): Behavior identical
- **Question**: What must not break?
- **Resolution**: Each script's observable behavior (exit codes, stdout/stderr, file effects, default `--root`/args) must stay identical after relocation — except check-topology's internal frontmatter parser, which must reproduce pyyaml's result for the `paths:` block list. `render-session-transcript` is invoked as a subprocess from `python/run_logs.py` (`_RENDER_TRANSCRIPT`, with stderr capture for redaction); preserve that subprocess+stderr boundary by repointing it to the cli.py verb rather than switching to an in-process call.
- **Source**: codebase / issue

## Decision 5 (scope boundary): Exactly six files + repoint callers; no opportunistic cleanup
- **Question**: In-scope vs out-of-scope?
- **Resolution**: In-scope: relocate the six scripts to `python/` modules + `cli.py` verbs, repoint every caller (Makefile, `.pre-commit-config.yaml`, `.github/workflows/ci.yaml`, docs, `python/run_logs.py`, `agent-lint.toml`), move/port the `.md` siblings and the three linter harnesses, record deleted paths in `python/migrated-scripts.tsv` with `#4974`, keep `make lint` / `py-lint` / `py-test` green, leave no stale references (`make lint-retired-scripts`). Out-of-scope: any adjacent refactor, new test coverage for the three previously-untested utilities (`cleanup-implement-logs`, `render-session-transcript`, `retro-v3-sweep`), or behavior changes. Minimum change.
- **Source**: codebase / issue
