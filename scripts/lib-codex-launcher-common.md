# lib-codex-launcher-common.sh

Sourced-only helper library for Codex review launcher behavior that needs to stay in parity with the Cursor review launcher.

The canonical bodies for `codex_launcher_promote_inner_done` (which promotes `${OUTPUT}.inner.done` to `${OUTPUT}.done` only after launcher-owned post-processing has completed) and `codex_launcher_append_outer_meta` (which appends retry metadata so `collect-agent-results.sh` can replay empty-output retries through `scripts/launch-review.sh --tool codex`) live in `scripts/lib-external-launcher-common.sh` (issue #1502 dedup); this file sources that lib and exposes the per-tool wrapper names so existing callers in `scripts/launch-review.sh --tool codex` continue to work unchanged.

`codex_launcher_record_usage_from_events` is the matching thin wrapper around
`external_launcher_record_usage_from_events`. It parses `${OUTPUT}.events.jsonl`
through [scripts/parse-codex-usage.md](parse-codex-usage.md), appends
fail-closed parser diagnostics to the sidecar when parsing fails, and otherwise
either writes a `TOOL=codex` token-record sidecar or records a `vendor=codex`
ledger row depending on whether the optional fifth argument is present.

## Codex stdin contract

All background Codex spawns inherit `/dev/null` as stdin at the actual spawn site in [scripts/run-external-agent.sh](run-external-agent.md), across the default, `--capture-stdout`, and `--capture-stdout-only` branches. This Codex-named launcher layer documents the contract so future Codex callers do not accidentally add an interactive stdin dependency while using the shared background wrapper.

The library intentionally does not install traps or set shell options; callers own exit semantics.

**Edit-in-sync**: `scripts/lib-external-launcher-common.sh`, `scripts/launch-review.sh --tool codex`, `scripts/launch-review.md`, `scripts/collect-agent-results.sh`, and `scripts/test-launch-review.sh`.
