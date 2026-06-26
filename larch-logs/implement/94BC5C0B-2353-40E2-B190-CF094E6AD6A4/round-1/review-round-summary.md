# Review Round 1

- Mode: `diff`
- 1 accepted, 4 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Step 7a shell harness still asserts pre-rename timing marks and skip breadcrumbs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: After the Step 7a rebrand to pre-ship (and related Step 8 ship-PR strings), `skills/implement/scripts/test-step-7a.sh` still pins old literals such as `Step 7a — code flow diagram`, `7a: diagrams status=skip`, and related timing marks. Green-path, diagram-skip, and quiet-diagram-skip regression cases fail while runtime output is correct; `make test-step-7a` does not validate the rename on a green tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Update assertions to Step 7a — pre-ship and ⏩ 7a: pre-ship status=skip ….
  - From cursor-specialist-edge-cases-output.txt: Update harness strings to Step 7a — pre-ship and 7a: pre-ship; optionally add pytest assertions so Makefile test-step-7a catches drift.
  - From cursor-specialist-testing-output.txt: Update assertions to Step 7a — pre-ship, Step 8 — ship PR, and ⏩ 7a: pre-ship status=skip …; extend coverage for ship-PR log-flush marks if needed.
  - From codex-specialist-edge-cases-output.txt: Update the Step 7a harness and any exact-string consumers to the new labels in the same patch, or keep emitting the old labels until those consumers are updated together.
  - From codex-specialist-testing-output.txt: update the harness literals alongside the rename, or keep the legacy breadcrumb until the harness is migrated
  - From codex-specialist-testing-output.txt: update those assertions to the new label, or preserve the legacy skip string until downstream checks are updated


