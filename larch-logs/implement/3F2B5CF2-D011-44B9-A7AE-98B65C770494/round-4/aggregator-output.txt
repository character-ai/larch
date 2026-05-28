### FINDING_1: Multi-candidate extractor exceeds planned scope
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Implementation diverges from the agreed minimal preamble/fence stripping plan by adding a large multi-candidate Awk extractor, increasing review and regression risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Fenced diffs suppress valid unfenced fallback
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-awk-extraction-output.txt, dyn-candidate-lifecycle-output.txt
- **Severity**: important
- **Concern**: If any fenced diff candidate is extracted, the full raw response is not scanned, so a valid unfenced `plan.txt` diff after a corrupt or wrong-path fenced diff can be ignored.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-awk-extraction-output.txt, dyn-candidate-lifecycle-output.txt: Address the concern above.

### FINDING_3: Rewritten harness no longer preserves original acceptance matrix
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The test harness was fully rewritten despite plan acceptance requiring the original nine scenarios to remain unchanged or traceable, making regression equivalence hard to verify.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_4: Candidate glob order does not preserve encounter order
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-awk-extraction-output.txt, dyn-candidate-lifecycle-output.txt
- **Severity**: latent
- **Concern**: Candidate files are copied in encounter order but later iterated by shell glob order, so suffixed candidates can be tried before the first candidate or in `-10` before `-2` order.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-awk-extraction-output.txt, dyn-candidate-lifecycle-output.txt: Address the concern above.

### FINDING_5: `extract_patch` failure branch is unreachable
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-harness-equivalence-output.txt
- **Severity**: nit
- **Concern**: `attempt_tier` handles `extract_patch` returning non-zero, but the extract helpers always exit 0, leaving misleading dead control flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-harness-equivalence-output.txt: Address the concern above.

### FINDING_6: Candidate patch basename docs and fixtures drift from runtime
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Documentation, fixtures, and plan expectations refer to legacy or generic candidate patch names while runtime emits names such as `codex-output-candidate.patch`, creating forensic and test drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_7: Non-winning candidate artifacts remain published
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Failed scratch candidate patch files remain in revise logs and may be published, creating misleading artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: Plan-review loop can report revise success after rollback
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: If revise succeeds but post-apply `EMIT_PLAN` fails and restores the backup, `REVISE_STATUS` may still report `ok` or `ok-fallback` despite the restored plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_9: Missing leading prose preamble regression test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Tests cover trailing prose but not the issue #3146 failure mode where leading model prose precedes a valid unified diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: Missing `--recount` miscounted-hunk test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The harness does not include a patch with wrong hunk counts that fails normal `git apply --check` but passes with `--recount`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: Direct file-replacement mode lost test coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-harness-equivalence-output.txt
- **Severity**: important
- **Concern**: The rewritten harness does not exercise `--patch-format file-replacement` for tiers 1-3, leaving the standalone CLI mode untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-harness-equivalence-output.txt: Address the concern above.

### FINDING_12: Missing issue #3146 corrupt long-line reproduction
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: There is no automated fixture for the primary #3146 scenario involving structurally corrupt multi-hunk patches against long-line plans.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: Missing real revise-loop integration test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `ok-fallback` is tested through stub KV injection, but no end-to-end case wires the real revise script through `plan-review-loop.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: `revise.env` success and publish paths are under-tested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Durable `revise.env` artifacts are asserted on failure but not adequately checked on successful `ok-fallback` paths or publish happy paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: Tier-4 status assertions are incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Several harness cases do not assert `REVISE_TIER_4_STATUS`, despite acceptance expecting per-case KV coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_16: Blank lines can split one multi-hunk diff into partial candidates
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Interior blank lines between hunks can split a single valid multi-hunk patch, allowing only the first partial candidate to apply and report success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: Live `git apply --recount` may apply wrong boundaries on long lines
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Applying with `--recount` on very long plan lines may let a miscounted patch apply with plausible but incorrect boundaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_18: Tier-4 status ranking conflicts with documented severity
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `merge_tier4_status` ranks `invalid-patch` above `apply-failed`, which may hide the more actionable status and diverge from docs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_19: Tier-4 file replacement drops `## Plan` heading
- **Reviewer(s)**: dyn-awk-extraction-output.txt
- **Severity**: important
- **Concern**: `extract_file_replacement_candidate` treats `## Plan` as an opener but does not include it in the emitted block, so tier-4 can write a structurally invalid plan while reporting `ok-fallback`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-awk-extraction-output.txt: Address the concern above.

