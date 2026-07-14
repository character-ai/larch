## Decision 1: Architectural-compliance agent file disposition
- **Question**: When retiring the architectural-compliance reviewer slot, should piece 1 delete the orphaned agent files or keep/regenerate them? (Issue §3 says "update together"; piece title says "agent deletion".)
- **Resolution**: Delete the agent files — `agents/reviewer-architectural-compliance.md`, `agents/pre-rendered/reviewer-architectural-compliance-body.txt`, the `.manifest` line, the `rendering.py:991` special-case branch, the `skill-closure-baseline.json` entry, and the `tests/skills/_structure_review_specialized.py:142` list entry. The `reviewer-architectural-compliance` agent type is only panel-driven (no direct invocation found in python/skills/docs), so deletion is safe.
- **Source**: user

## Decision 2: Scope boundary — docs are out of scope for piece 1
- **Question**: Are `docs/review-agents.md`, `docs/external-reviewers.md`, `docs/topology.md` in piece 1's scope?
- **Resolution**: No. The partition assigned docs to piece 2; piece 1's firm file list contains no `docs/` paths. Transient doc/code inconsistency between piece 1 and piece 2 is accepted by the partition.
- **Source**: codebase (partition scope list)

## Decision 3: Hard constraint — archetype removal must be consistent across all static-reviewer sources
- **Question**: Is removing `architectural-compliance` from `_CODE_REVIEW_ARCHETYPES` alone sufficient?
- **Resolution**: No. `python/larch/review/review_pipeline_shared.py:25` independently hardcodes `STATIC_REVIEWERS` with the same 4 archetypes; `python/larch/report/tokens.py:114` and `python/larch/design/plan_scout.py` also reference it. All in-scope sources must be updated consistently so the archetype is fully retired, not half-removed.
- **Source**: codebase
