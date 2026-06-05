### FINDING_1: Unused/coarse dispatch status signals obscure panel failure semantics
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-waterfall-routing-output.txt
- **Severity**: important
- **Concern**: `review-core.sh` still parses `DISPATCH_OK` / `STATIC_DISPATCH_OK`, but no longer uses them after removing the dispatch-failed short-circuit. Meanwhile, the waterfall-layer `STATIC_DISPATCH_OK=false` remains a coarse “any static slot failed” signal that no longer matches the new threshold + per-archetype coverage semantics. This can mislead operators and maintainers about whether partial static dispatch aborts review rounds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-waterfall-routing-output.txt: Address the concern above.

### FINDING_2: Reviewer basename/static-slug normalization is duplicated across scripts
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Reviewer output basename normalization and static slug detection are implemented in multiple scripts. Drift in phase/retry suffix handling or static basename rules could make threshold counting, coverage attribution, and vote tallying disagree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_3: Coverage gate hardcodes static archetype slugs separately from dispatch authority
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `review-core.sh` hardcodes the four required static archetypes instead of consuming the dispatch-panel authority. Adding or renaming a static archetype in dispatch without updating coverage can make review-core require the wrong lenses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Threshold never-launched padding is unreachable because intended and launched counts are identical
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `review-core.sh` passes identical intended-slot and launched-slot counts to the threshold script, so the threshold script’s never-launched padding path never runs. A manifest row that fails to launch without dropped-slot or collector evidence may not increment failed slots unless another gate catches it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

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

### FINDING_9: Threshold counting can mis-handle duplicate normalized basenames or disagreeing statuses
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-waterfall-routing-output.txt
- **Severity**: latent
- **Concern**: `check-reviewer-failure-threshold.sh` can undercount or overcount when collector rows and phase/retry output files normalize to the same basename but carry different statuses. Collector duplicates can inflate failures, while collector OK plus failed phase artifacts can hide failures unless the script merges to one worst-status outcome per normalized base.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-waterfall-routing-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Scout harness does not pin prompt ban on folded static slugs
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The scout prompt forbids dynamic resurrection of folded `structure` and `plan-fidelity` slugs, but the harness does not assert that prose. Prompt drift could re-enable those folded slugs without immediate test failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: Expanded raw plan/feature embedding to reviewers increases prompt-injection and secret-exposure risk
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-prompt-context-output.txt
- **Severity**: important
- **Concern**: `render-specialist-prompt.sh` now exposes plan/feature content more broadly to external reviewers, especially `reviewer-testing`, and still inlines raw file content without redaction, escaping, or robust untrusted-data delimiters. Dynamic generic-mode reviewers also receive inline plan content across both vendors. Issue-derived plan text, secrets, or closing-tag prompt injection can therefore reach Codex/Cursor reviewers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-prompt-context-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Stale static-focus mappings still mention folded archetypes
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-waterfall-routing-output.txt
- **Severity**: nit
- **Concern**: `tally-code-votes.sh` still maps `structure` and `plan-fidelity` even though those static panel slots are no longer dispatched. This is harmless for runtime/legacy manifests but can confuse maintainers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-waterfall-routing-output.txt: Address the concern above.

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

### FINDING_15: [OUT_OF_SCOPE] Legacy folded specialist agents remain discoverable in-tree
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `agents/reviewer-structure.md` and `agents/reviewer-plan-fidelity.md` remain in the repository even though they are no longer active static panel slots. Operators browsing `agents/` may think they are still dispatched.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_16: Dynamic Codex reviewer outputs remain committed to run logs while static Codex outputs are excluded
- **Reviewer(s)**: dyn-prompt-context-output.txt
- **Severity**: important
- **Concern**: Static Codex specialist raw outputs are excluded from committed run logs, but dynamic Codex outputs and metadata remain included. With Codex dynamic twins enabled, reviewer transcripts may echo sensitive diff, plan, or drop context into committed logs, creating an asymmetric exposure path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-context-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Pre-existing description text quoting can break prompt structure
- **Reviewer(s)**: dyn-prompt-context-output.txt
- **Severity**: nit
- **Concern**: `render-specialist-prompt.sh` embeds `DESCRIPTION_TEXT` inside single quotes in an unquoted heredoc. A description containing a quote can break prompt structure. The reviewer marked this pre-existing, though the branch increases nearby plan/feature exposure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-context-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Pre-existing issue/plan materialization lacks redaction
- **Reviewer(s)**: dyn-prompt-context-output.txt
- **Severity**: latent
- **Concern**: `implement-bootstrap.sh` copies issue-derived plan and feature-description content into session files without redaction. Codex re-enable increases exposure, but the underlying trust model predates this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-context-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] Render-specialist prompt harness lacks broader negative assertions
- **Reviewer(s)**: dyn-prompt-context-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-render-specialist-prompt.sh` asserts plan injection for `reviewer-testing`, but does not broadly assert absence of plan injection for other agents in all narrowed modes.
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

### FINDING_23: [OUT_OF_SCOPE] Larch-log harness docs still list only Cursor static denied files
- **Reviewer(s)**: dyn-artifact-policy-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-larch-log.md` contract prose still lists only `cursor-specialist-*-output.txt` as denied write-round files, despite Codex static deny behavior being added elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-policy-output.txt: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] Timing kind enum still includes folded Codex specialist slugs
- **Reviewer(s)**: dyn-artifact-policy-output.txt
- **Severity**: nit
- **Concern**: `scripts/lib-timing-kinds.sh` still lists `codex-specialist-structure` and `codex-specialist-plan-fidelity` even though those archetypes are no longer dispatched. This may misattribute timing after the four-archetype collapse.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-policy-output.txt: Address the concern above.

### FINDING_25: Quick-mode docs sync contract overstates what POS_MARKERS enforces
- **Reviewer(s)**: dyn-sync-surfaces-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-quick-mode-docs-sync.md`, the script header, topology preamble, and generator text claim broader Step 5 public-phrase pinning than `POS_MARKERS` actually enforces. The harness only checks a subset of the documented anchors, so contributors may believe round-cap and hard-panel phrasing are mechanically protected when they are not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sync-surfaces-output.txt: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] Tally docs use folded `structure` as representative static slug
- **Reviewer(s)**: dyn-sync-surfaces-output.txt
- **Severity**: nit
- **Concern**: `skills/review/scripts/tally-code-votes.md` uses `structure` as a representative static slug even though the live panel no longer dispatches that archetype.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sync-surfaces-output.txt: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] Reviewer agent headers still imply template-derived generation
- **Reviewer(s)**: dyn-sync-surfaces-output.txt
- **Severity**: nit
- **Concern**: Some hand-maintained reviewer agents still carry “Derived from `skills/shared/reviewer-templates.md`” headers despite fold edits intentionally not routing through that template, which can mislead future editors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sync-surfaces-output.txt: Address the concern above.
