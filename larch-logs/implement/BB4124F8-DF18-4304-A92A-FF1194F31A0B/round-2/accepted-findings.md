### FINDING_1: Driver ignores assess child exit code
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-kv-contract-output.txt
- **Severity**: latent
- **Concern**: `_assess_rc` is captured from `assess-plan-round.sh` but never branched on. A non-zero child exit with empty or partial stdout is backfilled to `ASSESSOR_STATUS=skipped` / `ASSESSOR_VERDICT=skipped` and the driver exits 0, so misconfigured or failing assess runs can look like an intentional skip and Step 3.6 proceeds without fail-closed handling (including assess exit 2 with no `ASSESSOR_STATUS=` line).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Branch on _assess_rc after assess capture; emit explicit status/WARN or propagate failure before _write_result_and_emit.
  - From cursor-specialist-correctness-output.txt: Branch on _assess_rc; fail-closed or explicit error status when assess exits non-zero.
  - From cursor-specialist-testing-output.txt: Add harness for assess stub rc!=0 documenting behavior or fail-closed on rc
  - From cursor-specialist-edge-cases-output.txt: Check _assess_rc; on failure emit degraded status, WARN, and append-tool-failure; avoid silent skipped default.
  - From cursor-specialist-plan-fidelity-output.txt: Branch on _assess_rc; emit WARN or non-skipped status and document in design-plan-quality-assessor.md.
  - From dyn-kv-contract-output.txt: After the `set -e` block, if `_assess_rc -ne 0`, append a `WARN=`, set `ASSESSOR_STATUS` to a distinct settled status (or propagate failure via exit 2), and document the contract in `design-plan-quality-assessor.md`; mirror with a harness case.


### FINDING_10: write-after-failure test lacks rollback assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The write-after failure test does not assert `write-cursor` rollback behavior; regression removing or mis-ordering rollback could leave `plan-review-round-cursor.txt` inconsistent while `review-round-count.txt` still decrements.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: structural pin only checks string presence in driver Grep CALL_LOG for write-cursor and assert plan-review-round-cursor.txt after write-after failure


### FINDING_11: No dedicated worse-majority HARD happy-path driver test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: WORSE-majority is the operator-facing gate path but only not-worse is covered on the main happy path; KV/handoff regressions for worse-majority could reach production.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add HARD case with worse-majority ok status and EFFECTIVE_ASSESSORS>=1 asserting .step3.6-assessor.env and stdout


### FINDING_12: HARD round 1 (ROUND_NUM<2) path untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Driver write-after on round 1 then assess skipped is plan-documented but unguarded; cursor/snapshot ordering bugs could break the first HARD review round.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Stub ROUND_CURSOR_VALUE=1 and assert write-after plus assess skipped KVs


### FINDING_17: read-cursor failure silently keeps ROUND_NUM=1
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: On non-zero `read-cursor`, the driver resets to `ROUND_NUM=1` without WARN; SNAPSHOT_SH errors on HARD can make write-after and assess use the wrong round.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: WARN and log on non-zero read-cursor; fail closed or write-after-failed style settle.


### FINDING_18: write-cursor rollback ignores non-zero exit
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: After write-after failure, count is decremented but `write-cursor` rollback ignores non-zero exit; count and `plan-review-round-cursor.txt` can diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Log rollback failure; tie count decrement to successful cursor write.


### FINDING_19: Symlink/stale-env handoff missing chat WARN assertions
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-warn-routing-output.txt
- **Severity**: important
- **Concern**: Harness symlink case (and related stale-env coverage) checks stderr refusal and stdout KV fallback but does not assert driver-emitted `WARN=` lines (including write-failure WARN) appear in `chat.out` via the stdout-merge path when file parse is refused or incomplete, though SKILL.md / `apply_step3_6_handoff` should surface them when `_assessor_parse_ok` is false.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add assert_contains on chat.out for driver WARN lines after apply_step3_6_handoff with a symlinked result env.
  - From dyn-warn-routing-output.txt: Address the concern above.


