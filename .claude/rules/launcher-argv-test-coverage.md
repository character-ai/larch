---
paths: ["scripts/launch-*.sh", "scripts/test-launch-*.sh", "skills/implement/scripts/launch-*.sh", "skills/implement/scripts/test-launch-*.sh", "skills/implement/scripts/step2-implement.sh", "skills/implement/scripts/test-step2-*.sh"]
---

# Launcher Argv Test Coverage

Changing argv validation, output grammar, or rejection messages in `scripts/launch-*.sh` (or its dispatcher `step2-implement.sh`) without updating the sibling regression harness is the highest-recurrence agent-mistake class in this repo's launcher surface. The pattern "ship launcher change → file OOS for harness gap → fix later" is itself the bug.

When you change a launcher's behavior:

- **Run the matching `scripts/test-launch-<basename>.sh`** to see what it currently asserts. Asserted rejection paths, accepted paths, validation message text, and exit codes are the harness's contract.
- **Add or extend assertions in the same PR** for: every new accept path, every new reject path, the exact validation message text (pin literally), and the exit code on each branch.
- **Apply parity to other launchers** per `external-tool-launcher-parity.md` if the changed surface is shared (timeout grammar, api-key forwarding, model arg passing).

If a behavior change cannot be covered in the same PR for a concrete reason, file an OOS issue explicitly stating which assertion is missing — do not ship the launcher change with a quiet harness gap.
