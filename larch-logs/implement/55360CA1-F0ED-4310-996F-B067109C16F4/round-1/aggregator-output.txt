Here is the normalized aggregator output. Every input item was either merged into one of these findings or treated as non-actionable verification (**FINDING_23** — “hunks match intended shape”) and omitted from the fix list, which is appropriate for an aggregator that lists concerns rather than praise.

```text
### FINDING_1: docs/workflow-lifecycle.md — `/design` node disconnected from orchestration Mermaid graph
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-mermaid-syntax-output.txt
- **Concern**: After removing `IMPLEMENT --> DESIGN`, the Skill Orchestration hierarchy still declares `DESIGN["/design"]` with no edges, so the diagram no longer encodes how `/design` relates to `/implement` / `/fix-issue` even though prose treats `/design` as a prerequisite peer orchestrator (not nested invocation). Readers may infer a broken or incomplete call graph.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-mermaid-syntax-output.txt: **correctness** `docs/workflow-lifecycle.md:9-32` — In the Skill Orchestration Hierarchy `graph TD` block, `DESIGN["/design"]` is declared and styled but has no incoming or outgoing edges after the planned removal of `IMPLEMENT -->|invokes| DESIGN`, so the diagram still parses and renders but no longer encodes any relationship between `/design` and the rest of the orchestration graph despite the prose immediately below stating that `/design` is a standalone orchestrator that runs before `/implement`. **Suggested fix:** Add one or more explicit edges that reflect the real contract without implying sub-invocation (for example a dashed edge `DESIGN -.->|issue-body larch:plan| IMPLEMENT`, or a small prerequisite node between `FIX` and `IMPLEMENT` if you want to keep `/implement` as the only hub).

### FINDING_2: docs/agents.md — “Sequential Composition” heading vs prerequisite `/design` peer example
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: The subsection title and lead framing emphasize sequential / nested skill invocation while the body describes issue-anchored `/design` as a prerequisite peer to `/implement` (and non-`/review` paths). Skimmers may misread the lifecycle model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_3: README.md — weaker discovery path to `skills/design/references/flags.md`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Concern**: The `/design` catalog row no longer points operators at `skills/design/references/flags.md` for internal host dispatch / `SendMessage` / suspend-recovery nuance; discovery may rely on searching the tree or hitting stalls first.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Restore a neutral one-line pointer to skills/design/references/flags.md without advertising removed public argv flags.

### FINDING_4: [OUT_OF_SCOPE] Review session — empty precomputed diff and `main..HEAD` empty on unpushed single-commit branches
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-mermaid-syntax-output.txt, dyn-agents-md-scope-output.txt
- **Concern**: Precomputed `diff.txt` was empty and/or `merge-base..HEAD` was empty when `HEAD` matched local `main`, so reviewers relying on those artifacts could not confirm branch deltas from the sidecar alone; effective comparison may need `origin/main..HEAD`, parent commit, or refreshed session packaging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-mermaid-syntax-output.txt: The file at `<TMPDIR>/round-1/diff.txt` was empty, so whether the orphaned `DESIGN` node or any other diagram detail was introduced on this branch could not be confirmed from that artifact; the above is based on the current tree contents.
  - From dyn-agents-md-scope-output.txt: `<TMPDIR>/round-1/diff.txt` was empty; local `HEAD` and `main` pointed at the same commit, so `git log $(git merge-base HEAD main)..HEAD --oneline` was empty; the `AGENTS.md` review used `git show 7bfa1d63 -- AGENTS.md` as the effective patch.

### FINDING_5: [OUT_OF_SCOPE] CHANGELOG.md and skills/implement/** — residual historical `--design-only` / old framing in history or scripts
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Latent mentions of removed or legacy argv / framing may remain in changelog history and implement-related scripts; likely acceptable if consumer-facing docs are in scope and changelog is expected to retain history unless policy mandates scrubbing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: risk-integration — docs/topology.md / skills/shared/topology.tsv not updated on branch
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: If the implementation plan assumed topology regeneration but `topology.tsv` / generated topology docs were not updated, `topology.tsv` can drift and CI (`test-generate-topology-docs`) may fail on merge unless `scripts/generate-topology-docs.sh` is run and any diff committed or a no-op is documented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] skills/implement/scripts/write-final-report.sh — legacy DESIGN_ONLY_DONE paths may still emit `--design-only` in finalized summaries
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Old run logs may still show removed-flag strings beside newer consumer docs; awareness only for this PR unless log hygiene is in scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] skills/compress-skill/SKILL.md — `/design --inline` vs `flags.md` wording drift
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: `compress-skill` still references `/design --inline` while `flags.md` uses different mitigation wording; not in branch diff — possible conflicting operator instructions across docs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Reconcile compress-skill and flags.md in a follow-up doc pass.
  - From cursor-specialist-edge-cases-output.txt: Update compress-skill in a follow-up doc pass; not introduced by this diff.

### FINDING_9: [OUT_OF_SCOPE] docs/workflow-lifecycle.md — compress-skill forwarder still mentions `--auto` on `/implement` delegation
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Operators may forward removed argv into `/implement` when scaffolding compress runs; separate docs pass, unchanged by this commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] docs/workflow-lifecycle.md — End-to-End flowchart “merge yes” path may not reach completion
- **Reviewer(s)**: dyn-mermaid-syntax-output.txt
- **Concern**: In the End-to-End `flowchart TD`, the merge subgraph may leave `VERIFY` disconnected from `POST_ISSUE` / `DONE` (dead end unless intentional sketch); may predate this branch and is not specific to the `IMPLEMENT→DESIGN` edge removal alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-mermaid-syntax-output.txt: **correctness** `docs/workflow-lifecycle.md:73-107` — In the End-to-End `flowchart TD`, `MERGE_FLAG -->|Yes| MERGE_PHASE` enters the merge subgraph, but nothing connects the subgraph’s last step (`VERIFY`) to `POST_ISSUE` or `DONE`, so the “yes merge” path is a dead end in the diagram unless this was intentional as an incomplete sketch; if that layout predates this branch, it is not specific to the IMPLEMENT→DESIGN edge removal. **Suggested fix:** Add `VERIFY --> POST_ISSUE` or `VERIFY --> DONE` (whichever matches the real lifecycle) so every branch reaches completion.

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