### FINDING_3: workflow_path vs design_classification drift and dual parsers
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-kv-contract-output.txt
- **Severity**: important
- **Concern**: `WORKFLOW_PATH` in `design-plan-quality-assessor.sh` defaults missing/null `workflow_path` to `SIMPLE` and skips the gate, while `read-design-classification.sh` defaults missing/invalid `design_classification` to HARD with a warning. Partially corrupted `run-params.json` (e.g. `design_classification: "HARD"` but absent `workflow_path`) can leave the rest of `/design` on HARD while Step 3.6 silently skips with no mismatch `WARN=`. Separately, SKILL.md pre-read leaves `_wp` empty in the skip breadcrumb (`workflow_path=`) while the driver records `WORKFLOW_PATH=SIMPLE`, hiding the default in chat telemetry even when both skip.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Share one parser/default or pass orchestrator _wp into the driver.
  - From dyn-kv-contract-output.txt: When `workflow_path` is empty, fall back to `design_classification` (map `HARD` → HARD lane) or default `workflow_path` to HARD when classification is HARD; at minimum emit a `WARN=` when `design_classification` and `workflow_path` disagree so operators see assessor skip is not intentional.
  - From dyn-kv-contract-output.txt: In the SKILL.md pre-read, apply the same default as the driver (`SIMPLE` when empty after parse) or print the parsed `WORKFLOW_PATH` from the driver result env after invoke; add a harness case for missing `workflow_path` with HARD `design_classification`.


### FINDING_4: Step 3.6 handoff fence duplicated in harness
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `apply_step3_6_handoff` in `test-design-plan-quality-assessor.sh` mirrors the full SKILL.md fence (~75 lines); handoff contract drift is likely unless both are updated together. The SIMPLE skip-breadcrumb path is not exercised through `apply_step3_6_handoff`, so printf-only SIMPLE tests can pass while chat handoff drifts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared handoff shell or generate fence from one source.
  - From cursor-specialist-testing-output.txt: Run apply_step3_6_handoff on SIMPLE and assert skip breadcrumb in chat.out


### FINDING_5: Qualified-path test pins source text, not runtime invoke
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The qualified-path test greps harness `$0` source, not runtime behavior; regression could remove runtime qualified invoke while the test still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Assert call log or captured invoke uses CLAUDE_PLUGIN_ROOT path.


### FINDING_6: write-after-failure test does not assert assess was skipped
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The write-after-failure harness case does not assert the assess stub was not called; regression could invoke assess after a failed write-after without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add CALL_LOG assert that assess was not invoked.


### FINDING_8: Stale `.step3.6-assessor.env` wins over fresh stdout on write failure
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-warn-routing-output.txt
- **Severity**: important
- **Concern**: When `phase_driver_write_result_env` fails but a prior readable `.step3.6-assessor.env` remains (rm blocked or partial failure), the post-failure `result env write failed` WARN is appended only after `_kvs` is built so it never lands in the file and is stdout-only. SKILL.md file-first parse sets `_assessor_parse_ok=true` from any stale routing key, replays only file-stored WARNs, and suppresses stdout `WARN=` when `_assessor_parse_ok` is true; fill-only-unset merge cannot override stale `ASSESSOR_*` from stdout. Operators may see old `ASSESSOR_VERDICT=worse-majority`, miss write-after warnings, and get mis-routed WORSE Continue/Stop. Harness test 16 documents stale retention on driver stdout but does not run `apply_step3_6_handoff` for chat routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: On write failure remove or invalidate pre-existing env (or fail-closed); optionally stderr the write-failure WARN; consider skipping file-read when write failed.
  - From cursor-specialist-security-output.txt: Skip file parse or force stdout precedence when write fails or driver emits write-failure WARN.
  - From cursor-specialist-edge-cases-output.txt: Prefer stdout routing KVs when stdout includes result env write failed; or unlink env before write; extend handoff harness for chflags-blocked rm.
  - From cursor-specialist-plan-fidelity-output.txt: Invalidate file parse when write failed or delete stale env before merge; add handoff test where stale env disagrees with stdout.
  - From dyn-warn-routing-output.txt: On env write failure, treat the handoff as “file did not parse” (e.g. skip file-read when stdout contains `design-plan-quality-assessor: result env write failed`, or force routing-key merge from stdout to overwrite file values), and always replay stdout `WARN=` lines that are absent from the file; extend the harness with `apply_step3_6_handoff` over an immutable stale env asserting chat shows the write-failure WARN and stdout routing keys win.


