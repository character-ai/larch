---
paths: ["scripts/launch-*.sh", "scripts/test-launch-*.sh", "skills/implement/scripts/step2-implement.sh", "skills/implement/scripts/test-step2-*.sh", "skills/implement/scripts/test-codex-implementer.sh", "skills/implement/scripts/test-cursor-implementer.sh", "skills/implement/scripts/test-gemini-implementer.sh"]
---

# Launcher Argv Test Coverage

Changing argv validation, output grammar, or rejection messages in `scripts/launch-*.sh` (or its dispatcher `step2-implement.sh`) without updating the regression harness is the highest-recurrence agent-mistake class in this repo's launcher surface. The pattern "ship launcher change → file OOS for harness gap → fix later" is itself the bug.

When you change a launcher's behavior, locate the harness that covers it. The harness path is **not** uniform — review-side launchers and implementer-side launchers live in different trees:

- `scripts/launch-cursor-review.sh` → `scripts/test-launch-cursor-review.sh`
- `scripts/launch-gemini-review.sh` → `scripts/test-launch-gemini-review.sh`
- `scripts/launch-codex-implement.sh` / `launch-cursor-implement.sh` / `launch-gemini-implement.sh` → `skills/implement/scripts/test-codex-implementer.sh` / `test-cursor-implementer.sh` / `test-gemini-implementer.sh` (and `test-step2-dispatch.sh` for cross-coder dispatcher coverage)
- `scripts/launch-codex-review.sh` → no dedicated `test-launch-*.sh` harness today; coverage runs through the `/review` reviewer-collection path. If you change its argv, add a dedicated harness in the same PR rather than relying on indirect coverage.

The launcher's sibling `<basename>.md` (per `.claude/rules/script-md-siblings.md`) names its current harness; consult it before assuming a path. `docs/linting.md` enumerates the harnesses CI runs.

When you change a launcher:

- **Read the matching harness** to see what it asserts. Asserted rejection paths, accepted paths, validation message text, and exit codes are the harness's contract.
- **Add or extend assertions in the same PR** for: every new accept path, every new reject path, the exact validation message text (pin literally), and the exit code on each branch.
- **Apply parity to other launchers** per `.claude/rules/external-tool-launcher-parity.md` if the changed surface is shared (timeout grammar, api-key forwarding, model arg passing).

If a behavior change cannot be covered in the same PR for a concrete reason, file an OOS issue explicitly stating which assertion is missing — do not ship the launcher change with a quiet harness gap.
