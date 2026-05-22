Here is the normalized structured finding list. Same behavioral risks are merged; distinct fixes or code paths stay separate. `[OUT_OF_SCOPE]` is kept on any heading that merged an out-of-scope source (FINDING_1 includes that tag because FINDING_21 was tagged).

### FINDING_1: [OUT_OF_SCOPE] Branch bundles audit-title work with unrelated changes
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: The branch mixes the narrow audit-title change with other work (main-sync pre-lock, OOS disposition / oos-silent-drop scan, harness shards, version/changelog, large run-log flushes, etc.), which inflates review surface, blurs plan traceability, and raises revert/bisect cost beyond a single headline narrative.
- **Suggested revision**: Split into focused PRs (audit-title-only vs main-sync vs OOS scan vs harness/log housekeeping) or explicitly document a deliberately coupled release and validate with full `make lint` (or the repo’s authoritative checks) before merge.

### FINDING_2: Legacy-shaped run-logs audit titles without `audit-report` label remain `/fix-issue` lock-eligible
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: After removing the dedicated legacy title guard, titles like `[Run Logs Audit Report <ts> …]` without the `audit-report` label can still match generic `has_report_prefix` / gating order such that `/fix-issue` exits success and acquires a lock (e.g. fixture 24b). Mis-labeled, imported, or fork issues with old title shapes remain eligible despite looking like chain-of-history audit output.
- **Suggested revision**: Treat as an explicit trade-off and document the invariant (rename + label guarantees), reintroduce a narrow legacy-prefix guard, tighten label verification, and/or enforce labeling policy so audit-shaped titles cannot lock without verifiable `audit-report`.

### FINDING_3: Duplicated git revision walk risks inconsistent pass/fail between gate and audit scan
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Inline triage logic duplicates a revision walk that also exists beside sourced `oos-disposition-shared` helpers, so edge cases (empty merge-base, missing remote) can diverge between the gate and the audit scan.
- **Suggested revision**: Consolidate range and evidence collection into one shared helper or a single script entry reused by both paths.

### FINDING_4: SKILL scan-registry prose mixes unrelated main-sync operator guidance
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: A long main-sync operator note sits inside scan-registry maintenance text, forcing operators editing scans to parse unrelated `/fix-issue` prefetch guidance.
- **Suggested revision**: Move the note to Pre-flight or a dedicated short subsection.

### FINDING_5: `has_report_prefix` comment may misstate case rules vs matcher
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: The comment uses a lowercase `report` snippet while the matcher is case-insensitive, which can mislead maintainers about the required title shape.
- **Suggested revision**: Clarify explicitly that matching is case-insensitive.

### FINDING_6: Docs overclaim alignment between generic `has_report_prefix` and narrower audit self-exclusion
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Comments/docs imply parity or audit-specificity for `has_report_prefix`, but it is a generic bracket-`Report` predicate while the skill uses a narrower “Run Logs Audit” regex; SKILL text also risks readers copying the wrong pattern into runbooks or scripts.
- **Suggested revision**: Tighten wording and, if helpful, show the exact bash and jq fragments side by side with independent descriptions of each predicate.

### FINDING_7: Missing explicit harness for new canonical audit title lacking `audit-report` after label gate ordering
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: No integration test locks in the expectation that a new-shape audit title without the `audit-report` label is rejected via `has_report_prefix` / report-prefix error after the label check, so future gate reorder could let unlabeled new-shape audits slip without a failing harness.
- **Suggested revision**: Add a targeted stub fixture expecting the report-prefix error path for the new title shape without `audit-report`.

### FINDING_8: Tests 14g vs 58f document different legacy semantics without cross-link
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Nearby tests/docs can read as contradictory about legacy classification vs self-exclusion without explicit linkage of intent.
- **Suggested revision**: Add a brief note in `test-audit-runs.md` linking 14g and 58f semantics.

### FINDING_9: [OUT_OF_SCOPE] Workflow YAML unchanged in branch diff
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: No workflow changes; N/A if `make lint` (or equivalent) remains the authoritative CI entrypoint.
- **Suggested revision**: None unless CI wiring must change for the new behavior.

### FINDING_10: oos-silent-drop inline triage can false-pass from unrelated parent-repo commits when artifacts are missing
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Fallback scans `merge-base..HEAD` of the parent repo when transcript artifacts are missing, so partial/copied run logs without `session-transcript` / `codex-commit-message` can yield a misleading pass.
- **Suggested revision**: Return zero, skip, or restrict logging to paths under `RUN_DIR` when artifacts are absent unless the run directory is an isolated git root; avoid parent-repo history as evidence in that mode.

### FINDING_11: `probe-error` fail-open when `origin/main` is absent weakens verified main-sync contract
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Clones or environments missing the remote ref may proceed to lock while main-sync state is unknown.
- **Suggested revision**: Tighten the contract or emit an explicit operator warning when the fail-open path is taken.

### FINDING_12: [OUT_OF_SCOPE] Bulk committed run logs dominate diff size
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Large `larch-logs/implement/**` trees add noise for feature-oriented review (likely intentional per run-log policy).
- **Suggested revision**: No change required for this PR scope beyond acknowledging policy.

### FINDING_13: [OUT_OF_SCOPE] `check-main-sync.sh` destructive `git reset` heuristics
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Destructive reset is guarded by heuristics; misclassification could reset local `main` (general git safety class).
- **Suggested revision**: Keep strict subject/path parity checks when evolving flush detection.

### FINDING_14: Operator-facing SKILL noise regex omits legacy `[Run Logs Audit Report <ts> …]` shapes that tests treat as non-matching / non-noise
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Documentation lists a single audit-title noise regex that does not cover legacy bracket shapes; stale or fork GitHub data with open legacy-titled audit issues may appear in searches while SKILL implies such titles are filtered noise.
- **Suggested revision**: Add a legacy disjunct to documented and implemented exclusion filters, or explicitly document the migration invariant and keep jq/shell parity.

### FINDING_15: Plan did not cover new `oos-silent-drop` scan and wiring
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: The diff adds scan registry / runner wiring not reflected in the supplied plan, breaking plan-to-implementation traceability.
- **Suggested revision**: Split unrelated work or extend the written plan to cover the new scan explicitly.

### FINDING_16: Plan did not cover `check-main-sync` pre-lock gate (and related stdout/eligibility contract shifts)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Pre-lock integration and optional hard reset expand behavior beyond audit-title alignment; consumers may have expected title-only changes.
- **Suggested revision**: Separate PR or add explicit requirements for main-sync integration and contracts.

### FINDING_17: Plan anchors stale line numbers for SKILL regex prose
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Plan cited line 105 while the relevant prose moved to ~106, inviting mis-filed review anchors.
- **Suggested revision**: Update plan templates or accept/annotate line drift when filing reviews.

### FINDING_18: Test 58f: legacy open title buckets to `proposed_augmentations` vs old `^\[Run Logs Audit Report` noise filter
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Stray legacy-titled open issues can change C.1 classification relative to the prior noise filter; intent may be unclear to operators.
- **Suggested revision**: Document as accepted behavior or tighten the jq noise predicate if stray legacy issues remain a concern.

### FINDING_19: [OUT_OF_SCOPE] Unrelated merged commit narrative (`cf73a0a3`, issue #2540 ordering fix)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: A merged commit addresses OOS disposition ordering unrelated to the audit-title plan scope.
- **Suggested revision**: Track under its own issue/PR narrative.

---

**Note:** `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` is **not** included because this output contains one or more `### FINDING_N:` blocks.
