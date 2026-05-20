---
paths: ["scripts/launch-review.sh", "scripts/launch-codex-*.sh", "scripts/launch-cursor-*.sh", "scripts/run-negotiation-round.sh", "scripts/lint-fix-loop.sh", "agents/codex-implementer.md", "agents/cursor-implementer.md", "scripts/run-external-agent.sh", "scripts/collect-agent-results.sh", "scripts/check-reviewers.sh", "skills/implement/scripts/step2-implement.sh", "docs/external-reviewers.md", "docs/configuration-and-permissions.md"]
---

# External-Tool Launcher Parity

Codex and Cursor share most launcher surfaces; changes in one
usually apply to the other. This rule covers shared argv grammar,
sanitization, serial-lock spawn guards, retry, health, and cross-doc
supported-tool lists.
Intentional asymmetries exist; classify each one instead of forcing symmetry
blindly.

When changing `scripts/launch-review.sh`,
`scripts/launch-codex-*.sh`, `scripts/launch-cursor-*.sh`,
`scripts/run-negotiation-round.sh`, or `scripts/lint-fix-loop.sh`,
audit:

- **Argv validation** — `--timeout`, `--api-key`, `--model`, `--output`, `--prompt`, `--agent-file`; accepted in one launcher and rejected by another is a parity bug unless documented.
- **Serial-lock spawn site** — Darwin `external_serial_lock_acquire` / `external_serial_lock_release_after` coverage and relative ordering versus the actual Codex/Cursor spawn must stay aligned across the launcher family; dedicated harnesses pin the concrete lock behavior.
- **Sibling agent prompt** — `agents/codex-implementer.md` / `agents/cursor-implementer.md`; schema/wording changes usually apply to both.
- **Sibling `.md` contracts** — every launcher has `<basename>.md` (per `.claude/rules/script-md-siblings.md`); update both together.
- **Common collectors** — `scripts/run-external-agent.sh` and `scripts/collect-agent-results.sh`; sanitization, retry, and `.meta` parser changes affect all lanes.
- **Health probe** — `scripts/check-reviewers.sh`; healthy/unhealthy semantics must stay aligned.
- **Cross-doc surface** — `docs/external-reviewers.md`, `docs/configuration-and-permissions.md`, and SKILL.md prose enumerating supported tools must list both identically.

Missing any surface is a common OOS-issue generator after an external-tool
integration sweep.
