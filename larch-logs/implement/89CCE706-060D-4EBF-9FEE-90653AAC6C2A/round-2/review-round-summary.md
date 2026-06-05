# Review Round 2

- Mode: `diff`
- 13 accepted, 4 rejected (4 exonerated)

## Accepted Findings

### FINDING_1: Unused/coarse dispatch status signals obscure panel failure semantics
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-waterfall-routing-output.txt
- **Severity**: important
- **Concern**: `review-core.sh` still parses `DISPATCH_OK` / `STATIC_DISPATCH_OK`, but no longer uses them after removing the dispatch-failed short-circuit. Meanwhile, the waterfall-layer `STATIC_DISPATCH_OK=false` remains a coarse “any static slot failed” signal that no longer matches the new threshold + per-archetype coverage semantics. This can mislead operators and maintainers about whether partial static dispatch aborts review rounds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-waterfall-routing-output.txt: Address the concern above.


### FINDING_11: Expanded raw plan/feature embedding to reviewers increases prompt-injection and secret-exposure risk
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-prompt-context-output.txt
- **Severity**: important
- **Concern**: `render-specialist-prompt.sh` now exposes plan/feature content more broadly to external reviewers, especially `reviewer-testing`, and still inlines raw file content without redaction, escaping, or robust untrusted-data delimiters. Dynamic generic-mode reviewers also receive inline plan content across both vendors. Issue-derived plan text, secrets, or closing-tag prompt injection can therefore reach Codex/Cursor reviewers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-prompt-context-output.txt: Address the concern above.


### FINDING_13: Threshold contract docs omit reviewer-output-files and updated COUNTED_SLOTS semantics
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-waterfall-routing-output.txt
- **Severity**: latent
- **Concern**: `check-reviewer-failure-threshold.md` does not document `--reviewer-output-files`, even though it is used to count phase-2/phase-3 static fallback outputs. It also describes `COUNTED_SLOTS` as collector-only, while the script can include additional deduped static output files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt, dyn-waterfall-routing-output.txt: Address the concern above.


### FINDING_14: Stale render-specialist-prompt test comment contradicts reviewer-testing description-mode plan injection
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-sync-surfaces-output.txt
- **Severity**: nit
- **Concern**: A comment in `scripts/test-render-specialist-prompt.sh` still says description-mode plan injection is “diff-generic-only,” but new tests and docs require `reviewer-testing` to receive plan content in description mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt, dyn-sync-surfaces-output.txt: Address the concern above.


### FINDING_16: Dynamic Codex reviewer outputs remain committed to run logs while static Codex outputs are excluded
- **Reviewer(s)**: dyn-prompt-context-output.txt
- **Severity**: important
- **Concern**: Static Codex specialist raw outputs are excluded from committed run logs, but dynamic Codex outputs and metadata remain included. With Codex dynamic twins enabled, reviewer transcripts may echo sensitive diff, plan, or drop context into committed logs, creating an asymmetric exposure path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-context-output.txt: Address the concern above.


### FINDING_20: Static Codex run-log exclusion is under-tested
- **Reviewer(s)**: dyn-artifact-policy-output.txt
- **Severity**: latent
- **Concern**: Run-log harnesses do not fully pin the new static Codex raw-output deny policy. One test only checks Cursor static exclusion, and another stages only `codex-specialist-security-output.txt.meta` without staging/asserting the primary `.txt` transcript exclusion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-policy-output.txt: Address the concern above.


### FINDING_21: Dynamic Codex run-log inclusion is under-tested
- **Reviewer(s)**: dyn-artifact-policy-output.txt
- **Severity**: latent
- **Concern**: `test-larch-log-write-round.sh` only checks dynamic Codex `.meta` inclusion/sanitization, not body or JSON artifact inclusion. An over-broad deny-pattern regression could block `dyn-*-codex-output.txt` while tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-policy-output.txt: Address the concern above.


### FINDING_22: Larch-log shell comment omits Codex phased static fallback outputs
- **Reviewer(s)**: dyn-artifact-policy-output.txt
- **Severity**: nit
- **Concern**: The inline comment in `scripts/larch-log.sh` says phased Cursor specialist outputs remain included, but does not mention equivalent Codex static phased fallbacks. The behavior may be correct, but the comment is stale/misleading.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-policy-output.txt: Address the concern above.


### FINDING_25: Quick-mode docs sync contract overstates what POS_MARKERS enforces
- **Reviewer(s)**: dyn-sync-surfaces-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-quick-mode-docs-sync.md`, the script header, topology preamble, and generator text claim broader Step 5 public-phrase pinning than `POS_MARKERS` actually enforces. The harness only checks a subset of the documented anchors, so contributors may believe round-cap and hard-panel phrasing are mechanically protected when they are not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sync-surfaces-output.txt: Address the concern above.


### FINDING_5: Coverage gate ignores substantive external reviewer files outside collector OK/cap-hit rows
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-waterfall-routing-output.txt
- **Severity**: latent
- **Concern**: `static_archetype_coverage_ok` supplements collector success with substantive Claude fallback files, but not substantive external files from `external_array`. If collector rows are missing or non-OK while a Codex/Cursor output file exists and is substantive, threshold math may credit the file while coverage still fails the archetype.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-waterfall-routing-output.txt: Address the concern above.


### FINDING_6: Dispatch-panel harness does not assert Codex-present forwarding to waterfall
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-dispatch-panel.sh` checks scout argv but not waterfall argv for `--codex-present true/false`. A regression that again sets `codex_present_for_waterfall=false` when Codex is available could pass tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_7: Review-core lacks harness coverage for partial static dispatch with threshold still passing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The relaxed `STATIC_DISPATCH_OK=false` behavior is not directly tested. A regression could reintroduce early bailout or skip threshold processing when one static peer is dropped but the round should continue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_8: Coverage gate lacks test for both peers of one archetype dropped while aggregate threshold passes
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Harnesses do not cover the case where both vendors for one required archetype are dropped while total failures remain at or below 50%. That could allow a round with no security/testing/etc. lens if coverage regresses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


