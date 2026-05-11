# scripts/generate-reviewer-correctness-edges-agent.sh — contract

`scripts/generate-reviewer-correctness-edges-agent.sh` regenerates `agents/reviewer-correctness-edges.md` from the canonical `## Reviewer: Correctness + Edge Cases` archetype in `skills/shared/reviewer-templates.md`. Default mode rewrites the agent file in place; `--check` exits non-zero if the committed file would drift from generator output.

Determinism is load-bearing: `LC_ALL=C`, no timestamps, no git state, and a hard-coded generated header. Enforcement comes from `scripts/check-generators.sh`, which dispatches every row in `scripts/generators.tsv` in `--check` mode. Editing the archetype requires re-running this generator in the same PR; see `.claude/rules/reviewer-archetype-generation.md`.
