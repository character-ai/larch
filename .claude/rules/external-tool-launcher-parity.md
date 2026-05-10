---
paths: ["scripts/launch-review.sh", "scripts/launch-codex-*.sh", "scripts/launch-cursor-*.sh", "scripts/launch-gemini-*.sh", "agents/codex-implementer.md", "agents/cursor-implementer.md", "agents/gemini-implementer.md", "scripts/run-external-agent.sh", "scripts/collect-agent-results.sh", "scripts/check-reviewers.sh", "skills/implement/scripts/step2-implement.sh", "docs/external-reviewers.md", "docs/configuration-and-permissions.md"]
---

# External-Tool Launcher Parity

Codex, Cursor, and Gemini share most launcher surfaces; changes in one
usually apply to the other two. This rule covers shared argv grammar,
sanitization, retry, health, and cross-doc supported-tool lists.
Intentional asymmetries exist, e.g. dormant Gemini reviewer call sites in
some lanes, plus review-side JSON normalization and admin-policy snapshots
absent from implementers. Classify each asymmetry; don't force symmetry
blindly.

When changing `scripts/launch-review.sh`,
`scripts/launch-codex-*.sh`, `scripts/launch-cursor-*.sh`, or
`scripts/launch-gemini-*.sh` (implement and review variants), audit:

- **Argv validation** — `--timeout`, `--api-key`, `--model`, `--output`, `--prompt`, `--agent-file`; accepted in one launcher and rejected by another is a parity bug unless documented.
- **Sibling agent prompt** — `agents/codex-implementer.md` / `agents/cursor-implementer.md` / `agents/gemini-implementer.md`; schema/wording changes usually apply to all.
- **Sibling `.md` contracts** — every launcher has `<basename>.md` (per `.claude/rules/script-md-siblings.md`); update all three together.
- **Common collectors** — `scripts/run-external-agent.sh` and `scripts/collect-agent-results.sh`; sanitization, retry, and `.meta` parser changes affect all lanes.
- **Health probe** — `scripts/check-reviewers.sh`; healthy/unhealthy semantics must stay aligned.
- **Cross-doc surface** — `docs/external-reviewers.md`, `docs/configuration-and-permissions.md`, and SKILL.md prose enumerating supported tools must list all three identically.

Missing any surface is the #1 OOS-issue generator after a Cursor/Gemini
integration sweep.
