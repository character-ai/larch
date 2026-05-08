# lib-codex-launcher-common.sh

Sourced-only helper library for Codex review launcher behavior that needs to stay in parity with the Cursor review launcher.

The canonical bodies for `codex_launcher_promote_inner_done` (which promotes `${OUTPUT}.inner.done` to `${OUTPUT}.done` only after launcher-owned post-processing has completed) and `codex_launcher_append_outer_meta` (which appends retry metadata so `collect-agent-results.sh` can replay empty-output retries through `scripts/launch-codex-review.sh`) live in `scripts/lib-external-launcher-common.sh` (issue #1502 dedup); this file sources that lib and exposes the per-tool wrapper names so existing callers in `scripts/launch-codex-review.sh` continue to work unchanged.

The library intentionally does not install traps or set shell options; callers own exit semantics.

**Edit-in-sync**: `scripts/lib-external-launcher-common.sh`, `scripts/launch-codex-review.sh`, `scripts/launch-codex-review.md`, `scripts/collect-agent-results.sh`, and `scripts/test-launch-codex-review.sh`.
