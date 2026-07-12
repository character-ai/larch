## Decision 1: Scope — regression guard + close
- **Question**: #7047 appears already-resolved by #7095 (all three consumers route through issue_wire). What scope should this design take?
- **Resolution**: Add a regression guard test asserting every `larch:plan` marker consumer routes through `issue_wire` (no hardcoded `<!-- larch:plan` marker literals in source), locking in #7095 so the cross-consumer drift that caused #7047 cannot silently recur. Then close #7047 as fixed by #7095.
- **Source**: user

## Decision 2: Hard constraint — #7095 already unified the three consumers
- **Question**: Do decompose.py / learn_from_bugs.py / design_router.py still bypass the shared marker owner?
- **Resolution**: No. Investigation confirms `python/larch/design/decompose.py:358` (`issue_wire.compose_named_block`), `python/larch/design/design_router.py:130` (`issue_wire.parse_named_block`), and `python/larch/issue/learn_from_bugs.py:67` (`issue_wire.named_block_marker_re`) all route through the shared `issue_wire` owner. No residual `larch:plan` `:start`/`:end` block literals exist in source outside `issue_wire.py`. The design must NOT re-do #7095's unification; it only hardens it.
- **Source**: codebase

## Non-goals
- Do NOT extend scope to the heading-based plan-boundary regexes in `learn_from_bugs._BOUNDARY_PATTERNS` (`## Plan` / `## Approach` / `### NEW:`) — those are intentional legacy-heading detection heuristics, not the `larch:plan` marker grammar.
- Do NOT touch the unrelated `design-pause` marker literal at `design_router.py:87` — different marker family owned by `design_pause.py`, outside #7047's plan-marker scope.
