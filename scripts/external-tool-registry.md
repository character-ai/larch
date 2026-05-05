# scripts/external-tool-registry.sh - contract

## Purpose

Single canonical source for external-tool name taxonomy and implementer-coder taxonomy.

## Sourced by

- `scripts/agent-model-args.sh`
- `scripts/check-reviewers.sh`
- `skills/implement/scripts/step2-implement.sh`

Update this list whenever a new consumer sources the registry.

## Related

`scripts/run-external-agent.sh` is a label-only consumer and is NOT sourced. It aligns to this registry via a header comment per DECISION_1 of #1099. The wrapper accepts any `--tool` label without validation by design.

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

If a consumer registers a tool in `LARCH_EXTERNAL_TOOLS` but a `case` in `agent-model-args.sh` or a switch helper in `check-reviewers.sh` does not handle it, the consumer exits via the defensive `*)` arm with `internal error: unsupported reviewer tool: <id>`. Test #14 in `test-external-tool-registry.sh` walks every registry entry through `check-reviewers.sh` to catch this at lint time.

## Non-goals

Per-tool model defaults stay in `agent-model-args.sh`; probe argv templates stay in `check-reviewers.sh`; launcher paths, agent-prompt paths, runtime-failure tokens, and `REQUIRES_HEAD_UNCHANGED` policy stay in `step2-implement.sh`; capture-mode policy and metadata writes stay in `run-external-agent.sh`.

## Adding a new external tool

1. Append the new id to `LARCH_EXTERNAL_TOOLS` and to `LARCH_IMPLEMENTER_CODERS` if it is also an implementer.
2. Add the per-tool branch in `agent-model-args.sh`.
3. Add the per-tool branch in `check-reviewers.sh` `start_probe` and in every switch helper (`get_available`, `get_healthy`, `set_healthy`, `get_skip`, `set_probe_error`, `get_probe_error`); decide opt-in vs. default and update `--include-*` policy accordingly.
4. If the new tool is also an implementer, add the launcher branch in `step2-implement.sh`.
5. No change is required in `run-external-agent.sh` because it is label-only.
6. Update the relevant sibling `.md` contracts.
7. Run `make lint` and `/relevant-checks`.

## Known follow-up drift point

`scripts/collect-agent-results.sh` `derive_tool()` re-encodes the `codex|cursor|gemini` enum with a fourth `unknown` classification at `scripts/collect-agent-results.sh:106-118`. That collector deliberately keeps an `unknown` fallback for observational classification of partial or malformed launches, which is semantically different from dispatch validation. Tracked as a deferred follow-up via the OOS_2 issue filed by `/implement` after this PR.

## Tests

`scripts/test-external-tool-registry.sh` covers registry contents, predicates, brace formatting, source-time side effects, consumer consistency, and nested-cwd step2 path resolution.

## CI wiring

Target: `make test-external-tool-registry`. A `make lint` prerequisite via `test-harnesses-5`. Also documented in `docs/linting.md`.
