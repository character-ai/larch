```text
### FINDING_1: Policy vs mechanics — Rejected oos-issues disposition not enforced
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: SKILL terminal invariant treats rejection into the oos-issues log batch as a durable disposition, but the disposition gate (and related audit logic) effectively keys off filed GitHub URLs and/or git-log `Inline-triage` breadcrumbs. Rejected-only batches with no URLs and no qualifying inline commits can still fail the gate and block clearing `OOS_PENDING`, so documented policy and enforcement disagree.
- **Suggested revision**: Extend gate/audit to recognize structured rejection evidence for each obligated non-security OOS block (or narrow SKILL invariant / NEVER text so it matches the signals the gate actually checks); add harness coverage if behavior is intentional.

### FINDING_2: Commit-range construction when merge-base is missing — too-wide or too-narrow git history
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Fallback behavior when the merge-base is empty/unavailable can reduce the inspected range to the tip only (missing inline breadcrumbs on earlier run commits) or, conversely, widen `git log` walks across large ancestry where unrelated historical commits contain `Inline-triage` strings, producing false negatives/positives relative to the intended “this run” contract.
- **Suggested revision**: Fail closed when base refs are unavailable, require explicit bounded refs/range, or otherwise align the walked revision set with the run’s intended commit list (document the contract if heuristic remains).

### FINDING_3: Audit `oos-silent-drop` inline evidence vs gate — different inputs can disagree
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Retroactive audit counting sums `Inline-triage` substring hits across broad run-directory `md/json/ndjson` surfaces, while the gate predicates primarily on git commit messages over a computed revision range. Stray mentions in logs/exports can inflate counts (false pass) or diverge from commit-only truth (false fail vs audit), undermining “audit matches live gate” expectations.
- **Suggested revision**: Restrict audit inputs to the same git-log predicate/range as the gate, use an allowlisted artifact set, or explicitly document weaker audit semantics (and reflect that in scan metadata like `scans.tsv` if applicable).

### FINDING_4: Duplicated awk counting logic risks gate/audit drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: The non-security OOS block counting snippet is duplicated between the gate and audit scripts; independent edits can desynchronize behavior silently.
- **Suggested revision**: Factor the shared counting/matching snippet into one included source of truth used by both paths.

### FINDING_5: `Inline-triage` detection is a loose substring heuristic (not tied per OOS block)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Counting treats any `Inline-triage` substring occurrence in-range as evidence without a strict per-block linkage to specific OOS indices/commits, so incidental mentions can satisfy obligations or real triage can be under-counted across commits.
- **Suggested revision**: Document explicitly as heuristic-only, or tighten matching to structured markers tied to each obligated OOS block.

### FINDING_6: Minor formatting drift in `audit-scan-run.sh` case arm
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Misaligned spacing in a `case` arm hurts readability and consistency with neighboring arms.
- **Suggested revision**: Match neighboring `case` arm formatting.

### FINDING_7: Gate exit code 1 vs exit code 2 conflated in orchestrator guidance
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: SKILL/orchestrator prose maps non-zero gate failures to the same remediation path, but exit `2` plausibly represents invalid range/setup/validation errors while exit `1` represents disposition gaps—operators may mis-diagnose and apply the wrong fix.
- **Suggested revision**: Branch messaging/categories by exit code (distinct failure text and recovery steps for exit `2` vs exit `1`).

### FINDING_8: [OUT_OF_SCOPE] Version bump bundled with behavioral OOS changes
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Semver churn mixed into the same change set as functional gate/audit behavior increases review noise; treated as release hygiene expectation rather than a defect requiring code change here.
- **Suggested revision**: No code change required from this finding; optionally keep policy as-is and separate semver-only churn in future PRs for reviewer ergonomics.

### FINDING_9: URL evidence source mismatch — `oos-issues-created.md` vs `oos-issues.ndjson`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Gate and audit may consult different URL-bearing artifacts; if they diverge, pass/fail and operator signals can disagree even when “an oos URL record exists somewhere.”
- **Suggested revision**: Unify the canonical URL source, or document parity requirements and add a regression fixture proving aligned behavior.

### FINDING_10: Exit `2` validation paths under-tested in harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Documented bad commit-range / validation failures (exit `2`) are not exercised, so regressions in `rev-list` validation can ship without CI signal.
- **Suggested revision**: Add harness cases asserting exit `2` and a stable stderr contract for invalid ranges/inputs.

### FINDING_11: Release notes gap for OOS gate / audit behavior
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: `CHANGELOG` omits the new OOS disposition gate / audit scan behavior, making failures and audits harder to correlate to the release.
- **Suggested revision**: Add a concise “Changed” bullet describing the behavior operators will observe.

### FINDING_12: [OUT_OF_SCOPE] Secrets scanning for committed implement run logs
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Committed run trees may contain environment/tool transcripts; org policy might warrant `gitleaks`/similar checks, but this is orthogonal to the gate script’s correctness.
- **Suggested revision**: Handle via org security policy / optional scanning workflows; not a required fix to `oos-disposition-gate.sh` itself.

### FINDING_13: Mixed PR scope — unrelated SKILL alignment bundled with OOS gate work
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Unrelated `caller_kind` documentation alignment in the same branch increases diff size and blurs regression attribution relative to the OOS gate change.
- **Suggested revision**: Split unrelated doc edits onto a separate branch/PR for clearer review history.

### FINDING_14: Gate inline counting uses line-based `grep -cF` semantics
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Multiple distinct `Inline-triage` obligations concatenated on a single commit body line can be counted as one line hit, causing false disposition failures vs `non_security_oos` counts.
- **Suggested revision**: Count occurrences per commit body (not lines) and add harness coverage for the multi-mention-on-one-line case.

### FINDING_15: Security OOS detector may match `focus-area = security` too broadly in free text
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Broad substring matching in block prose can misclassify blocks, excluding “normal” OOS items from obligations or otherwise skewing security vs non-security handling.
- **Suggested revision**: Tighten parsing to the actual structured `focus-area` field line (or equivalent structured extraction) and add a regression fixture.

### FINDING_16: [OUT_OF_SCOPE] Pre-existing `/issue` file-conflict edge limitation
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Known limitation around dropped file-conflict edges on some `/issue` paths; unchanged by this branch and not amplified by the new gate.
- **Suggested revision**: Track separately if still a product concern; no action required as part of this OOS gate review thread.

### FINDING_17: [OUT_OF_SCOPE] Bundled issue #2539 ship-pr harness / `caller_kind` rename scope
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Additional harness/SKILL edits tied to issue #2539 are outside the enumerated OOS plan traceability surface; not asserted as functional breakage for the OOS goal, but increases mixed-scope review burden.
- **Suggested revision**: Note orthogonality in PR summary and/or split commits/PRs for clearer attribution.
```
