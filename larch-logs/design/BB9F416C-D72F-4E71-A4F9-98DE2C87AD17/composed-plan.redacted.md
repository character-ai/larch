## Plan

Wire the existing `scripts/lint-bash32.sh` into pre-commit (incremental, staged-files only) so that CI inherits coverage through the `lint` job's `make lint-only` → `pre-commit run --all-files`, and developers who have `pre-commit install` get a local commit-time gate. Keep the existing `make lint` umbrella unchanged so the whole-repo scan (which covers untracked non-ignored shell files) continues to run on local `make lint`.

### Files to modify/create

#### UPDATED: `scripts/lint-bash32.sh`

Extend argv parsing to accept positional file paths in addition to the existing `--root PATH` whole-repo mode. Behavior matrix:

- Zero positional args + no `--root` → existing whole-repo default (scans `$REPO_ROOT`).
- Zero positional args + `--root PATH` → existing harness/whole-repo mode (scans `$PATH`).
- One or more positional args (paths under `$ROOT`) → new pre-commit mode: scan only the listed paths.

Implementation:

- Add a positional accumulator in the existing `while [[ "$#" -gt 0 ]]` argv loop. Treat any non-flag token (i.e. anything not consumed by `--root`, `-h`, or `--help`) as a positional file path; push into a `FILES=()` indexed array.
- After argv parsing, branch on `${#FILES[@]}`:
  - `0` → fall through to the existing `list_shell_files` + `scan_file` loop (default and `--root` modes).
  - `>0` → bypass `list_shell_files`; iterate the supplied paths. For each entry:
    - Reject if it does not match `\.(sh|inc\.bash)$` — print `lint-bash32: skipping non-shell path: <path>` to stderr (not a violation) and continue.
    - Convert the path to a path relative to `$ROOT`. The positional path is treated as repo-relative when it is not absolute, and is converted from absolute to relative form when it is absolute and inside `$ROOT`. If a positional path is absolute and outside `$ROOT`, print `lint-bash32: skipping path outside lint root: <path>` to stderr and continue. This preserves the existing `scan_file` contract that reads `$ROOT/$rel` and reports `<rel>` in violation messages; no `scan_file` edit is required and no "outside-root" code path is introduced.
    - Call the existing `scan_file <rel>` (its built-in `[[ -f "$path" && ! -L "$path" ]]` guard silently skips directories and symlinks).
- Preserve the existing trap-on-EXIT temp cleanup, the exit codes (0 clean, 1 violation, 2 usage), and every awk rule pattern.
- The interface remains Bash 3.2-compatible: no associative arrays, no namerefs, no `mapfile`/`readarray`, no parameter case conversion. The positional accumulator uses a plain indexed array (`FILES=()`).

#### UPDATED: `scripts/lint-bash32.md`

Document the new positional-file mode and the pre-commit caller:

- Add a paragraph describing positional `*.sh` / `*.inc.bash` paths as a third mode alongside the default whole-repo scan and `--root PATH`. State the path-resolution rule: positional paths are interpreted relative to `$ROOT`; absolute paths inside `$ROOT` are converted to relative paths; absolute paths outside `$ROOT` are skipped with a warning.
- Note that pre-commit (via the new `lint-bash32` hook) is now a primary caller alongside `make lint-bash32` and the `make lint` umbrella.
- Update the "Edit in sync" list to include `.pre-commit-config.yaml` and `docs/linting.md`.

#### UPDATED: `scripts/test-lint-bash32.sh`

Add new regression cases for the positional-file mode while preserving every existing `--root` case unchanged:

1. **positional clean (`.sh`)** — invoke `(cd "$TMPROOT" && bash "$LINT" --root "$TMPROOT" scripts/good.sh)` against a clean `.sh` fixture under `$TMPROOT/scripts/`; assert exit 0 with empty stderr.
2. **positional with violation (`.sh`)** — invoke `(cd "$TMPROOT" && bash "$LINT" --root "$TMPROOT" scripts/bad-unsuppressed.sh)` against a `.sh` fixture under `$TMPROOT/scripts/` containing the same multi-rule violation set as the existing `forbidden constructs` case; assert exit 1 and that stderr contains the expected violation strings. Additionally place a sibling `bad-unsuppressed-2.sh` in the same tree that is NOT passed positionally and confirm it is not flagged (proves positional mode scopes to argv, not whole-tree).
3. **positional with violation (`.inc.bash`)** — invoke `(cd "$TMPROOT" && bash "$LINT" --root "$TMPROOT" scripts/helper-bad.inc.bash)` against an `.inc.bash` fixture under `$TMPROOT/scripts/` (reuse the existing `inc.bash extension is scanned` fixture pattern). Assert exit 1 and that stderr contains `scripts/helper-bad.inc.bash` and `declare -A associative arrays`. This is the positional-mode counterpart to the existing whole-root `.inc.bash` case.
4. **positional skip non-shell** — invoke `(cd "$TMPROOT" && bash "$LINT" --root "$TMPROOT" scripts/good.sh notes.md)` with a `.md` path mixed into the positional list; assert exit 0 and that stderr contains the expected `lint-bash32: skipping non-shell path: notes.md` line for the `.md` file.
5. **positional skip outside-root** — invoke `(cd "$TMPROOT" && bash "$LINT" --root "$TMPROOT" /tmp/foo.sh)` with a path that is absolute and outside `$TMPROOT`; assert exit 0 and that stderr contains the expected `lint-bash32: skipping path outside lint root:` line.

