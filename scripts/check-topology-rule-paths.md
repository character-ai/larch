# scripts/check-topology-rule-paths.py - contract

`scripts/check-topology-rule-paths.py` enforces that every distinct runtime authority in column 4 of `skills/shared/topology.tsv` is listed literally in `.claude/rules/topology-generation.md` frontmatter `paths:`.

## Purpose And Callers

Primary callers are the `agent-sync` job in `.github/workflows/ci.yaml`, the local `check-topology-rule-paths` pre-commit hook, the offline harness `scripts/test-check-topology-rule-paths.sh`, and manual local runs via `python3 scripts/check-topology-rule-paths.py`.

## Invariants

- Runs under Python 3 with PyYAML 6.0.2 supplied by `.github/workflows/requirements-lint.txt` in CI and `.pre-commit-config.yaml` locally.
- Resolves `REPO_ROOT` from the script's own path, so caller cwd does not affect canonical inputs.
- Reads both canonical inputs with `newline=""` so CRLF is visible and rejected.
- Parses `.claude/rules/topology-generation.md` frontmatter with `yaml.safe_load`; this avoids unsafe Python object construction but resolves anchors, aliases, and merge keys before validation.
- Requires frontmatter `paths` to be a `list[str]`.
- Validates TSV row shape, rejects CRLF, requires non-empty columns 1, 2, and 4, and allows an empty column 3.
- Validates TSV runtime-authority path grammar with the same repo-relative checks as `scripts/generate-topology-docs.sh::validate_repo_path`, plus an explicit leading/trailing whitespace rejection and a resolved-path containment check so symlink escapes cannot leave the repo root.
- Performs a one-directional subset check: `skills/shared/topology.tsv` runtime authorities must be contained in rule `paths`; extra rule paths are allowed.
- Rejects an empty TSV with no data rows.
- Exits 0 silently on success and exits 1 with stderr diagnostics on any error.

## YAML Shape Contract

The rule's `paths:` may use block-list YAML or flow-style YAML; both are parsed by `yaml.safe_load`. Glob entries are not expanded or interpreted. Coverage is literal string equality only, so future glob support must be added deliberately in this script and its harness.

## No Env Overrides

The script accepts no positional arguments and no environment-variable overrides. Test fixtures use a copy-into-temp-tree pattern so the script's own-path repo-root resolution remains the exercised contract.

## Makefile Wiring

Target: `make test-check-topology-rule-paths`. A `make lint` prerequisite via `test-harnesses-4`; `test-harness-shards-coverage` validates shard membership.

## Edit In Sync

Changes to validation grammar or the YAML-shape contract must update `scripts/test-check-topology-rule-paths.sh` fixtures in the same PR. Changes to Makefile shard wiring must update `docs/linting.md`. Changes to the PyYAML pin must update `.pre-commit-config.yaml`, `.github/workflows/requirements-lint.txt`, and that file's comment.
