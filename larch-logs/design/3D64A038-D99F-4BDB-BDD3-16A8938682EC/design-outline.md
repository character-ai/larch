## Proposed Design Outline

### Goals
- A failed vendor launch at ANY site leaves committed diagnostics that distinguish health-gate fast-fail vs mid-run crash vs timeout (124) vs auth vs quota.
- `execution-issues.md` error blocks are never empty when any diagnostic stream had content.
- An audit table (call site × {saved, logged, flushed}) lives in a committed `docs/` file.

### Non-goals
- No publishing of bulky raw transcripts for successful runs (preserve #3534).
- No exhaustive hand-patch of every site; centralize, then file residual gaps as OOS.
- No change to per-attempt auth/quota classification semantics.

### Approach sketch
- Centralize capture: on failure, fall back to `${OUTPUT}.diag` (and a bounded `${OUTPUT}.events.jsonl` tail) when the live sidecar is empty, via the shared `lib-failed-agent-stderr-tail.sh` source selection used by `append_launch_failure`.
- Preserve per-attempt stderr: append the outgoing sidecar to `${OUTPUT}.sidecar.history` before each `: > "$SIDECAR"` truncation; the live sidecar still holds the current attempt only.
- Health-gate fast-fail (`run-external-agent.sh`): also echo the one-line diagnosis to stderr so the sidecar is never empty on that path.
- Publish failure-only: include `*.diag` + `*.sidecar.history` for failed launches in `design-log-publish.sh`; add implement-side `larch-log-batches.sh` slugs; redact at publish.
- Audit + record: classify every vendor-agent call site, write `docs/vendor-agent-diagnostics-audit.md`, add regression coverage.

### Surfaces in scope
- `scripts/launch-review.sh`, `scripts/run-external-agent.sh`, `scripts/lib-failed-agent-stderr-tail.sh`, `scripts/append-tool-failure.sh`
- `scripts/design-log-publish.sh`, `scripts/larch-log-batches.sh`
- launcher family: `launch-codex-implement.sh`, `launch-cursor-implement.sh`, `launch-cursor-ci.sh`, `launch-codex-ci.sh`, `launch-claude-ci.sh`, `launch-claude-subprocess.sh`, `scout-dynamic-archetypes.sh`
- `docs/vendor-agent-diagnostics-audit.md` (new), sibling `.md` files, `test-*.sh` harnesses

### Open questions
- Size-bounding of the new `.sidecar.history` and committed `.diag` (cap bytes/attempts to stay #3534-aligned).
- Whether to add a bounded codex `.events.jsonl` tail as a diagnostic source, or rely on `.diag` alone.
