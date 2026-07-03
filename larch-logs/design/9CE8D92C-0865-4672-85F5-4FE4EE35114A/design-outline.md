## Proposed Design Outline

### Goals
- Reorder Step 5's claude_sub reviewer prompt assembly (`rendering.py::_render_specialist_text`) so the large static reviewer checklist comes first and per-round-varying content (diff-file pointer, optional plan/feature blocks) comes last, restoring Anthropic prefix-cache hits — mirroring the already-correct pattern in `render_voter_main`.
- Make Step 3's submodule-path list deterministic (`coder_delta_guards.submodule_paths`), removing a secondary Step 3 prefix-instability source.
- Extend `scripts/test-cache-key-discipline.sh` to cover the files central to this bug that it doesn't currently scan.

### Non-goals
- No session/resume (`--resume`/`--continue`) changes to the claude_sub lane — no such infrastructure exists today, and adding it is disproportionate to an assembly-ordering fix.
- No deduplication of the diff/plan/feature content that's both referenced by path and separately inlined via `--context-files` — removing content risks changing review outcomes, which the issue requires to stay unchanged.
- No change to *what* content Step 3/Step 5 prompts include — ordering only.

### Approach sketch
- `python/larch/rendering/rendering.py::_render_specialist_text`: move the dynamic diff-file-path sentence and optional plan/feature blocks to after the static `body` checklist; update the now-stale `# intentionally non-stable: ... (not Claude API)` comments, since this path is confirmed used for the claude_sub lane via `_claude_runner.py::launch_claude_review_main`.
- `python/larch/core/coder_delta_guards.py::submodule_paths`: sort the returned paths for determinism, matching the pattern `coder_runner.py::_submodule_paths` already uses via a separate helper.
- `scripts/test-cache-key-discipline.sh`: add coverage for `checks_lint_fix.py`, `coder_runner.py`, `review_dispatch_panel.py`, and `round_runner.py`, reconciling `scripts/test-cache-key-discipline.md`'s scope claim with actual enforcement.

### Surfaces in scope
- `python/larch/rendering/rendering.py`
- `python/larch/core/coder_delta_guards.py`
- `scripts/test-cache-key-discipline.sh` and its companion `scripts/test-cache-key-discipline.md`
- Existing tests: `python/tests/rendering/test_rendering.py`, `python/tests/core/test_coder_delta_guards.py`

### Open questions
- None.
