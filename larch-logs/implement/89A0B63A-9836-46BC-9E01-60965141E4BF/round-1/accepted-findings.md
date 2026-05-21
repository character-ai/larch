### FINDING_1: risk-integration: .claude/skills/audit-runs/scripts/audit-map-runs.md:17
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Contract claims no manifest fallback after gh pr view failure but script still attempts manifest scan when RUN_ID is empty. Operators or tests written against the markdown may assume mapping stops on gh failure while runtime still maps via pr_number scan producing non-empty rows. Align audit-map-runs.md with audit-map-runs.sh or gate manifest fallback on gh_ok per intended policy.
- **Suggested revision**: Address the concern above.


### FINDING_10: correctness: .claude/skills/audit-runs/scripts/audit-scan-run.sh:366-391
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] cross-cutting pr_number_null and ended_at_null still mean empty field which becomes the normal case after removing those manifest fields. Every compliant new manifest emits pr_number_null true forever so audit noise hides real regressions. Schema-aware cross-cutting or renamed semantics aligned with manifest v2.
- **Suggested revision**: Address the concern above.


### FINDING_11: correctness: scripts/test-larch-logs-manifest.sh:45-56
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] New jq-based assertions run when jq is absent after jq-optional init checks. Environment without jq: script passes grep branch then fails on jq for updated_at test. Wrap updated_at assertions in command -v jq guard or skip.
- **Suggested revision**: Address the concern above.


### FINDING_12: correctness: scripts/larch-log.sh:402-428
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Flat steps_ran field updates bypass dotted validation and can corrupt steps_ran type. --field steps_ran=false breaks audit-scan jq argjson and silently drops skip semantics. Forbid flat steps_ran or validate object type.
- **Suggested revision**: Address the concern above.


### FINDING_15: correctness: .claude/skills/audit-runs/scripts/audit-map-runs.md:17
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Contract claims empty row and no manifest fallback when gh pr view fails, but audit-map-runs.sh still calls pick_newest_manifest_among_pr whenever RUN_ID is empty. Consumers treating MAP_GH_PR_VIEW_FAILED as hard empty-mapping may now get non-empty run_id from legacy pr_number manifests during gh outages, skewing PR-to-run joins. Align implementation with the contract (skip manifest fallback when gh_ok is false) or update the contract and add a stubbed gh regression test documenting the chosen behavior.
- **Suggested revision**: Address the concern above.


### FINDING_16: risk-integration: scripts/test-larch-logs-manifest.sh:44-55 vs scripts/larch-log.sh:1069-1078
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan and larch-log.md require commit-time updated_at refresh; tests only cover manifest subcommand refresh. A regression removing or mis-ordering the commit jq refresh ships green while breaking flush-time timestamp semantics. Add a commit-path assertion in test-larch-logs-manifest.sh or scripts/test-larch-log.sh comparing updated_at before and after commit.
- **Suggested revision**: Address the concern above.


### FINDING_20: risk-integration: larch-logs/implement/89A0B63A-9836-46BC-9E01-60965141E4BF/manifest.json:1-20
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Newly committed manifest still carries pr_number null and status in-progress despite template removal. Schema migration messaging and greps for new manifests may look inconsistent within the same PR. Re-flush from new init or normalize on commit; or document transitional legacy keys.
- **Suggested revision**: Address the concern above.


### FINDING_21: code-quality: .claude/skills/audit-runs/scripts/test-audit-runs.sh:1309-1375
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Tests 50-51 appear before Test 49, breaking monotonic test numbering. Harder to correlate failure output with file order during triage. Renumber or move blocks so labels match execution order.
- **Suggested revision**: Address the concern above.


### FINDING_23: correctness: larch-logs/implement/89A0B63A-9836-46BC-9E01-60965141E4BF/manifest.json:1-20
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Flushed manifest.json still has pr_number/status and omits steps_ran despite new init schema and tests expecting the opposite. Consumers/tests assume new manifests match the updated template; this committed directory contradicts the branch contract and weakens confidence in schema rollout. Regenerate or edit the committed manifest to match the new schema or adjust the flush commit so the repo matches the SSOT.
- **Suggested revision**: Address the concern above.


### FINDING_25: risk-integration: .claude/skills/audit-runs/scripts/audit-map-runs.md:17 vs .claude/skills/audit-runs/scripts/audit-map-runs.sh:158-168
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Doc claims no manifest fallback and an empty row when gh pr view fails; script still runs pick_newest_manifest_among_pr whenever RUN_ID is empty. Operators auditing with degraded gh may believe mapping is empty while a legacy manifest grep still returns a run_id, hiding auth/network failures. Match implementation to doc or update doc to describe manifest fallback after gh failure.
- **Suggested revision**: Address the concern above.


### FINDING_26: architecture: .claude/skills/audit-runs/scripts/audit-scan-run.sh:368-375
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] cross-cutting pr_number_null and ended_at_null treat absent fields like null. After pr_number/ended_at are routinely omitted, flags stay true for good manifests so the synthetic object loses discriminative power for integrity checks. Refine semantics for new schema_version or rename fields so absent keys do not read as failures/nulls.
- **Suggested revision**: Address the concern above.


