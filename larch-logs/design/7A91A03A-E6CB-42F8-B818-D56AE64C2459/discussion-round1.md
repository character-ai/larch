## Decision 1: Outcome scope
- **Question**: What outcome should #5393 produce for the hardcoded plan-review panel matrix in loaded SKILL prose?
- **Resolution**: Full centralization. Strip the hardcoded archetype matrix from all loaded SKILL prose (skills/design/SKILL.md — the line-10 opening summary and the Step 3 blocks), route readers to the topology/authority source, and reconcile references/plan-review.md.
- **Source**: user

## Decision 2: Hard constraints to preserve
- **Question**: What must not break when removing the matrix prose?
- **Resolution**: Preserve every load-bearing instruction. The "MUST ALWAYS run the full Step 3 panel / never skip or abbreviate" directive, the slowest-first spawn-order instruction (Cursor static slots before Codex), the cross-tool and both-absent Claude fallback rules, and the agent-lint S030 literal-path pins all stay. Only the archetype-identity enumeration (Arch, Innovation, Pragmatic, Requirements) is removed; the structural panel instructions remain.
- **Source**: codebase

## Decision 3: File scope (in vs out)
- **Question**: Which files are in scope?
- **Resolution**: IN — skills/design/SKILL.md (loaded prose: opening summary, Step 3 IMPORTANT block, spawn-order line) and skills/design/references/plan-review.md (the topology-designated authority; light reconcile to keep it the single prose home). OUT — scout-plan-archetypes-prompt.txt (load-bearing runtime scout input that needs the names to avoid proposing duplicate archetypes), python/rendering.py (code source of truth for rendered prompts), skills/shared/topology.tsv + docs/topology.md (count source of truth + generated projection; counts unchanged), docs/review-agents.md (human-facing consumer catalog that already links the topology anchors). The docs/review-agents.md boundary is surfaced at the outline gate for confirmation.
- **Source**: codebase

## Decision 4: Non-goals
- **Question**: What is explicitly NOT changing?
- **Resolution**: No runtime behavior change. The Python dispatch (panel-dispatch / plan_review.py) already builds the manifest; this is pure docs/prose dedup. No panel counts change, so no topology regeneration is required. No new abstractions.
- **Source**: user + codebase
