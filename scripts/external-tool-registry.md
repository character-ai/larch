# scripts/external-tool-registry.sh - contract

## Purpose

Single canonical source for external-tool name taxonomy and implementer-coder taxonomy.

## Sourced by

- `scripts/larch.sh agent model-args`
- `scripts/larch.sh agent check-reviewers`
- `scripts/larch.sh agent collect-results`
- `scripts/larch.sh implement step2-dispatch`

Update this list whenever a new consumer sources the registry.

## Related

`scripts/larch.sh agent run-external-agent` is NOT sourced from this registry and still does not validate `--tool` against it, per DECISION_1 of #1099. The human-facing log keeps the raw label, while the `.meta` `TOOL=` sidecar field is sanitized at write time through a label-safe allowlist (alphanumerics, `.`, `_`, `-`); disallowed bytes are translated to `_` (length-preserved), and an empty sanitized result falls back to `sanitized-empty`. See `crates/larch-core/src/vendor/external_agent.rs` for the full sanitization contract.

## Public API

- `LARCH_EXTERNAL_TOOLS`
- `LARCH_IMPLEMENTER_CODERS`
- `larch_is_external_tool`
- `larch_is_implementer_coder`
- `larch_external_tools_braced`
- `larch_implementer_coders_braced`

## Invariants

- `# shellcheck shell=bash` is the first content line.
- The library has no stdout/stderr while the file is being sourced. Formatter functions (`larch_external_tools_braced`, `larch_implementer_coders_braced`) intentionally print to stdout when called by consumers.
- No `set -e`, `set -u`, or `set -o pipefail` mutation; no `exit`; no I/O on source.
- Bash 3.2-compatible: no associative arrays, namerefs, mapfile/readarray, or eval.
- `claude` is an implementer-only coder; it MUST NOT appear in `LARCH_EXTERNAL_TOOLS`. Step2's `TOOL=` envelope-line contract continues to mean external implementer only.
- Re-source is idempotent via the `LARCH_EXTERNAL_TOOL_REGISTRY_LOADED` sentinel, set as the final line of the library so "loaded" implies "fully initialized."

## Failure symptoms

## Non-goals

Per-tool model defaults and plugin `userConfig` environment variables stay in `python/agents.py`; this shell registry only names tool taxonomy.

## Adding a new external tool

1. Append the new id to `LARCH_EXTERNAL_TOOLS` and to `LARCH_IMPLEMENTER_CODERS` if it is also an implementer.
2. Add the per-tool branch in `python3 scripts/larch.sh agent model-args`.
3. Add the per-tool branch in `agent check-reviewers` presence detection and in any dispatcher fallback helpers; decide opt-in vs. default and update `--include-*` policy accordingly.
4. If the new tool is also an implementer, add the launcher branch in `implement step2-dispatch`.
5. No change is required for `scripts/larch.sh agent run-external-agent`'s raw `--tool` label: it sanitizes `.meta` `TOOL=` for any input. Prefer a label-safe id (alphanumerics, `.`, `_`, `-`) so `.meta` `TOOL=` matches the registry id verbatim; non-label-safe ids may still collide after sanitization (e.g. `tool/a` and `tool?a` both become `tool_a`), so `.meta` `TOOL=` is not a bijection from arbitrary labels. Direct execution remains closed to approved typed vendor programs; add an explicit process-port variant before a new vendor executable can launch.
6. If the new tool produces output collected by `scripts/larch.sh agent collect-results`, ensure its tool derivation can classify the new id from metadata and filenames so dispatcher fallback can attribute results.
7. Update the relevant sibling `.md` contracts.
8. Run `make lint` and `scripts/larch.sh checks run-relevant --site local --tmpdir "${TMPDIR:-/tmp}"`.

## Collector integration

`scripts/larch.sh agent collect-results` uses the same external-tool allowlist exposed by `scripts/larch.sh agent external-tool-registry --kind external-tools` for both `.meta` `TOOL=` validation and basename inference. The collector deliberately keeps an `unknown` fallback for observational classification of partial or malformed launches, which is semantically different from dispatch validation and is not a registry member.

## Tests

`scripts/test-external-tool-registry.sh` covers registry contents, predicates, brace formatting, source-time side effects, consumer consistency, and nested-cwd step2 path resolution.

## CI wiring

Target: `make test-external-tool-registry`. A `make lint` prerequisite via `the test-harnesses-N shard partition`. Also documented in `docs/linting.md`.
