### FINDING_1: [latent] Migration-limit operator note removed from SKILL
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The `--clear-architecture` migration-limit operator note was removed during driver extraction and not relocated. Operators troubleshooting legacy `runid=` diagram comments lose the only in-tree explanation of incomplete architecture cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add a Migration limit section to `design-publish.md` and optionally one pointer line in SKILL Step 5c item 4.


### FINDING_10: [important] Bundled upgrade-larch retention changes lack automated coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-prune-retention-output.txt
- **Severity**: important
- **Concern**: Bundled `upgrade-larch.sh` retention/stamp/backfill changes on this branch have no hermetic harness, Makefile target, or `relevant-checks` hook (unlike new `test-design-publish.sh` coverage for the design driver). Prune could delete the running version or fail to retain eight dirs; backfill/protected-prune regressions would only surface during live `/upgrade-larch`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add hermetic cache-dir harness + Makefile target + `relevant-checks` mapping or split to separate PR.


### FINDING_11: [latent] No harness for non-blocking design_reentry_marker_write failure
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No harness covers non-blocking `design_reentry_marker_write` failure. Marker-write regression could stop publishing or skip the append-tool-failure warning without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add stub/wrapper case forcing non-zero marker rc; assert continue + warning path.


### FINDING_12: [latent] No harness for upsert skipped when no diagram and no sentinel
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No harness covers upsert skipped when neither diagram nor skipped sentinel exists. Regression could call upsert with wrong args or skip the publish tail incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add fixture with neither arch file; assert no upsert log line and exit 0.


### FINDING_13: [nit] Missing structure pin for render-final-summary in design-publish.sh
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `test-design-structure.sh:1051-1063` lacks an explicit pin that `design-publish.sh` invokes `render-final-summary.sh`. Accidental removal of render calls might pass structure pins that only check exports.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add `grep -Fq render-final-summary.sh` on `DESIGN_PUBLISH_SH`.


### FINDING_15: [latent] step-5c sentinel written on plan-write-only success
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The `step-5c` sentinel is written on `PLAN_WRITE_OK=true` even when publish/rename failed (`SKILL.md:1361-1362`). Operators or tooling see `.completed/step-5c` while the issue lacks `[DESIGNED]` and logs may be missing; `/implement` admission still blocks but anti-halt proceeds to footer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Gate `step-5c` on `PUBLISH_OK=true` when `SESSION_ID` is set, or document sentinel semantics as plan-write-only.


### FINDING_16: [latent] Symlink result env blocks parse; loose fallback on rc 0
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: A symlink result env blocks file parse; loose `_publish_parse_ok` fallback can leave parse false with driver rc 0 (`SKILL.md:1327-1353`). GitHub mutations may have succeeded but the orchestrator skips success/failure branches and preservation warnings when stdout is empty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Abort `/design` when `_publish_parse_ok` is false after rc 0/1, or require `PLAN_WRITE_OK` in captured stdout.


### FINDING_18: [nit] design-publish.md overstates --clear-architecture trigger
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `design-publish.md:23` overstates the clear-architecture trigger vs implementation. Readers expect `--clear-architecture` whenever the skipped sentinel exists; empty `architecture-diagram.md` prevents clear.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document absent-file requirement for `--clear-architecture`.


### FINDING_19: [nit] Whitespace-only --session-id accepted at argv validation
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Session-id validation allows whitespace-only values (`design-publish.sh:20-24`). Whitespace run-id reaches `design-log-publish` and fails slug validation with a weaker operator signal than empty `SESSION_ID` WARN.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Reject whitespace-only `--session-id` at argv validation.


