## Final Design Plan

The plan is very large. Showing the full plan body below.

## Plan

## Approach

Translate each legacy assertion into a named pytest node or parameter ID before deleting its Bash source. Invoke real repository helper scripts with `subprocess.run`. Use shared session, fake-plugin, and subprocess fixtures where they fit. Keep focused stubs local to the test module for `python3`, `review core`, and Step 18 CLI behavior. Do not change runtime helper scripts.

### NEW: python/tests/implement/test_implement_shell_scripts.py

- Add sections for Step 5 wrappers, Step 8 ship, Step 18, and review token propagation.
- Parameterize Step 5 wrapper-shape checks across `step-5-review.sh`, `step-5-resume.sh`, `step-6-entry.sh`, and `run-step-checks.sh`.
- Port Step 8 static pins and dynamic cases for fresh launch, live and dead rejoin, timeout replay, stale-result restart, exact bgjob and ship argv, state rehydration, guard routing, handoff publication, symlink rejection, and fail-closed merge-result writes.
- Port Step 18 gate predicates, marker behavior, Step 17 precedence, failure tolerance, safety-net routing, restore decisions, exact teardown argv, output ordering, and post-terminal finalization.
- Port token and timing-ledger propagation through the real session and `review-and-fix step5` CLI paths. Cover unsafe-ledger rejection and the TRIVIAL, MODERATE, and HARD panel shapes.
- Use real checkout paths for every helper under test. Keep fake dependencies in temporary directories and capture argv in structured files.
- Give every migrated assertion a descriptive node or parameter ID so parity can be audited against the deleted harnesses.

### REWRITTEN: skills/implement/scripts/test-step-5-review.sh

Delete the Bash harness after its wrapper assertions and delegated Python coverage have named pytest equivalents.

### REWRITTEN: skills/implement/scripts/test-step-8-ship.sh

Delete the Bash harness after all static, launcher, rejoin, child, guard, seeder, state-file, sidecar, and failure-path assertions pass in pytest.

### REWRITTEN: skills/implement/scripts/test-step-18.sh

Delete the Bash harness after the gate, finalize, marker, safety-net, restore, teardown, and ordering cases pass in pytest.

### REWRITTEN: skills/implement/scripts/test-implement-review-token-propagation.sh

Delete the Bash harness after session rehydration, token and timing propagation, unsafe-path handling, exact review argv, and difficulty routing pass in pytest.

### UPDATED: skills/implement/scripts/step-5-review.md

Point the edit-in-sync and coverage contract at the new pytest module and its Step 5 nodes.

### UPDATED: skills/implement/scripts/step-8-ship.md

Replace the retired harness reference with the new pytest Step 8 coverage.

### UPDATED: skills/implement/scripts/step-18.md

Describe the pytest coverage for gate, finalize, safety-net, restore, and teardown behavior.

### UPDATED: skills/implement/scripts/test-implement-review-token-propagation.md

Retitle this as the pytest coverage contract and reference the new module and relevant node group.

### UPDATED: skills/implement/scripts/test-step-5-review.md

Remove the obsolete `.sh` heading and describe the replacement pytest coverage while retaining the Step 5 contract note.

### UPDATED: skills/implement/scripts/test-step-18.md

Remove the obsolete `.sh` heading and retarget the coverage list to the pytest module.

### UPDATED: skills/implement/scripts/test-write-final-report.sh

Retarget or remove the retained comment that names the deleted Step 18 harness. If retained, point it to the Step 18 finalize and marker node group in `python/tests/implement/test_implement_shell_scripts.py`.

### UPDATED: skills/implement/SKILL.md

Replace all four retired harness references with the pytest module and the retained contract documents. Do not alter runtime orchestration.

### UPDATED: Makefile

- Remove the four focused Bash targets and their `.PHONY` entries.
- Remove the four prerequisites from harness shards 1, 3, and 5.
- Leave the new module under the existing Python test lane.

### UPDATED: scripts/residual-bash-paths.txt

Remove the three listed harness rows. `test-step-5-review.sh` has no residual-manifest row.

### UPDATED: python/migrated-scripts.tsv

Add the four deleted `.sh` paths with the current issue ID so retired-script lint blocks future references.

### UPDATED: agent-lint.toml

Remove the retired Step 18 shell-harness allowlist entry. Retain only live contract-document entries that still need explicit reachability treatment.

### UPDATED: docs/linting.md

Remove obsolete focused Bash target and shard claims. Point relevant coverage prose at the focused pytest module.

### UPDATED: python/test_fixtures/plan-fidelity-calibration/diffs/66A96EAD-3088-4750-AE3A-64A0E11EABBD_FINDING_10.diff

Replace the retired review-token harness-path literal with the new pytest module path. Preserve the fixture’s calibration scenario and all unrelated replay content.

### UPDATED: python/test_fixtures/plan-fidelity-calibration/diffs/E79F3F0B-4459-48FB-8241-5DDB90ABF050_FINDING_1.diff

Replace the retired review-token harness-path literal with the new pytest module path. Preserve the fixture’s intended calibration assertion and all unrelated replay content.

## Edge cases

- Preserve argument boundaries for paths containing spaces.
- Clear or reject stale, malformed, missing, non-regular, and symlinked result or state artifacts exactly as the real helpers require.
- Scrub ambient larch session and quiet-routing variables from subprocess environments.
- Keep Step 8 driver failure distinct from handoff-publication failure.
- Keep Step 18 best-effort failures from skipping teardown while preserving output order.
- Verify unsafe timing-ledger paths are omitted and warned about.
- Sweep retained harness comments and calibration-fixture literals so retired-script lint has no unmanifested references to deleted paths.

## Failure modes

- Missing assertion parity can silently reduce coverage. Use descriptive pytest nodes and compare them against every legacy assertion before deletion.
- Over-broad fakes can test fixture behavior instead of the shipped helper. Invoke real helper paths and stub only their external boundaries.
- Removing shard entries without removing targets or references can break partition and retired-script lints. Sweep Make, manifests, lint config, skills, retained harness comments, fixtures, and docs together.
- Editing calibration fixtures beyond their obsolete path literals can invalidate their replay purpose. Limit those changes to the replacement coverage reference.
- Nested pytest calls would hide coverage and distort collection. Port assertions directly instead of launching pytest from pytest.

## Testing strategy

- Run `PYTHONPATH=python python3 -m pytest -q python/tests/implement/test_implement_shell_scripts.py`.
- Run the existing Step 5 and bgjob modules that the thin harness previously delegated to.
- Run Python lint and type checks for the new module.
- Run `python3 python/cli.py residual-bash paths --root . --check-exists`.
- Run `make lint-retired-scripts`, confirming the tracked calibration fixtures no longer produce retired-path findings.
- Run `make test-harness-shards-coverage`.
- Run affected harness shards 1, 3, and 5, then `make test-harnesses`.
- Run `make py-test` for aggregate Python coverage.

difficulty: MODERATE
diff_added: 803
diff_deleted: 1053
mechanical_churn: true
oversize_override: operator
diff_lines: 1856
