### FINDING_14: [OUT_OF_SCOPE] architecture: .claude/skills/audit-runs/SKILL.md:99
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Docs still frame cross-cutting pr_number signals pre-schema-change. Pre-existing drift amplified by manifest cleanup. Update when cross-cutting logic changes.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_2: code-quality: scripts/ship-pr.sh:1738-1742
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Post-merge path still writes status=done and pr_number to manifest despite initiative to drop those fields and teardown no longer mirroring them. Merged runs keep pr_number/status populated from ship-pr even when finalize stops touching them; audits expecting removal stay red. Remove or relocate those manifest fields in the ship-pr postmerge writer or explicitly document dual-writer policy.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_22: [OUT_OF_SCOPE] risk-integration: tests/test-audit-runs.sh (plan text only)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Implementation plan references tests/test-audit-runs.sh but Makefile points at .claude/skills path. Reader confusion only; CI already runs the correct harness. Update future plan text or add a thin wrapper if the path must exist.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_24: risk-integration: scripts/ship-pr.sh:1738-1742
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Postmerge path still writes status=done and pr_number to manifest.json. Teardown and init were aligned to drop these fields but ship-pr reintroduces them on successful postmerge so the schema cleanup never fully applies to typical runs. Remove or redesign these manifest writes and update ship-pr.md so only intended fields are written at flush.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_27: architecture: scripts/ship-pr.md:91
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Contract still documents status=done and pr_number manifest writes postmerge. Misleading documentation alongside updated implement-finalize.md. Update ship-pr.md when ship-pr.sh manifest writes change.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_32: [OUT_OF_SCOPE] code-quality: .claude/skills/audit-runs/scripts/test-audit-runs.sh:309-353
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Test blocks numbered 50/51 appear before Test 49 Mild maintainability friction only Renumber or reorder tests to match execution order
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_36: **correctness** `scripts/test-larch-log.sh:63,120-124` — Init no longer writes `"status": "in-progress"` (see `scripts/larch-log.sh` template in the branch diff), but this harness still requires that substring and still asserts `manifest` updates `status=done` and `pr_number=99`. `make test-harnesses-3` / `make test-larch-log` will fail until these expectations match the new schema (e.g. assert `steps_ran` object, drop or replace status/pr_number checks, and align the manifest-update test with supported fields). **Suggested fix:** Update `scripts/test-larch-log.sh` to match `scripts/test-larch-logs-manifest.sh` and the new `write_manifest_file` / `manifest` contract (or adjust `Makefile`/harness grouping if the test is intentionally retired).
- **Reviewer**: dyn-manifest-schema-integrity-output.txt
- **Concern**: - **correctness** `scripts/test-larch-log.sh:63,120-124` — Init no longer writes `"status": "in-progress"` (see `scripts/larch-log.sh` template in the branch diff), but this harness still requires that substring and still asserts `manifest` updates `status=done` and `pr_number=99`. `make test-harnesses-3` / `make test-larch-log` will fail until these expectations match the new schema (e.g. assert `steps_ran` object, drop or replace status/pr_number checks, and align the manifest-update test with supported fields). **Suggested fix:** Update `scripts/test-larch-log.sh` to match `scripts/test-larch-logs-manifest.sh` and the new `write_manifest_file` / `manifest` contract (or adjust `Makefile`/harness grouping if the test is intentionally retired).
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_37: **correctness** `scripts/ship-pr.sh:1692-1743` — `run_postmerge_phase` still calls `larch-log.sh manifest` with `--field "status=done"` and `--field "pr_number=$pr_num"` on the `PR_CLOSED=true` path. That was not changed in the reviewed diff while init/teardown dropped those fields, so new runs can still gain `status` / `pr_number` from this path and the “removed from manifest schema / post-flush lifecycle” story is inconsistent across writers. **Suggested fix:** Either remove or replace this postmerge manifest write (and `scripts/test-ship-pr.sh` expectations) so a single policy applies repo-wide, or explicitly document that only this path may set legacy fields and accept them in schema docs until a later migration.
- **Reviewer**: dyn-manifest-schema-integrity-output.txt
- **Concern**: - **correctness** `scripts/ship-pr.sh:1692-1743` — `run_postmerge_phase` still calls `larch-log.sh manifest` with `--field "status=done"` and `--field "pr_number=$pr_num"` on the `PR_CLOSED=true` path. That was not changed in the reviewed diff while init/teardown dropped those fields, so new runs can still gain `status` / `pr_number` from this path and the “removed from manifest schema / post-flush lifecycle” story is inconsistent across writers. **Suggested fix:** Either remove or replace this postmerge manifest write (and `scripts/test-ship-pr.sh` expectations) so a single policy applies repo-wide, or explicitly document that only this path may set legacy fields and accept them in schema docs until a later migration.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_38: **correctness** `scripts/verify-run-log-completeness.sh:47-76,90-91` — Step reachability for `step8` / `step9a1` still uses `MANIFEST_PR_NUMBER` and `MANIFEST_STATUS` from `manifest.json`. If `pr_number` / terminal `status` are no longer written on normal paths, runs that skip Step 9a.1 but omit `oos-issues.ndjson` / `run-statistics.md` can be misclassified vs `audit-scan-run.sh`’s new `steps_ran.<step>=false` gate (which the diff adds only to the audit scanner). **Suggested fix:** Mirror the `steps_ran` conditional semantics (or an equivalent reachability signal) in `verify-run-log-completeness.sh` and extend `scripts/test-verify-run-log-completeness.sh` so the two checkers stay aligned.
- **Reviewer**: dyn-manifest-schema-integrity-output.txt
- **Concern**: - **correctness** `scripts/verify-run-log-completeness.sh:47-76,90-91` — Step reachability for `step8` / `step9a1` still uses `MANIFEST_PR_NUMBER` and `MANIFEST_STATUS` from `manifest.json`. If `pr_number` / terminal `status` are no longer written on normal paths, runs that skip Step 9a.1 but omit `oos-issues.ndjson` / `run-statistics.md` can be misclassified vs `audit-scan-run.sh`’s new `steps_ran.<step>=false` gate (which the diff adds only to the audit scanner). **Suggested fix:** Mirror the `steps_ran` conditional semantics (or an equivalent reachability signal) in `verify-run-log-completeness.sh` and extend `scripts/test-verify-run-log-completeness.sh` so the two checkers stay aligned.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_41: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-manifest-schema-integrity-output.txt
- **Concern**: - **risk-integration** `scripts/ship-pr.md:91` (and related operator docs) still describe postmerge manifest finalization with `status=done` / `pr_number=N`; this predates or trails the partial doc updates in the diff and can confuse operators until ship-pr behavior and docs are reconciled.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_42: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-manifest-schema-integrity-output.txt
- **Concern**: - **correctness** `scripts/verify-run-log-completeness.md:36` — Mentions `manifest.json` `pr_number` / `status=done` as signals; same documentation drift as the verifier script if the schema migration is meant to be complete.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_43: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-manifest-schema-integrity-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/step2-implement.sh:444` — Reads `.status` from a different manifest artifact (`MANIFEST_RAW_PATH`); not introduced by this diff’s larch-log manifest template change.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_44: [OUT_OF_SCOPE] The `steps_ran.*` / `sn`+`v` jq binding pattern in `scripts/larch-log.sh` is internally consistent for multiple `steps_ran.*` fields in one invocation (indices advance with each `--arg` / `--argjson` triple). No collision defect found there.
- **Reviewer**: dyn-manifest-schema-integrity-output.txt
- **Concern**: - The `steps_ran.*` / `sn`+`v` jq binding pattern in `scripts/larch-log.sh` is internally consistent for multiple `steps_ran.*` fields in one invocation (indices advance with each `--arg` / `--argjson` triple). No collision defect found there. NO_ISSUES_FOUND does not apply; in-scope findings are listed above.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_46: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-audit-map-runs-flow-output.txt
- **Concern**: - **code-quality** `larch-logs/implement/89A0B63A-9836-46BC-9E01-60965141E4BF/manifest.json:1-20` — The new committed run-log fixture still uses `pr_number: null` and `status: "in-progress"`, which predates or contradicts the stated schema cleanup goal for new manifests; it does not affect `audit-map-runs.sh` logic directly but may confuse readers auditing #2513. **Suggested fix:** Regenerate or hand-edit that fixture to match the post-change manifest template once the schema work is finalized, or omit the fixture from the branch if it was only session scaffolding.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_7: [OUT_OF_SCOPE] code-quality: scripts/ship-pr.md:91
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Stale description of post-merge manifest pr_number/status writes while sibling docs were updated elsewhere. Pre-existing doc drift until next manifest lifecycle edit. Update alongside ship-pr.sh manifest policy changes.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