### FINDING_20: [important] SKILL final-summary block still references removed two-phase render callsites
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The final-summary block still references two-phase render callsites in removed Step 5c prose (`SKILL.md:424`). The orchestrator may search SKILL for inline render/publish steps or misuse the cancellation fence on the Gate-C happy path instead of relying on `design-publish.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Reword to: happy path uses `design-publish.sh` (internal two-phase render); do not use this fence on Gate-C success.


### FINDING_21: [nit] Missing --help exit-0 smoke test in design-publish harness
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Plan acceptance included a `--help` exit-0 smoke test; `test-design-publish.sh` lacks it. Broken `--help` could ship with a green harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add `assert_rc` for `bash design-publish.sh --help` expecting 0.


### FINDING_22: [nit] Missing phase_driver_write_result_env structure pin on design-publish.sh
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `test-design-structure.sh` has no `phase_driver_write_result_env` pin on `design-publish.sh` unlike design-route/init siblings. Result-env write could be removed without failing structure tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add grep pins for `phase_driver_write_result_env` on `design-publish.sh` matching sibling drivers.


### FINDING_23: [important] upgrade-larch stamps unverified installs before stable verification
- **Reviewer(s)**: dyn-prune-retention-output.txt
- **Severity**: important
- **Concern**: The branch moves `write_install_stamp "$ACTUAL_VERSION"` ahead of stable verification while still skipping `prune_cached_versions` when `VERIFIED_TARGET` is false (`upgrade-larch.sh:378-409`). A failed or partial upgrade can stamp the actually-installed (non-`LATEST_STABLE`) cache directory with a fresh `date +%s` timestamp even though prune does not run; on a later successful upgrade, that wrongly-stamped version enters the eight-version retention ranking as recently installed and can displace legitimately useful older cache dirs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prune-retention-output.txt: Restore stamping to the verified-only path (stamp together with prune when `VERIFIED_TARGET=true`), or stamp failed/unverified installs with a non-competitive value (for example mtime-derived backfill only) so failed installs cannot jump to the top of the retention sort.


### FINDING_4: [nit] Harness missing success-without-RENAMED= warn path
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `test-design-publish.sh:347-360` omits the success-without-`RENAMED=` warn path. Regression in `_rename_seen` handling would not be caught by CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add `RENAMED_OMIT_LINE=true` harness case asserting `WARN=` in result env.


### FINDING_6: [latent] Post–plan-write failures under set -e misreport exit 1 / omit result env
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-shell-compat-output.txt
- **Severity**: latent
- **Concern**: After `PLAN_WRITE_OK=true`, the success tail in `design-publish.sh` still runs under `set -euo pipefail` without a blanket `set +e` or ERR trap. Hard failures after a successful `plan-block-write.sh` (including `phase_driver_write_result_env` after emit, reentry guard source, upsert `printf`, etc.) abort with exit **1** and often no `.design-publish-result.env`, while stdout may already advertise `PLAN_WRITE_OK=true`. Exit `1` is reserved for plan-block-write failure; SKILL Step 5c treats `_publish_rc=1` as that path. The orchestrator may parse success from captured stdout on driver exit 1, write `step-5c`, and advance cleanup despite missing/invalid result env, or stop without the plan-write failure warning when `PLAN_WRITE_OK=false` was not parsed—even though the plan may already be on GitHub with publish/rename/summary incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use a non-1 exit or warn-and-exit-0 on result-env write failure after `emit_kv`; or document a third exit class and branch in `SKILL.md` so exit 1 remains plan-write-only.
  - From dyn-shell-compat-output.txt: After plan-block-write succeeds, either (a) disable `set -e` for the remainder and handle each helper’s rc explicitly (matching publish/upsert/marker), or (b) add an ERR trap that writes `.design-publish-result.env` with `PLAN_WRITE_OK=true` plus a `WARN=` and exits with a dedicated code outside `{0,1}` (e.g. `3`), and teach the SKILL exit-code contract to abort on that code.


### FINDING_7: [important] Happy-path harness pollutes operator HOME with reentry marker
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The happy-path harness writes a real reentry marker under the operator’s HOME without cleanup (`test-design-publish.sh:239`). Parallel CI or repeated local runs can leave `design-completed-42-9999` in `~/.cache` and cause ordering/flake failures in `test-design-reentry-guard` or other design tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Run subject under isolated HOME (`mktemp`) or stub marker write; trap-remove marker files; prefer CALL_LOG ordering assertions.


### FINDING_8: [important] SKILL.md-only edits skip test-design-publish in relevant-checks
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/relevant-checks.sh:101-105` skips `test-design-publish` for SKILL.md-only edits. A developer can change the Step 5c parse/exit contract in `SKILL.md`; pre-commit passes but the driver harness does not run until CI shard 16.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add `append_target_once test-design-publish` to the `skills/design/SKILL.md` case.


### FINDING_9: [important] Stale Step 5c.5 prose in run-logs.md
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `docs/run-logs.md:429` still describes Step 5c.5 inline orchestrator prose after driver extraction (plan-drift grep miss). Operators/docs readers may believe architecture upsert is orchestrator Step 5c.5 prose, not `design-publish.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Update `run-logs.md` to reference `design-publish.sh` / Step 5c driver.