All new cases use `--root "$TMPROOT"` with repo-relative positional paths so the existing `scan_file <rel>` contract is preserved; no outside-root scan-file code path is exercised. Refactor `run_lint` to forward extra argv (or introduce a second helper `run_lint_positional`) while keeping the existing signature of `run_lint` callable for the existing `--root`-only cases.

#### UPDATED: `.pre-commit-config.yaml`

Insert a new `local` repo hook block. Recommended position: between the existing `lint-no-raw-stderr-after-quiet-init` block and the `check-topology-rule-paths` block, preserving alphabetical-ish proximity to other `lint-*` hooks. Hook definition:

```yaml
- id: lint-bash32
  name: Lint Bash 3.2 portability of shell scripts
  entry: bash scripts/lint-bash32.sh
  language: system
  files: \.(sh|inc\.bash)$
  pass_filenames: true
```

Rationale for fields:

- `files: \.(sh|inc\.bash)$` — covers both extensions explicitly, avoiding reliance on pre-commit's `identify` shell-type detection (which may not auto-classify `.inc.bash`).
- `pass_filenames: true` — pre-commit passes the staged file list as positional argv to the entry, exercising the new positional mode in `lint-bash32.sh`.
- No `additional_dependencies` — the script is pure bash + awk; no Python deps needed.
- No `always_run` / `pass_filenames: false` — this hook is intentionally incremental.

#### UPDATED: `Makefile`

The existing `lint:` umbrella target dependency list is unchanged:

```
lint: test-harnesses lint-bash32 lint-foreground-markers lint-readability-preamble lint-only
```

