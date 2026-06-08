## Goal
Implement issue #3667: [IMPLEMENTING] sh-to-py F1: cli.py dispatcher, direct-call convention, migration playbook\n\nPart of the sh-to-py bash-to-Python migration (umbrella tracking issue links all parts; DAG, waves, and global strategy live there)..

## Implementation Plan
## Plan

F1 is the root of the sh-to-py DAG (umbrella #3692). It lands the keystone conventions every later sh-to-py issue builds on.

### Goals

- One argparse dispatcher `python/cli.py` with `<domain> <verb>` grammar, lazy domain imports, a Python 3.11 in-driver guard, exit-code passthrough, and the `lib-quiet` fd-3 KV contract preserved via `logging_util`.
- The migration playbook `docs/python-migration.md` plus a retired-scripts manifest + Python lint that fails CI on stale references to retired paths.
- Adopt `ship` and `report-tokens` as the first real domains; cut their consumers over to direct `cli.py` calls and retire the `run-analysis.sh` wrapper.

### Files to create

- `python/cli.py` — static `(domain, verb)` registry: `ship pr` → `ship.main`, `report-tokens analyze` → `report_tokens_cli.main`, `lint retired-scripts` → `migration_lint.main`. Lazy `importlib` per domain; top-level imports limited to `argparse`/`importlib`/`sys`. 3.11 guard before any domain import. `--help` lists registry without importing domains; unknown domain/verb exits 2. Exit passthrough `return int(target_main(rest_argv))` where `rest_argv` excludes both `<domain>` and `<verb>`; a delegated `SystemExit` propagates unchanged. cli.py keeps its own `__main__`; it does NOT call `quiet_init()` (subcommands own stream setup).
- `python/migration_lint.py` — `main(argv)` with `--manifest` (default `python/migrated-scripts.tsv`) and `--root` (default cwd). Parse args (and reject usage/manifest errors, exit 2) BEFORE `quiet_init()`. Enumerate tracked files via `git ls-files -z` through the `proc.py` seam. Match retired **full repo-relative paths only** (never bare basenames — live `.claude/skills/analyze-issues/scripts/run-analysis.{sh,md}` share the retired basenames). Exclusions: any `larch-logs/` segment, `CHANGELOG.md`, the manifest itself; skip binary files. Quiet-safe diagnostics through `logging_util.BreadcrumbWriter().emit()` (fd-4 parity, never raw `print(file=sys.stderr)` after `quiet_init`). A still-present manifest path is itself an error. Contract: `emit_kv` `LINT_STATUS`/`RETIRED_PATHS`/`RETIRED_REFS`; exit 0 clean, 1 on findings, 2 on usage/manifest errors.
- `python/migrated-scripts.tsv` — manifest (`path<TAB>retired_by`, `#` comments), header documents the full-path-only rule, seeded with the four retired report-tokens files.
- `python/test_cli.py` — dispatch/lazy-import/exit-passthrough units; subprocess cases derive the CLI path from `Path(__file__).with_name("cli.py")` (pytest runs from inside `python/`); fd-3 contract case (KV on stdout, chatter to quiet log, `file:line` diagnostic visible on stderr); `report-tokens analyze` quiet-env subprocess case (report body + `Cache JSON:` on stdout, scan diagnostics on stderr); ported wrapper cases (bogus `--skill`, `--plot-from`, version guard). No retired-path literals.
- `python/test_migration_lint.py` — git-fixture cases: clean tree; full-path flag; live same-basename file NOT flagged; `larch-logs/`/`CHANGELOG.md` exclusions; manifest self-reference ignored; binary skip; still-present manifest path errors; empty manifest exit 0; malformed row exit 2; KV present; failing-case `file:line` on stderr under quiet. Fixture paths built at runtime, never the seed literals.
- `docs/python-migration.md` — per-domain recipe (port → register → colocated pytest → cut ALL consumers to direct cli.py → run retargeted `test-*.sh` once as a parity gate → delete bash + harness + `.md` siblings → append to manifest → `make lint-retired-scripts`) and the decision log (no shims; hard cutover; hooks stay bash; flat layout; stdlib-only ≥3.11; cli.py is canonical entrypoint while adopted modules MAY keep `__main__` as compatibility pass-throughs; fd-3 via `quiet_init`/`contract_stream`/`emit_kv`, post-quiet human diagnostics via `BreadcrumbWriter`). Documents the manifest format, full-path-only matching, exclusions, and the no-retired-literal authoring rule — without naming retired paths.

### Files to update

- `python/logging_util.py` (+ test) — add `emit(text)` / `emit_kv(key, value)` to `contract_stream()`; `emit_kv` rejects `\n`/`\r` (`ValueError`).
- `skills/implement/SKILL.md` — selector fence `python/ship.py` → `python/cli.py ship pr` (argv unchanged); repoint the selector/critical-boundary/NEVER #13/Step 8+ opener/exit-matrix re-invoke sentences; module-role prose stays.
- `skills/implement/references/{oos-pipeline,conflict-resolution,stall-recovery}.md`, `skills/shared/subskill-invocation.md` — repoint re-invoke argv to `cli.py ship pr`.
- `scripts/test-implement-structure.sh` (+ `.md`) — update the selector-window / critical-boundary / re-invoke grep pins to the cli.py form, in the same commit as the SKILL.md edits; module-role pins (`PY_SHIP`, finalize-state, OOS decoupling) stay.
- `skills/report-tokens/SKILL.md` — invocation → `python/cli.py report-tokens analyze`; drop `run-analysis.md` / quiet-harness pointers; host the rate-override env-var docs; point to `docs/python-migration.md`.
- `Makefile` — add `lint-retired-scripts` (3.11 guard + `$(PYTHON) python/cli.py lint retired-scripts`) to `.PHONY` and the `lint:` aggregate; remove `test-run-analysis-quiet` (target, `.PHONY`, `test-harnesses-9` slot).
- `.pre-commit-config.yaml` — local `lint-retired-scripts` hook (`python3 python/cli.py lint retired-scripts`, system, `pass_filenames: false`, `always_run: true`).
- `scripts/relevant-checks.sh` (+ harness `scripts/test-relevant-checks.sh`) — report-tokens arm maps surviving triggers (`skills/report-tokens/SKILL.md`, `plot-cost-over-time.*`, `docs/run-logs.md`) to `py-test`; add `python/migrated-scripts.tsv` → `lint-retired-scripts`; rewrite the `setup_report_tokens_wrapper_repo` fixture + section 3j2 with no retired-path literals.
- `python/README.md`, `AGENTS.md`, `docs/linting.md`, `docs/installation-and-setup.md`, `docs/configuration-and-permissions.md`, `docs/workflow-lifecycle.md`, `SECURITY.md` — repoint default Step 8+ / report-tokens invocation prose to the cli.py forms (keep `python/ship.py` for module-role mentions), document `lint-retired-scripts`, drop the `test-run-analysis-quiet` row, relocate the rate-override pointer, add `docs/python-migration.md` to Canonical sources.
- `.claude/rules/gh-body-file.md` — drop the two retired report-tokens wrapper paths from `paths:`.

### Deletions (retired to the manifest)

`skills/report-tokens/scripts/run-analysis.sh`, `run-analysis.md`, `test-run-analysis-quiet.sh`, `test-run-analysis-quiet.md` (quiet-restore semantics move to `python/test_cli.py`).

### Explicitly unchanged

`python/ship.py` and `python/report_tokens_cli.py` keep their `__main__` blocks as compatibility pass-throughs (plan-review [SCOPE-REDUCTION] decision — removal would turn documented direct invocations into silent no-op imports). cli.py becomes canonical via consumer cutover + docs + lint, not by disabling module execution.

### Failure modes

1. Live /implement Step 8+ breaks at the dispatch cutover — argv after `ship pr` is byte-identical; harness pins move in the same commit.
2. Lint false positives block CI — full-path-only matching, segment exclusions, the no-retired-literal authoring rule, `file:line` diagnostics.
3. /report-tokens output visibility regresses — direct invocation has no quiet redirection to undo; subprocess pytest pins stdout/stderr visibility.

### Out-of-scope (filed)

- #3739 (blocked-by #3667) — port the `LARCH_REPORT_TOKENS_REPO` unsafe-slug rejection (exit-4) coverage from the retired wrapper harness into `python/test_cli.py`.

## Acceptance

- `python/cli.py` exists with the `(domain, verb)` registry, lazy imports, 3.11 guard, and fd-3 KV contract; `python3 python/cli.py --help` lists domains/verbs without importing domain modules; unknown domain/verb exits 2; `cli.py ship pr --help` reaches ship's parser; `cli.py report-tokens analyze --skill design --no-issue --no-plot` runs.
- `python/migration_lint.py` matches retired full paths only, applies the `larch-logs/`/`CHANGELOG.md`/manifest exclusions, emits quiet-safe `file:line` diagnostics, and exits 0/1/2 per contract.
- `docs/python-migration.md` lands with the per-domain recipe, decision log, manifest format, and no-retired-literal authoring rule.
- The four `run-analysis.sh` / `test-run-analysis-quiet.sh` files (+ `.md` siblings) are deleted and seeded into `python/migrated-scripts.tsv`; their quiet-restore semantics are covered by `python/test_cli.py`.
- All consumers (`skills/implement/**`, `skills/report-tokens/SKILL.md`, docs, `SECURITY.md`) call the cli.py invocations; `python/ship.py` / `python/report_tokens_cli.py` retain their `__main__` blocks.
- `make lint-retired-scripts` is wired into `make lint` and into `.pre-commit-config.yaml`, and is green on the final tree.
- `make py-lint`, `make py-test`, `make test-implement-structure`, and `make test-relevant-checks` are green.

diff_lines: 1340

## Test plan
(no test plan section in plan-file)