### FINDING_20: Trailing markdown bullets can be greedily included in diffs
- **Reviewer(s)**: dyn-awk-extraction-output.txt
- **Severity**: important
- **Concern**: Broad `+`/`-` patch-line matching can include post-diff markdown bullets or summaries as hunk lines, recreating corrupt patch failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-awk-extraction-output.txt: Address the concern above.

### FINDING_21: Candidate starts overlap inside one physical patch
- **Reviewer(s)**: dyn-awk-extraction-output.txt
- **Severity**: important
- **Concern**: `is_candidate_start()` can fire on embedded `---`/`+++` headers inside an existing `diff --git` patch, producing overlapping full and partial candidates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-awk-extraction-output.txt: Address the concern above.

### FINDING_22: Missing mismatched-context `git apply --check` regression
- **Reviewer(s)**: dyn-harness-equivalence-output.txt
- **Severity**: important
- **Concern**: The old case covering valid headers with mismatched hunk context was dropped, weakening coverage of apply-check failure and later-tier success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-equivalence-output.txt: Address the concern above.

### FINDING_23: Missing `--plan-file` argv defect coverage
- **Reviewer(s)**: dyn-harness-equivalence-output.txt
- **Severity**: nit
- **Concern**: The rewritten harness checks missing `--cursor-present` but no longer checks missing required `--plan-file` exits cleanly without `REVISE_*` stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-equivalence-output.txt: Address the concern above.

### FINDING_24: Total-failure harness assertions are weaker
- **Reviewer(s)**: dyn-harness-equivalence-output.txt
- **Severity**: nit
- **Concern**: The rewritten total-failure case uses presence-only assertions and no longer verifies empty winning fields, unchanged plan hash, or preserved backup snapshot.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-equivalence-output.txt: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] Unrelated breadcrumb fixture change
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-awk-extraction-output.txt, dyn-harness-equivalence-output.txt
- **Severity**: nit
- **Concern**: The branch includes unrelated `scripts/test-design-log-publish.sh` breadcrumb secret-path/tmpdir fixture changes and run-log artifacts outside the revise-waterfall scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-awk-extraction-output.txt, dyn-harness-equivalence-output.txt: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] Other `REVISE_STATUS` consumers may need `ok-fallback`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Other tooling may match only `ok` and misread `ok-fallback` unless repo-wide consumers are audited.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] Security docs omit `ok-fallback`, tier-4, and recount behavior
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md` still describes snapshot removal only for `REVISE_STATUS=ok` and does not mention `ok-fallback`, tier-4 fallback, or `--recount`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] Snapshot copy path may need symlink hardening
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Prior reviews noted possible symlink checks missing for `plan-review/round-N/revise/` sources copied into published artifacts; reviewers marked this as pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] Rename/copy patch metadata validation is incomplete
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `is_patch_line` accepts rename/copy metadata that `validate_unified_headers` does not explicitly validate, relying on `git apply` as the backstop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] Tier-4 fallback may call all external tools
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Tier-4 fallback can run up to three external tools after unified-diff tiers fail, increasing latency on large plans.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] Approval gate copy omits `ok-fallback`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Gate B passive-summary text does not mention `ok-fallback`, so operator-facing copy may not reflect tier-4 fallback outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] Informational branch and candidate-lifecycle observations
- **Reviewer(s)**: dyn-awk-extraction-output.txt, dyn-candidate-lifecycle-output.txt, dyn-harness-equivalence-output.txt
- **Severity**: nit
- **Concern**: Several reviewer notes record branch commits, verified tempdir lifecycle behavior, inner padded extraction ordering, tier-4 non-use of candidate globs, verified harness mappings, and other non-actionable observations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-awk-extraction-output.txt, dyn-candidate-lifecycle-output.txt, dyn-harness-equivalence-output.txt: Address the concern above.