`lint-bash32` remains in the umbrella so local `make lint` continues to cover untracked non-ignored shell files (the existing direct invocation uses `git ls-files --cached --others --exclude-standard`, which is broader than `pre-commit run --all-files`'s tracked-only scope). The small redundant local run after `lint-only` is acceptable — the script is fast and idempotent. The direct `lint-bash32:` target is also unchanged.

#### UPDATED: `docs/linting.md`

Two narrative updates to keep canonical linting docs in sync:

1. **Bash 3.2 portability row** (the table row that lists `scripts/lint-bash32.sh`): update the description to mention the new pre-commit hook. New text mentions: `Wired as the lint-bash32 pre-commit hook (incremental, staged-files only via positional argv); also runs whole-repo via make lint-bash32 (untracked-aware) and local make lint.`
2. **CI/local lint paragraph** (the paragraph describing `make lint-only`, `make lint`, and reviewer/CI wiring): update the sentence describing `Local make lint also runs make lint-bash32 ...` to reflect that `lint-bash32` now also runs as a pre-commit hook under `make lint-only` / CI / `relevant-checks.sh`, while `make lint-bash32` remains the explicit whole-repo (untracked-aware) target.

### Approach

Pre-commit propagation is the smallest single-source wiring: the existing `lint` job in `.github/workflows/ci.yaml` already runs `make lint-only` → `pre-commit run --all-files`, so a new pre-commit hook automatically enters CI without any workflow edit. The incremental (staged-files) scope is implemented by extending `lint-bash32.sh` to accept positional paths under `$ROOT`, which is the only file-list mechanism pre-commit offers without inventing a wrapper.

The existing `--root PATH` mode is preserved because the regression harness depends on it. The new positional mode is scoped to paths under `$ROOT` so the existing `scan_file <rel>` contract is preserved verbatim. The `make lint` umbrella is left unchanged so local developers retain whole-repo coverage of untracked non-ignored shell files (a small redundant local run after `lint-only` is acceptable — the script is fast and idempotent).

Key trade-off resolution: the staged-files-only pre-commit mode catches violations in files the developer touched, but does NOT catch a pre-existing violation in an unmodified file. The `make lint-bash32` direct target and the local `make lint` umbrella both retain whole-repo coverage; CI's whole-tree gate is provided by the pre-commit hook scoped to all changed files in a PR.

### Edge cases

- **Pre-commit invokes the hook with zero file arguments** (`files:` regex matches nothing in the commit): pre-commit's default behavior is to skip the hook entirely. The script's positional branch never runs and there is no surprise exit code.
- **Pre-commit passes paths relative to the repo root**: confirmed by inspection of other hooks. The new positional branch resolves relative paths against `$ROOT` (which defaults to `$REPO_ROOT`).
- **Files outside `$ROOT`**: practically unreachable through pre-commit. Defensive guard prints a `skipping path outside lint root:` warning and continues, so the script never scans paths the harness contract did not include.
- **Pre-existing violations in unmodified files**: not caught by the incremental pre-commit hook. The `make lint-bash32` direct target and the `make lint` umbrella remain as the whole-repo safety net.
- **Symlinks in the staged list**: silently skipped by the existing `[[ -f "$path" && ! -L "$path" ]]` guard inside `scan_file`. No behavior change.
- **`# lint-bash32: ok <reason>` inline suppression**: behavior unchanged; the awk pattern that recognizes it is per-line and orthogonal to the file-enumeration mode.

### Failure modes

1. **`*.inc.bash` silently skipped by pre-commit**: if the `files:` regex is wrong or pre-commit's path-encoding differs from what we assume, `*.inc.bash` files would skip the hook. Earliest signal: the new harness `positional with violation (.inc.bash)` case fails, or the `bash scripts/lint-bash32.sh --root "$TMPROOT" scripts/helper-bad.inc.bash` direct invocation fails to flag the fixture. Mitigation: dedicated positional `.inc.bash` harness case, and the `files:` regex uses an explicit alternation `\.(sh|inc\.bash)$`.
2. **Regression in `make lint-bash32` direct target**: argv-parsing changes could accidentally break the whole-repo default. Earliest signal: the existing `clean Bash 3.2 script` or `forbidden constructs` harness cases fail under `--root TMPROOT`. Mitigation: the harness retains every existing `--root`-mode case unchanged; argv parsing keeps zero-positional + no-`--root` as the existing default.
3. **Stale `docs/linting.md`**: failing to update the canonical linting reference would leave developers and reviewers reading an outdated CI/local wiring narrative. Earliest signal: a contributor reads `docs/linting.md` after this PR lands and finds the Bash 3.2 row describing only `make lint-bash32` and `make lint`, with no mention of the pre-commit hook. Mitigation: the explicit `docs/linting.md` updates above.

### Testing strategy

- Update `scripts/test-lint-bash32.sh` to cover five new positional-mode cases (clean `.sh`, violation `.sh`, violation `.inc.bash`, non-shell skip, outside-root skip) plus retain every existing `--root`-mode case unchanged. Verify the harness exits 0 locally via `bash scripts/test-lint-bash32.sh` and via `make test-lint-bash32`.
- Run `pre-commit run lint-bash32 --files scripts/lint-bash32.sh` locally to confirm the new hook is wired and emits no violations on clean input.
- Run `pre-commit run --all-files` to confirm no incidental regression in other hooks.
- Stage a temporary `.inc.bash` fixture with a `declare -A` violation, run `pre-commit run --files <fixture>`, confirm the hook blocks the commit. Revert the fixture.
- Run `make lint` locally to confirm the umbrella still passes (and confirms the `lint-bash32` + `lint-only` ordering is functional).

## Acceptance

The implementation is complete when ALL of the following are observably true on the feature branch and confirmed in CI:

1. **Pre-commit hook present**: `.pre-commit-config.yaml` contains a `lint-bash32` hook block matching the specification above (`entry: bash scripts/lint-bash32.sh`, `language: system`, `files: \.(sh|inc\.bash)$`, `pass_filenames: true`).
2. **Positional argv supported in `lint-bash32.sh`**: invoking `bash scripts/lint-bash32.sh --root <ROOT> path/under/root.sh` scans only the named file; invoking with multiple positional paths scans only those files; non-`*.sh` / `*.inc.bash` paths produce the `skipping non-shell path:` stderr warning and exit 0; absolute paths outside `$ROOT` produce the `skipping path outside lint root:` warning and exit 0.
3. **Backwards compatibility preserved**: `bash scripts/lint-bash32.sh` (no args) and `bash scripts/lint-bash32.sh --root <PATH>` both still produce identical exit codes and stderr output as before this change for any input that previously passed or failed.
4. **Harness updated**: `scripts/test-lint-bash32.sh` contains five new positional-mode cases (clean `.sh`, violation `.sh` + sibling-not-scanned proof, violation `.inc.bash`, non-shell skip, outside-root skip) and all existing `--root`-mode cases continue to pass. `make test-lint-bash32` exits 0.
5. **CI propagation**: a CI run on the feature branch shows the `lint-bash32` hook executed inside the `lint` job (visible in `pre-commit run --all-files` output). The hook is NOT in the `SKIP=...` env list of the `lint` job.
6. **Documentation in sync**: `scripts/lint-bash32.md` and `docs/linting.md` both reflect the new pre-commit-hook caller. `scripts/lint-bash32.md`'s `Edit in sync` list includes `.pre-commit-config.yaml` and `docs/linting.md`.
7. **Local commit-time gate verified**: staging a Bash 4+ violation in a `.sh` or `.inc.bash` file under `pre-commit install` triggers the hook and fails the commit with the expected `lint-bash32:` stderr message.
8. **Makefile unchanged**: the `lint:` umbrella still chains `lint-bash32`, and the direct `lint-bash32:` target still scans the whole repo. `make lint` runs to completion locally (a small duplicate `lint-bash32` run between `lint-only` and the umbrella is accepted).

diff_lines: 114
