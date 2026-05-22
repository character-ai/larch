# Review Round 1

- Mode: `diff`
- Accepted findings: 3
- Rejected findings: 0
- Exonerated findings: 2
- Neutral findings: 0

## Accepted Findings

### FINDING_1: docs/workflow-lifecycle.md — `/design` node disconnected from orchestration Mermaid graph
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-mermaid-syntax-output.txt
- **Concern**: After removing `IMPLEMENT --> DESIGN`, the Skill Orchestration hierarchy still declares `DESIGN["/design"]` with no edges, so the diagram no longer encodes how `/design` relates to `/implement` / `/fix-issue` even though prose treats `/design` as a prerequisite peer orchestrator (not nested invocation). Readers may infer a broken or incomplete call graph.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-mermaid-syntax-output.txt: **correctness** `docs/workflow-lifecycle.md:9-32` — In the Skill Orchestration Hierarchy `graph TD` block, `DESIGN["/design"]` is declared and styled but has no incoming or outgoing edges after the planned removal of `IMPLEMENT -->|invokes| DESIGN`, so the diagram still parses and renders but no longer encodes any relationship between `/design` and the rest of the orchestration graph despite the prose immediately below stating that `/design` is a standalone orchestrator that runs before `/implement`. **Suggested fix:** Add one or more explicit edges that reflect the real contract without implying sub-invocation (for example a dashed edge `DESIGN -.->|issue-body larch:plan| IMPLEMENT`, or a small prerequisite node between `FIX` and `IMPLEMENT` if you want to keep `/implement` as the only hub).


### FINDING_11: AGENTS.md, skills/design/references/flags.md, skills/design/references/heavy-worker.md — stale `/implement --inline` recovery vs removed `/implement` argv contract
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-agents-md-scope-output.txt
- **Concern**: `AGENTS.md` now defers `SendMessage`-heavy `/design` behavior to `flags.md`, but `flags.md` (and `heavy-worker.md`) may still tell operators without `SendMessage` to run `/implement --inline`, while `skills/implement/SKILL.md` treats `--inline` as a removed `/implement` argv surface that must not be accepted — so the primary reader path can fail closed instead of recovering. Child references and any “see AGENTS.md” tails need to stay consistent with the issue-anchored `/implement` argv contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-agents-md-scope-output.txt: **correctness** `AGENTS.md:55` — The new bullet only defers SendMessage and heavy-dispatch behavior to `skills/design/references/flags.md`, but that file (and `skills/design/references/heavy-worker.md:78`) still tell operators without `SendMessage` to run `/implement --inline`, while `skills/implement/SKILL.md:185` classifies `--inline` among removed `/implement` argv surfaces that must not be accepted. After this change, `AGENTS.md` no longer gives the prior `/design --inline` escape text, so the primary reader path is more likely to follow the stale `/implement --inline` instruction and hit a rejected flag. **Suggested fix:** Bring `skills/design/references/flags.md` and `skills/design/references/heavy-worker.md` in line with the post–issue #2485 `/implement` argv contract (replace the `/implement --inline` operator sentence with the real host or tier behavior), remove the dangling “see `AGENTS.md`” tail once `AGENTS.md` no longer documents that workaround, and keep the shortened `AGENTS.md` pointer once the child references are accurate.
```

**Subsumed / omitted**

- **FINDING_18** (`larch-logs/.../plan-goals-test.md`): merged into the “historical logs / optional hygiene” theme already covered by **FINDING_5** and **FINDING_7**; same “no PR-scope change unless hygiene policy” outcome, so not listed separately (no new fix axis).
- **FINDING_23** (dyn-agents-md-scope): positive verification that `AGENTS.md` hunks match intent — not a normalized “concern” for the voting list; excluded by design of this aggregator pass.

Because there is at least one `### FINDING_N:` block, the line `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` must **not** appear anywhere in this output.

### FINDING_2: docs/agents.md — “Sequential Composition” heading vs prerequisite `/design` peer example
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: The subsection title and lead framing emphasize sequential / nested skill invocation while the body describes issue-anchored `/design` as a prerequisite peer to `/implement` (and non-`/review` paths). Skimmers may misread the lifecycle model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


