---
paths: ["scripts/launch-codex-*.sh", "scripts/launch-cursor-*.sh", "scripts/launch-gemini-*.sh", "agents/codex-implementer.md", "agents/cursor-implementer.md", "agents/gemini-implementer.md", "scripts/run-external-agent.sh", "scripts/collect-agent-results.sh", "scripts/check-reviewers.sh", "skills/implement/scripts/step2-implement.sh", "docs/external-reviewers.md", "docs/configuration-and-permissions.md"]
---

# External-Tool Launcher Parity

Codex, Cursor, and Gemini share most launcher surfaces and the changes you make in one usually apply to the other two. The rule applies to **shared launcher surfaces** — argv grammar, sanitization, retry, health, and the cross-doc enumerations of supported tools. Intentional asymmetries exist (e.g., the Gemini reviewer call sites are dormant in some lanes; review-side has JSON normalization and admin-policy snapshots that the implementer side does not). When you find an asymmetry, decide whether it is intentional or a parity bug; don't force symmetry blindly.

When you change one of `scripts/launch-codex-*.sh` / `scripts/launch-cursor-*.sh` / `scripts/launch-gemini-*.sh` (implement and review variants), audit every parity surface below:

- **Argv validation** — `--timeout`, `--api-key`, `--model`, `--output`, `--prompt`, `--agent-file`. A flag accepted by one launcher and rejected by another is a parity bug unless the asymmetry is documented.
- **Sibling agent prompt** — `agents/codex-implementer.md` / `agents/cursor-implementer.md` / `agents/gemini-implementer.md` describe the implementer contract. Schema/wording change in one usually applies to all three.
- **Sibling `.md` contracts** — every launcher has `<basename>.md` (per `.claude/rules/script-md-siblings.md`); update all three together.
- **Common collectors** — `scripts/run-external-agent.sh` and `scripts/collect-agent-results.sh` consume outputs from all three; sanitization, retry, and `.meta` parser changes affect all three lanes.
- **Health probe** — `scripts/check-reviewers.sh` probes all three; healthy/unhealthy semantics must stay aligned.
- **Cross-doc surface** — `docs/external-reviewers.md`, `docs/configuration-and-permissions.md`, and SKILL.md prose enumerating supported tools must list all three identically.

Missing one of these is the #1 OOS-issue generator after a Cursor/Gemini integration sweep.
