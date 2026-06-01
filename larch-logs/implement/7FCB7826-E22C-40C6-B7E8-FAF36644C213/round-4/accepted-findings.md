### FINDING_1: design-publish.sh — `set +e` before reentry guard weakens fail-closed source
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Stray `set +e` before sourcing `lib-design-reentry-guard.sh` disables errexit on source failure. If `PLUGIN_ROOT` is wrong or the library is missing, `source` returns non-zero but the script continues into upsert/publish/rename without a reentry marker while the plan block may already be written. Remove the standalone `set +e` on line 191 (and redundant `set +e` on line 195); let `source` fail closed under `set -euo pipefail`.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_10: test-design-structure.sh — weak Step 5c sentinel pin (`PUBLISH_OK=true` substring only)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The step-5c sentinel pin matches only a `PUBLISH_OK=true` substring. The orchestrator could write step-5c after `PUBLISH_OK=false` while the pin still passes. Pin the full `SESSION_ID` empty or `PUBLISH_OK=true` gate from `SKILL.md` Step 5c item 6.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_11: test-design-publish.sh — no test for empty `architecture-diagram.md`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No test for an empty `architecture-diagram.md`. An empty file may regress to upsert or clear against contract. Add a harness case with a zero-byte `architecture-diagram.md` and assert no upsert log line.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_12: test-design-publish.sh — no assertion on append-tool-failure for publish/upsert failures
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No assertion for append-tool-failure on publish/upsert failures. Warning-append regressions would be invisible; operators could lose the `execution-issues.md` trail. Assert `execution-issues.md` or stub log after unexpected publish and upsert-failed cases.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_18: design-publish.sh — publish exit 0 with missing `PUBLISH_OK=` not treated as failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: No branch treats publish exit 0 with missing `PUBLISH_OK=` as failure. Contract drift or truncated stdout could leave `PUBLISH_OK` empty; rename and step-5c are skipped with no append-tool-failure or `WARN`. After parse, if `SESSION_ID` is set and `PUBLISH_OK` is empty, set `PUBLISH_OK=false`, append-tool-failure, and `add_warn`.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_19: design-publish.sh — zero-byte `architecture-diagram.md` skips upsert and `--clear-architecture`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Zero-byte `architecture-diagram.md` skips both upsert and `--clear-architecture`. Re-design after a non-architectural run can leave an empty diagram file while a stale Architecture section remains on the issue. Clear when the file is empty and `.skipped` exists, or enforce Step 3b sentinel-only skip via harness.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_2: test-design-publish.sh — no harness for driver exit 3 (result-env write failure)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Exit code 3 (result-env write failure after a successful publish tail) is documented in `design-publish.md` and `SKILL.md` but not covered by the offline harness. Regressions that drop exit 3, mis-handle `_publish_rc=3` in `SKILL.md`, or break persist-after-success would not fail `test-design-publish.sh` or current structure pins. Add a harness case forcing `phase_driver_write_result_env` failure (e.g. symlink or chmod stub on the result env) asserting exit 3; align with any fixed exit-3 orchestrator contract.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_20: SKILL.md — step-5c sentinel gated on `PUBLISH_OK` instead of `PLAN_WRITE_OK` alone
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Step-5c sentinel is gated on `PUBLISH_OK` instead of `PLAN_WRITE_OK` alone. When plan-block-write succeeds but design-log-publish returns `PUBLISH_OK=false`, step-5c is not written despite `PLAN_WRITE_OK=true`, diverging from plan/acceptance and pre-extraction behavior. Write step-5c whenever `PLAN_WRITE_OK=true` after parsed driver handoff; keep rename and Step 6 cleanup gated on `PUBLISH_OK` separately; remove or rewrite the `PUBLISH_OK` step-5c structure pin.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_21: SECURITY.md — stale Step 5c.5 inline prose after driver extraction
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Stale Step 5c.5 inline prose after driver extraction. Security readers may not trace Architecture upsert to `design-publish.sh`. Reference `skills/design/scripts/design-publish.sh` for the diagrams upsert step, consistent with `docs/run-logs.md`.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_5: design-publish.sh — errexit re-enabled mid success tail misclassifies render failures
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `set -e` is re-enabled after `set +e` at line 191 (`set -e` at 198), so pre/post `render-final-summary.sh` runs under errexit while `plan-block-write` and `design-log-publish` succeed without `|| true`. If post-publish render returns 1, the driver exits 1 without writing result env; the orchestrator may parse exit 1 as plan-block-write failure and print “preserving tmpdir” while plan and logs are already published. Keep `set +e` for the full success tail after `PLAN_WRITE_OK=true`, or guard each `render-final-summary.sh` call (match the failed-plan-write branch); always write result env before exit.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_6: exit 3 — orchestrator abort skips summary/parse despite successful publish tail
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Exit 3 on result-env write failure aborts `/design` before mandatory final-summary emit and before Step 5c parse/emit, even when the publish tail finished, `final-summary.md` exists, and stdout already contains `emit_kv` output. Plan and logs may be on GitHub while the operator sees “publish tail incomplete” with no verbatim summary or parsed `PLAN_WRITE_OK`/`PUBLISH_OK`. Consider parsing `_publish_out` (and emitting non-empty `final-summary.md`) with a `WARN` on exit 3, best-effort result env with `WARN=`, exit 0 with `WARN` when only persistence failed, or renaming the banner to result-env write failure.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_8: upgrade-larch — install stamp docs vs script when verification fails
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Docs claim an install stamp on any successful install regardless of verification, but the script only stamps when `VERIFIED_TARGET=true`. Failed stable verification leaves a new install unstamped while `CHANGELOG`/`SECURITY` promise a stamp; retention ranking stays wrong until a later verified run. Add unconditional `write_install_stamp` when `ACTUAL_VERSION` is version-shaped or revert docs; cover in `test-upgrade-larch-retention.sh`.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_9: test-design-structure.sh — no structural pin for design-publish exit 3 / SKILL abort prose
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No structural pin for design-publish exit 3 / SKILL abort prose. A future edit could drop exit-3 handling; the orchestrator might treat an incomplete publish tail like exit 1 or take the wrong abort path. Grep `SKILL.md` for publish tail incomplete (exit 3) and `_publish_rc=3` alongside existing exit 2/1 pins.
- **Suggested revisions (informational for voters; coder decides)**:


