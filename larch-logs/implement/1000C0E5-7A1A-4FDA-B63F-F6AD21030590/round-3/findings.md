### FINDING_1: **correctness** — [`scripts/collect-agent-results.md:19`](scripts/collect-agent-results.md) — The updated NS-retry contract says that if publishing the validated retry body back to `<base>.txt` fails, the collector leaves `STATUS=NOT_SUBSTANTIVE`, but it does not say that the collector also deletes the `<base>-first-pass.txt` file that was created immediately before publish (`rm` of the first-pass sidecar on the publish-failure path in [`scripts/collect-agent-results.sh:165-167`](scripts/collect-agent-results.sh)). Operators reading only the doc may expect a first-pass sidecar to remain after a publish failure; the implementation and [`scripts/test-collect-agent-results.sh`](scripts/test-collect-agent-results.sh) (`C_NS_FP_PUBLISH_FAIL`) assume it is removed. **Suggested fix:** extend the publish-failure sentence to state that the first-pass sidecar is removed so the tree does not imply a successful publish.
- **Reviewer**: dyn-result-record-consistency-output.txt
- **Concern**: - **correctness** — [`scripts/collect-agent-results.md:19`](scripts/collect-agent-results.md) — The updated NS-retry contract says that if publishing the validated retry body back to `<base>.txt` fails, the collector leaves `STATUS=NOT_SUBSTANTIVE`, but it does not say that the collector also deletes the `<base>-first-pass.txt` file that was created immediately before publish (`rm` of the first-pass sidecar on the publish-failure path in [`scripts/collect-agent-results.sh:165-167`](scripts/collect-agent-results.sh)). Operators reading only the doc may expect a first-pass sidecar to remain after a publish failure; the implementation and [`scripts/test-collect-agent-results.sh`](scripts/test-collect-agent-results.sh) (`C_NS_FP_PUBLISH_FAIL`) assume it is removed. **Suggested fix:** extend the publish-failure sentence to state that the first-pass sidecar is removed so the tree does not imply a successful publish.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] **correctness** — [`scripts/collect-agent-results.sh:1262-1310`](scripts/collect-agent-results.sh) — NS-retry success paths set `RESULTS[IDX]` with `REVIEWER_FILE=$ORIG_OUTPUT` only; structured publish failure for the TSV/JSONL copy leaves `STRUCTURED_SIDECAR` on the validated retry-path sidecar, which should still exist because `preserve_and_publish_ns_retry` does not remove `NS_RETRY_OUTPUT`. No stale `NS_RETRY_OUTPUT` value is written into `RESULTS[IDX]` on the success path.
- **Reviewer**: dyn-result-record-consistency-output.txt
- **Concern**: - **correctness** — [`scripts/collect-agent-results.sh:1262-1310`](scripts/collect-agent-results.sh) — NS-retry success paths set `RESULTS[IDX]` with `REVIEWER_FILE=$ORIG_OUTPUT` only; structured publish failure for the TSV/JSONL copy leaves `STRUCTURED_SIDECAR` on the validated retry-path sidecar, which should still exist because `preserve_and_publish_ns_retry` does not remove `NS_RETRY_OUTPUT`. No stale `NS_RETRY_OUTPUT` value is written into `RESULTS[IDX]` on the success path.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] **correctness** — [`scripts/collect-agent-results.sh:1321-1358`](scripts/collect-agent-results.sh) — `emit_summary_result` still only forwards the four summary keys; full emission still runs `with_structured_sidecar_field` then `tr '|' '\n'`. Structured NS-retry success rows keep the canonical field order `REVIEWER_FILE|TOOL|STATUS|EXIT_CODE|STRUCTURED_SIDECAR|FAILURE_REASON`; substantive NS-retry success rows omit `STRUCTURED_SIDECAR` in the pipe record and rely on the existing `with_structured_sidecar_field` pass-through / padding behavior, unchanged by this branch.
- **Reviewer**: dyn-result-record-consistency-output.txt
- **Concern**: - **correctness** — [`scripts/collect-agent-results.sh:1321-1358`](scripts/collect-agent-results.sh) — `emit_summary_result` still only forwards the four summary keys; full emission still runs `with_structured_sidecar_field` then `tr '|' '\n'`. Structured NS-retry success rows keep the canonical field order `REVIEWER_FILE|TOOL|STATUS|EXIT_CODE|STRUCTURED_SIDECAR|FAILURE_REASON`; substantive NS-retry success rows omit `STRUCTURED_SIDECAR` in the pipe record and rely on the existing `with_structured_sidecar_field` pass-through / padding behavior, unchanged by this branch.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] code-quality: scripts/collect-agent-results.sh:1231-1266
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] NS_RETRY_OUTPUT still uses ORIG_OUTPUT%.txt stripping pre-existing in this area. Unusual non .txt OUTPUT_FILE values get odd retry sibling names. Not introduced by this branch leave for a dedicated path hygiene change if desired.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] risk-integration: scripts/collect-agent-results.sh:1231-1232
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] NS retry path uses ORIG_OUTPUT%.txt while first_pass_sidecar_path handles non-.txt. Weird retry artifact naming when OUTPUT_FILE is not *.txt. Pre-existing; fix in a dedicated path-normalization change if desired.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/collect-agent-results.md:24-25
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] The NOT_SUBSTANTIVE NS-retry outcome paragraph is a single dense block of many conditional clauses. Editors miss edge cases (e.g. publish vs sidecar failure) when updating one clause and accidentally contradict another. Split into short bullets mirroring nearby sections (preserve first pass publish prose structured sidecar failure modes).
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: scripts/collect-agent-results.md:24-25 vs scripts/collect-agent-results.sh:148-149
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Doc says stderr warning on first-pass copy failure; code uses larch_err. Operators or triage playbooks expect a warning-level signal but get error-channel severity. Align documentation with larch_err or change severity to match the documented contract.
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: scripts/collect-agent-results.sh:1292-1298
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Structured NS success publishes the sidecar with cp instead of the plan s mv leaving a duplicate normalized sidecar at the retry path. Operators or scripts may treat both paths as live artifacts or waste disk on large JSONL TSV bodies. Prefer mv for same directory publish or document that the retry path copy is intentionally retained garbage.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: scripts/test-collect-agent-results.sh:353-377
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] C_NSR does not assert the original reviewer file contains the published retry body after success. A regression that publishes breadcrumbs but leaves stale prose on the canonical path could slip if only the retry artifact assertion passes. Mirror C_NS_FP_SUCCESS with a grep on OUT_NSR for RETRY_CONTENT.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/collect-agent-results.sh:127-133
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] first_pass_sidecar_path only maps *.txt to *-first-pass.txt; larch-log allow-list is *-output-first-pass.txt NS-retry success for a specialist OUTPUT_FILE not ending in .txt could write a sidecar that write-round never commits, losing the observability goal. Document .txt-only OUTPUT_FILE or extend path helper and round_artifact_included for other extensions.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: scripts/collect-agent-results.sh:1292-1298
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Structured NS success publishes the sidecar with cp instead of the plan’s mv, leaving duplicate structured files at the ns-retry path and the final path. Two copies of the same sidecar after success; confusing if something later edits the retry-path copy. Use mv if single-copy semantics are required.
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: scripts/collect-agent-results.sh:1292-1298
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Structured NS-retry success publishes the structured sidecar with cp instead of the planned mv. After success, STRUCTURED_SIDECAR may point at ORIG_OUTPUT.* while an identical file remains on the NS-retry path; plan assumed relocation off the retry path. Use mv as in the plan, or amend the plan/spec to require duplicate sidecars on disk.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: scripts/collect-agent-results.sh:135-168
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Retry prose is published via temp cp+mv onto ORIG_OUTPUT; NS_RETRY_OUTPUT is not mv-renamed onto ORIG_OUTPUT as the plan stated. Plan text implied mv of the retry file onto the original basename (no separate -ns-retry.txt path after success); implementation keeps a full duplicate transcript at -ns-retry.txt. Decide whether retaining -ns-retry.txt is normative; if not, switch to the plan’s mv (after first-pass copy) or update the plan.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: scripts/collect-agent-results.sh:144-150
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] First-pass cp failure fails closed; plan snippet only showed the success breadcrumb path. Stricter than the minimal plan snippet; could surprise if someone expected overwrite to proceed without a sidecar. Already documented in collect-agent-results.md in this branch; optional plan sync only.
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: scripts/test-collect-agent-results.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Planned C_NS_FP_FAILURE (no sentinel) is not implemented as a single named case. Reviewers tracing the plan line-by-line may look for a missing-sentinel test and not find it under that name. Add a sentinel-missing case or rename test comments to match the plan vocabulary.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: scripts/collect-agent-results.sh structured NS-retry; scripts/collect-agent-results.md
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Documented best-effort structured sidecar publish failure has no regression test. A regression in the cp-to-final branch could break consumers expecting STRUCTURED_SIDECAR beside REVIEWER_FILE without failing the harness. Add a harness that forces final sidecar cp to fail and assert STRUCTURED_SIDECAR remains on the ns-retry path plus stderr contract.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: scripts/collect-agent-results.sh:1289-1299
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Structured sidecar publish failure yields OK row with prose at ORIG_OUTPUT but STRUCTURED_SIDECAR on ns-retry path. A consumer ignores STRUCTURED_SIDECAR and reads REVIEWER_FILE.tsv/jsonl; that sibling may be absent or stale vs retry prose, producing plausible but mismatched structured+prose state. Document mandatory STRUCTURED_SIDECAR parsing for NS-retry success; or fail closed / clean up sibling sidecar if co-location is required.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: scripts/test-collect-agent-results.sh (C_NSR)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] C_NSR does not assert the first-pass sidecar after the assertion change. If only C_NSR regressed, dropping -first-pass.txt might go unnoticed until C_NS_FP_SUCCESS drifted too. Assert first-pass sidecar presence and content in C_NSR.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: scripts/test-collect-agent-results.sh (NS-retry failure coverage)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Plan-style NS failure (missing or bad retry sentinel or empty retry output) is not explicitly asserted. Coverage relies on helper exit failure and no-meta cases; a future change could mishandle missing or invalid sentinel or empty retry transcript and still pass CI. Add a fixture omitting or corrupting *-ns-retry.txt.done (or empty retry body) and assert no *-first-pass.txt and expected STATUS.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: scripts/test-collect-agent-results.sh:511-520
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] C_NS_FP_PUBLISH_FAIL sources collect-agent-results.sh --source-only then calls preserve_and_publish_ns_retry relying on helpers and lib-quiet being defined before the early return gate. A refactor that moves sourcing below the gate breaks the test with command not found style failures far from the production bug. Add a comment documenting the invariant or assert the function exists after source.
- **Suggested revision**: Address the concern above.

