---
paths: ["scripts/launch-*.sh", "scripts/test-launch-*.sh", "skills/implement/scripts/step2-implement.sh", "skills/implement/scripts/test-step2-*.sh", "skills/implement/scripts/test-codex-implementer.sh", "skills/implement/scripts/test-cursor-implementer.sh"]
---

# Launcher Argv Test Coverage

Changing argv validation, output grammar, or rejection messages in
`scripts/launch-*.sh` (or dispatcher `step2-implement.sh`) requires a
same-PR regression harness update. "Ship launcher change → file OOS for
harness gap → fix later" is the bug.

Harness paths are **not** uniform:

- `scripts/launch-review.sh --tool cursor|codex` → `scripts/test-launch-review.sh`
- `scripts/launch-codex-implement.sh` / `launch-cursor-implement.sh` → `skills/implement/scripts/test-codex-implementer.sh` / `test-cursor-implementer.sh` (and `test-step2-dispatch.sh` for cross-coder dispatcher coverage)

The sibling `<basename>.md` (per `.claude/rules/script-md-siblings.md`)
names the current harness; read it before assuming a path. `docs/linting.md`
lists CI harnesses.

When you change a launcher:

- **Read the matching harness**. Asserted reject paths, accept paths,
  validation message text, and exit codes are contract.
- **Add or extend assertions in the same PR** for every new accept path and
  reject path, exact validation message text (pin literally), and each
  branch exit code.
- **Apply parity to other launchers** per
  `.claude/rules/external-tool-launcher-parity.md` when the surface is
  shared: timeout grammar, api-key forwarding, model arg passing.

If a concrete reason blocks same-PR coverage, file an OOS issue naming the
missing assertion; do not ship with a quiet harness gap.
