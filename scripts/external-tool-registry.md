# scripts/external-tool-registry.sh - contract

## Purpose

Single canonical source for external-tool name taxonomy and implementer-coder taxonomy.

## Sourced by

- `scripts/agent-model-args.sh`
- `scripts/check-reviewers.sh`
- `scripts/collect-agent-results.sh`
- `skills/implement/scripts/step2-implement.sh`

Update this list whenever a new consumer sources the registry.

## Related

`scripts/run-external-agent.sh` is NOT sourced from this registry and still does not validate `--tool` against it, per DECISION_1 of #1099. The human-facing log keeps the raw label, while the `.meta` `TOOL=` sidecar field is sanitized at write time through a label-safe allowlist (alphanumerics, `.`, `_`, `-`); disallowed bytes are translated to `_` (length-preserved), and an empty sanitized result falls back to `sanitized-empty`. See `scripts/run-external-agent.md` for the full sanitization contract.

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

If a consumer registers a tool in `LARCH_EXTERNAL_TOOLS` but a `case` in `agent-model-args.sh` or a switch helper in `check-reviewers.sh` does not handle it, the consumer exits via the defensive `*)` arm with `internal error: unsupported reviewer tool: <id>`. Test #14 in `test-external-tool-registry.sh` walks every registry entry through `check-reviewers.sh` to catch this at lint time. `scripts/collect-agent-results.sh` derives `TOOL=` labels from `LARCH_EXTERNAL_TOOLS`, but its health helper state and `--write-health` output remain explicit `CODEX_HEALTHY`, `CURSOR_HEALTHY`, and `GEMINI_HEALTHY` fields; adding health fields for a future tool is a separate collector contract change.

## Non-goals

Per-tool model defaults stay in `agent-model-args.sh` for Codex and Cursor; for Gemini, `agent-model-args.sh`'s gemini arm defines the canonical env-precedence chain mirrored by `scripts/lib-gemini-model-resolver.sh` so the Gemini launch/probe sites (`launch-gemini-implement.sh`, `launch-gemini-review.sh`, `check-reviewers.sh`) can pass the model as a single quoted argv token — the helper and `agent-model-args.sh` gemini arm must stay in lockstep when env names, plugin fallbacks, or the hardcoded default change. Probe argv templates stay in `check-reviewers.sh`; launcher paths, agent-prompt paths, runtime-failure tokens, and `REQUIRES_HEAD_UNCHANGED` policy stay in `step2-implement.sh`; capture-mode policy and metadata writes stay in `run-external-agent.sh`.

## Adding a new external tool

1. Append the new id to `LARCH_EXTERNAL_TOOLS` and to `LARCH_IMPLEMENTER_CODERS` if it is also an implementer.
2. Add the per-tool branch in `agent-model-args.sh`.
3. Add the per-tool branch in `check-reviewers.sh` `start_probe` and in every switch helper (`get_available`, `get_healthy`, `set_healthy`, `get_skip`, `set_probe_error`, `get_probe_error`); decide opt-in vs. default and update `--include-*` policy accordingly.
4. If the new tool is also an implementer, add the launcher branch in `step2-implement.sh`.
5. No change is required in `run-external-agent.sh`: it sanitizes `.meta` `TOOL=` for any input. Prefer a label-safe id (alphanumerics, `.`, `_`, `-`) so `.meta` `TOOL=` matches the registry id verbatim; non-label-safe ids may still collide after sanitization (e.g. `tool/a` and `tool?a` both become `tool_a`), so `.meta` `TOOL=` is not a bijection from arbitrary labels. Only widen the wrapper's allowlist if you intentionally change that contract.
6. If the new tool produces output collected by `scripts/collect-agent-results.sh`, extend the collector's health envelope (`get_tool_healthy`, `set_tool_unhealthy`, the `--write-health` output) to include the new id; without this step, failures on the new tool's outputs are silently dropped from the per-tool monotonic-health state. See the Collector integration section below.
7. Update the relevant sibling `.md` contracts.
8. Run `make lint` and `/relevant-checks`.

## Collector integration

`scripts/collect-agent-results.sh` sources this registry and uses `LARCH_EXTERNAL_TOOLS` for both `.meta` `TOOL=` validation and basename inference. The collector deliberately keeps an `unknown` fallback for observational classification of partial or malformed launches, which is semantically different from dispatch validation and is not a registry member.

## Tests

`scripts/test-external-tool-registry.sh` covers registry contents, predicates, brace formatting, source-time side effects, consumer consistency, and nested-cwd step2 path resolution.

## CI wiring

Target: `make test-external-tool-registry`. A `make lint` prerequisite via `the test-harnesses-N shard partition`. Also documented in `docs/linting.md`.
