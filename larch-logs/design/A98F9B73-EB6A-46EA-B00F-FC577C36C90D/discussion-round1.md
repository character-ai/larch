## Decision 1: Difficulty threading for plan-review renderer
- **Question**: How should difficulty reach `render_plan_review_main`?
- **Resolution**: `tier` is already available in `plan_review_panel.py`'s `_static_slot_rows`, `_dynamic_slot_rows`, and `_generic_plan_codex_row`. Add `--difficulty tier` to each subprocess render call. `render_plan_review_main` accepts a new `--difficulty ""` optional arg.
- **Source**: codebase

## Decision 2: Difficulty threading for specialist renderer
- **Question**: How should difficulty reach `render_specialist_main` for /review runs?
- **Resolution**: Thread explicitly through the dispatch chain: `review_dispatch_panel.py` adds `--difficulty tier` to `waterfall_args`; `agent_waterfall.py` Options and `_common_args` gain a `difficulty` field; `_review_launcher.py` args parser and `_review_specialist_render_args` gain `--difficulty`.
- **Source**: codebase

## Decision 3: Optional extension — docs-only/generated-only diff modes
- **Question**: Should we skip guidelines for `docs-only` and `generated-only` diff modes in specialist review?
- **Resolution**: Include — guidelines yield for these modes is near-zero (docs focus on accuracy/clarity; generated files don't need code-architecture guidance). The invariants block still applies. This is a designer's call per the feature description. Add `diff_mode in {"docs-only", "generated-only"}` to the skip condition alongside `difficulty == "TRIVIAL"`. Does not apply to plan-review (no diff_mode concept there).
- **Source**: codebase

## Decision 4: Fail-open behavior
- **Question**: What happens when difficulty is absent or unparseable?
- **Resolution**: Include both blocks. Default `--difficulty ""` means include. Both renderers use `difficulty.normalize_tier(args.difficulty)` and gate only when the normalized result is `"TRIVIAL"`.
- **Source**: feature description