### FINDING_28: risk-integration: .claude/skills/audit-runs/scripts/audit-map-runs.md:22-25 / .claude/skills/audit-runs/scripts/audit-map-runs.sh:158-167
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Doc says no manifest fallback on gh failure but script still runs pick_newest_manifest_among_pr when RUN_ID is empty after gh_ok=false Offline or broken gh can still map a PR via legacy manifest pr_number while stderr reports MAP_GH_PR_VIEW_FAILED; aggregators lose a clean gh-only-failure signal and may pick the wrong newest run if multiple manifests match Align code with doc (skip manifest fallback when gh_ok is false) or update doc to describe fallback after gh failure and how to disambiguate
- **Suggested revision**: Address the concern above.


### FINDING_29: architecture: scripts/larch-log.sh:402-428
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Bare steps_ran key uses generic manifest branch and can replace object with a scalar --field steps_ran=true (or a string) corrupts steps_ran shape; audit-scan-run jq probes then misbehave or never skip conditional files Reject bare steps_ran updates; require steps_ran.<step> only or validate object type after update
- **Suggested revision**: Address the concern above.


### FINDING_3: code-quality: larch-logs/implement/89A0B63A-9836-46BC-9E01-60965141E4BF/manifest.json:1-20
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Committed flush manifest retains legacy pr_number/status and omits steps_ran vs new generator/tests. Harnesses asserting new schema on committed logs or steps_ran-based gates see inconsistent shipped example. Normalize manifest at flush or migrate keys on commit.
- **Suggested revision**: Address the concern above.


### FINDING_30: correctness: larch-logs/implement/89A0B63A-9836-46BC-9E01-60965141E4BF/manifest.json:7-17
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Shipped example manifest still includes pr_number and status removed from init template Consumers/tests see contradictory in-repo examples vs documented new schema Regenerate manifest for that run directory or document as legacy snapshot
- **Suggested revision**: Address the concern above.


### FINDING_33: correctness: .claude/skills/audit-runs/scripts/audit-map-runs.md:22-25,.claude/skills/audit-runs/scripts/audit-map-runs.sh:85-168
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Contract says no manifest fallback when gh pr view fails but script still calls pick_newest_manifest_among_pr when RUN_ID is empty after gh failure. Readers/tests following the markdown expect an empty mapping after MAP_GH_PR_VIEW_FAILED while the shell may still map via legacy pr_number manifests masking gh outages. Either document manifest fallback after gh failure as intentional or skip manifest fallback when gh_ok is false to match the contract.
- **Suggested revision**: Address the concern above.


### FINDING_34: correctness: larch-logs/implement/89A0B63A-9836-46BC-9E01-60965141E4BF/manifest.json:9-17
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] New committed manifest still includes pr_number null and status in-progress despite schema cleanup removing those init fields. Branch ships at least one manifest.json that contradicts the new no-pr_number/no-in-progress-status policy for committed logs. Normalize that committed manifest to the new schema or re-flush after ensuring init/commit paths only emit the new shape.
- **Suggested revision**: Address the concern above.


### FINDING_35: correctness: implementation_plan §7 vs .claude/skills/audit-runs/scripts/test-audit-runs.sh:1309-1353
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan cites tests/test-audit-runs.sh but tests live under .claude/skills/audit-runs/scripts/test-audit-runs.sh. Plan-to-file traceability is slightly wrong though behavior likely correct. Update plan references or add a delegating tests/test-audit-runs.sh wrapper if that path must exist.
- **Suggested revision**: Address the concern above.


### FINDING_39: **correctness** `scripts/larch-log.sh:402-428` — The `steps_ran.*` branch only matches keys with a dot; a bare `--field steps_ran=…` falls through to the generic `*)` arm and can assign a non-object to `.steps_ran`, corrupting the manifest shape that `audit-scan-run.sh` assumes is an object for `--argjson`. **Suggested fix:** Reject bare `steps_ran` (require `steps_ran.<step>` only) or treat `steps_ran` as immutable like other structural keys.
- **Reviewer**: dyn-manifest-schema-integrity-output.txt
- **Concern**: - **correctness** `scripts/larch-log.sh:402-428` — The `steps_ran.*` branch only matches keys with a dot; a bare `--field steps_ran=…` falls through to the generic `*)` arm and can assign a non-object to `.steps_ran`, corrupting the manifest shape that `audit-scan-run.sh` assumes is an object for `--argjson`. **Suggested fix:** Reject bare `steps_ran` (require `steps_ran.<step>` only) or treat `steps_ran` as immutable like other structural keys.
- **Suggested revision**: Address the concern above.


