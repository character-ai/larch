## Proposed Design Outline

### Goals
- Add a repo-wide structural backstop that fails CI / pre-commit when a `.sh` or `.py` file uses inline `gh ... --body` or `gh ... --notes`, independent of whether the file is listed in `.claude/rules/gh-body-file.md`'s `paths:` frontmatter.
- Provide a clearly-documented inline escape hatch for legitimate fixture/test lines.

### Non-goals
- Do NOT modify `.claude/rules/gh-body-file.md`'s `paths:` frontmatter or its scope.
- Do NOT change any existing `--body-file` callers, rewrite any test stubs, or extend coverage to `.md`, `.yaml`, or `.yml` files.
- Do NOT extend agent-lint upstream or change `agent-lint.toml`.
- Do NOT add multi-line backslash-continuation awareness in v1; line-based regex is sufficient for every known forbidden pattern in the rule.

### Approach sketch
- One bash linter script under `scripts/` that walks `.sh`/`.py` in the repo (honoring `.git`/`larch-logs/` skips like sibling lints) and matches inline `gh ... --body` / `gh ... --notes` on a single line.
- Inline allow-comment suppression mirroring `# lint-bash32: ok <reason>` / `# lint-foreground-markers: ok <reason>`.
- Pre-commit local hook registration in `.pre-commit-config.yaml` with `pass_filenames: false, always_run: true, files: \.(sh|py)$` (matches `lint-no-raw-stderr-after-quiet-init` shape).
- Makefile target + sibling `.md` contract + regression harness `test-lint-gh-body-inline.sh` + sibling `.md`.

### Surfaces in scope
- `scripts/lint-gh-body-inline.sh` (NEW)
- `scripts/lint-gh-body-inline.md` (NEW, sibling contract per `script-md-siblings.md`)
- `scripts/test-lint-gh-body-inline.sh` (NEW, regression harness)
- `scripts/test-lint-gh-body-inline.md` (NEW, sibling)
- `.pre-commit-config.yaml` (UPDATED — add `lint-gh-body-inline` local hook)
- `Makefile` (UPDATED — add `lint-gh-body-inline` target, optionally wire into aggregate `lint-only`/`lint`)
- `docs/linting.md` (UPDATED — register the new linter in the catalog, if other lints are listed there)
- Up to 9 existing `.sh` lines (gh-stub harness assertions) annotated with inline `# lint-gh-body-inline: ok <reason>` to clear the false-positive surface

### Open questions
- None.
