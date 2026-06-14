### OOS_1: [OUT_OF_SCOPE] `skills/design/references/brainstorm.md` still documents only Cursor framing and Codex scope launch examples; waterfall fallbacks (Codex framing, Cursor scope) do not spell out which `--stderr-sink` must pair with each canonical output file. That predates this branch but can still cause launch failures to land in a sink that `design_collect_launch_failures` never ingests when only the other output path is passed to `--mode collect`.
- **Reviewer**: dyn-brainstorm-flow-output.txt
- **Concern**: - `skills/design/references/brainstorm.md` still documents only Cursor framing and Codex scope launch examples; waterfall fallbacks (Codex framing, Cursor scope) do not spell out which `--stderr-sink` must pair with each canonical output file. That predates this branch but can still cause launch failures to land in a sink that `design_collect_launch_failures` never ingests when only the other output path is passed to `--mode collect`.
- **Suggested revision**: Address the concern above.


