---
paths: ["scripts/launch-codex-*.sh", "scripts/launch-cursor-*.sh", "scripts/launch-gemini-*.sh", "agents/codex-implementer.md", "agents/cursor-implementer.md", "agents/gemini-implementer.md", "scripts/run-external-agent.sh", "scripts/collect-agent-results.sh", "scripts/check-reviewers.sh", "skills/implement/scripts/step2-implement.sh", "docs/external-reviewers.md", "docs/configuration-and-permissions.md"]
---

# External-Tool Launcher Parity

Codex, Cursor, and Gemini are integrated symmetrically. When you change one of `scripts/launch-codex-*.sh` / `scripts/launch-cursor-*.sh` / `scripts/launch-gemini-*.sh` (implement and review variants), assume the change applies to the other two and audit every parity surface:

- **Argv validation** — `--timeout`, `--api-key`, `--model`, `--output`, `--prompt`, `--agent-file`. A flag accepted by one launcher and rejected by another is a parity bug.
- **Sibling agent prompt** — `agents/codex-implementer.md` / `agents/cursor-implementer.md` / `agents/gemini-implementer.md` describe the implementer contract. Schema/wording change in one usually applies to all three.
- **Sibling `.md` contracts** — every launcher has `<basename>.md` (per `script-md-siblings.md`); update all three together.
- **Common collectors** — `scripts/run-external-agent.sh` and `scripts/collect-agent-results.sh` consume outputs from all three; sanitization, retry, and `.meta` parser changes affect all three lanes.
- **Health probe** — `scripts/check-reviewers.sh` probes all three; healthy/unhealthy semantics must stay aligned.
- **Cross-doc surface** — `docs/external-reviewers.md`, `docs/configuration-and-permissions.md`, and SKILL.md prose enumerating supported tools must list all three identically.

Missing one of these is the #1 OOS-issue generator after a Cursor/Gemini integration sweep.