### FINDING_40: **correctness** `larch-logs/implement/89A0B63A-9836-46BC-9E01-60965141E4BF/manifest.json:1-20` — The new committed run-log `manifest.json` in the diff still contains `"pr_number": null` and `"status": "in-progress"` without `steps_ran`, which contradicts the updated init template (`steps_ran`, no `pr_number`/`status`). That skews schema consistency in the very tree meant to demonstrate the change. **Suggested fix:** Regenerate or hand-edit that committed manifest to match the new schema before merge, or drop the flush commit if it was only for local validation.
- **Reviewer**: dyn-manifest-schema-integrity-output.txt
- **Concern**: - **correctness** `larch-logs/implement/89A0B63A-9836-46BC-9E01-60965141E4BF/manifest.json:1-20` — The new committed run-log `manifest.json` in the diff still contains `"pr_number": null` and `"status": "in-progress"` without `steps_ran`, which contradicts the updated init template (`steps_ran`, no `pr_number`/`status`). That skews schema consistency in the very tree meant to demonstrate the change. **Suggested fix:** Regenerate or hand-edit that committed manifest to match the new schema before merge, or drop the flush commit if it was only for local validation.
- **Suggested revision**: Address the concern above.


### FINDING_45: **correctness** `.claude/skills/audit-runs/scripts/audit-map-runs.sh:88-168` — After `gh pr view` fails (`gh_ok=false`), `RUN_ID` stays empty and the loop still runs `pick_newest_manifest_among_pr` when `[ -z "$RUN_ID" ]`, so a row can be filled from `manifest.json` even though [.claude/skills/audit-runs/scripts/audit-map-runs.md:17](.claude/skills/audit-runs/scripts/audit-map-runs.md) documents the opposite: “no manifest fallback on `gh` failure” alongside `MAP_GH_PR_VIEW_FAILED=true`. That is a direct contract/implementation mismatch introduced by this branch’s reordering. **Suggested fix:** Only enter the manifest scan when the primary `gh` path was attempted successfully, e.g. guard the block at 158 with `[ "$gh_ok" = true ] && [ -z "$RUN_ID" ]` (and treat `gh` failure as terminal for mapping: emit the stderr marker, leave `run_id` empty, print the TSV row). Update [.claude/skills/audit-runs/scripts/test-audit-runs.sh:893-904](.claude/skills/audit-runs/scripts/test-audit-runs.sh) (Test 31) to use a `PATH` stub for `gh` that succeeds with a body containing no usable `Closes #N` (or no matching `parent-issue.md`) so manifest-by-`pr_number` is still tested without relying on a real failed `gh` call, and add a focused test where `gh` exits non-zero but a matching old-format manifest exists and the script must leave `run_id` empty per the contract.
- **Reviewer**: dyn-audit-map-runs-flow-output.txt
- **Concern**: - **correctness** `.claude/skills/audit-runs/scripts/audit-map-runs.sh:88-168` — After `gh pr view` fails (`gh_ok=false`), `RUN_ID` stays empty and the loop still runs `pick_newest_manifest_among_pr` when `[ -z "$RUN_ID" ]`, so a row can be filled from `manifest.json` even though [.claude/skills/audit-runs/scripts/audit-map-runs.md:17](.claude/skills/audit-runs/scripts/audit-map-runs.md) documents the opposite: “no manifest fallback on `gh` failure” alongside `MAP_GH_PR_VIEW_FAILED=true`. That is a direct contract/implementation mismatch introduced by this branch’s reordering. **Suggested fix:** Only enter the manifest scan when the primary `gh` path was attempted successfully, e.g. guard the block at 158 with `[ "$gh_ok" = true ] && [ -z "$RUN_ID" ]` (and treat `gh` failure as terminal for mapping: emit the stderr marker, leave `run_id` empty, print the TSV row). Update [.claude/skills/audit-runs/scripts/test-audit-runs.sh:893-904](.claude/skills/audit-runs/scripts/test-audit-runs.sh) (Test 31) to use a `PATH` stub for `gh` that succeeds with a body containing no usable `Closes #N` (or no matching `parent-issue.md`) so manifest-by-`pr_number` is still tested without relying on a real failed `gh` call, and add a focused test where `gh` exits non-zero but a matching old-format manifest exists and the script must leave `run_id` empty per the contract.
- **Suggested revision**: Address the concern above.


### FINDING_6: code-quality: .claude/skills/audit-runs/scripts/test-audit-runs.sh:309-355
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Test blocks ordered 50/51 before labeled Test 49. Minor maintenance friction when triaging failures. Reorder or renumber tests monotonically.
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: .claude/skills/audit-runs/scripts/audit-map-runs.md:17 vs .claude/skills/audit-runs/scripts/audit-map-runs.sh:158-167
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Contract says no manifest fallback when gh pr view fails but script still scans manifest by pr_number when RUN_ID is empty. gh fails (auth blip) but an unrelated legacy manifest still has pr_number matching the PR: stderr reports MAP_GH_PR_VIEW_FAILED while stdout can show a mapped run_id masking total failure or mapping wrong content. Gate manifest fallback on gh_ok or update contract and tests to match actual behavior.
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: larch-logs/implement/89A0B63A-9836-46BC-9E01-60965141E4BF/manifest.json:1-19
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Shipped flush manifest retains pr_number/status and omits steps_ran contrary to new schema docs. Downstream schema validation or docs that assume this directory exemplifies the new contract fail or teach the wrong shape. Regenerate or edit manifest with current larch-log init template and steps_ran object.
- **Suggested revision**: Address the concern above.


