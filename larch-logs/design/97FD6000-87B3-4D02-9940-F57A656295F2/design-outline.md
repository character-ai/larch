## Proposed Design Outline

### Goals
- Make `render specialist --competition-notice --competition-notice-file` payload-byte accounting include the inlined notice file's bytes, so `measure-panel-cost` scaffold/payload split reflects reality.
- Keep the fix mechanical: mirror the existing counting pattern already used for `feature_file` / `plan_file`.

### Non-goals
- Not changing the static "Competition notice" boilerplate paragraph (stays scaffold — it is stable per run, not per-run content).
- Not touching `measure-panel-cost` aggregation logic; it already trusts the `payload_bytes` column it's given.
- Not changing plan-review or voter rendering (they never receive `--competition-notice`).

### Approach sketch
- Extend `_specialist_payload_bytes()` in `python/larch/rendering/rendering.py` to add `competition_notice_file` raw bytes via the existing `_file_payload_bytes()` helper, gated on `args.competition_notice and args.competition_notice_file` (the same condition under which `_render_specialist_text()` inlines the file).
- Count raw file bytes only, consistent with how `feature_file`/`plan_file` are counted today (not exact rendered bytes including the leading newline/wrapper).

### Surfaces in scope
- `python/larch/rendering/rendering.py` (`_specialist_payload_bytes`)
- `python/tests/rendering/test_rendering.py` (new regression test)

### Open questions
- None.
