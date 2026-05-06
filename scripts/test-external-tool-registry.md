# scripts/test-external-tool-registry.sh - contract

Regression harness for `scripts/external-tool-registry.sh` and its consumers.

## Purpose

Pins the canonical external-tool taxonomy (`codex cursor gemini`), implementer-coder taxonomy (`claude codex cursor gemini`), predicate behavior, formatter output, source-time safety, and consumer consistency.

## Invariants

- The harness anchors paths through `REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"` so it can run from any cwd.
- The registry can be sourced once or twice without stdout, stderr, shell-option mutation, or readonly collisions.
- `claude` remains an implementer-only coder and is not an external tool.
- `check-reviewers.sh --include-gemini` emits an availability key for every registered external tool and does not hit an unsupported-tool defensive arm.
- `agent-model-args.sh --tool <T>` returns non-empty stdout for every registered external tool and does not hit its `*)` defensive arm — catches drift where the registry grows but a per-tool model `case` arm is forgotten (without coverage the script would silently exit 0 with empty stdout, leaving callers to launch probes with no `--model`).
- `step2-implement.sh --coder claude` resolves the registry from a non-repo cwd and returns `STATUS=claude_fallback`.

## Makefile wiring

Target: `make test-external-tool-registry`. A `make lint` prerequisite via `the test-harnesses-N shard partition`.

## Edit-in-sync

Update this harness with any change to `scripts/external-tool-registry.sh`, the registry's public API, sourced consumers, or Makefile shard wiring.
