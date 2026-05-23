Here is the normalized aggregator output. Several reviewers repeated the same themes; those are merged with combined attribution. `[OUT_OF_SCOPE]` sources that were kept as their own merged items (not folded into in-scope headings) retain the tag on the heading per your rules. Finding 13’s grep concern is the same as merged **FINDING_3** (with in-scope framing), so it does not get a separate heading; its reviewer slot is listed there.

```text
### FINDING_1: PR bundles prefix work with unrelated semver, argv/docs, and run logs
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: The change set mixes the title-prefix overhaul with unrelated MAJOR-level argv/docs changes and a large `larch-logs/implement/` tree, so reviewers cannot isolate regressions and consumers may read a MAJOR semver whose release story does not match the headline prefix work. Split the PR or document every bundled concern explicitly in the PR title, body, and changelog structure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Unreleased changelog audit-scope bullet contradicts branch reality
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: The Unreleased audit-scope bullet claims `CHANGELOG.md` and `larch-logs/` were left unchanged even though the branch adds or edits Unreleased changelog content and run-log paths. Readers may treat the bullet as forbidding any edits there and argue the PR contradicts its own changelog story.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Rewrite the bullet to distinguish bulk rewrite of historical prefix literals from normal new Unreleased entries and intentional new run-log commits.

### FINDING_3: “Zero-hit” acceptance grep conflicts with deliberate legacy literals in tree
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-testing-output.txt
- **Concern**: A literal “zero hits” `git grep` acceptance check cannot hold on a correct implementation that still carries deliberate legacy bracket tokens in tests, migration docs, `SECURITY.md`, admission recovery prose, and hermetic fixtures; CI or operators following the plan verbatim would false-fail. Tighten acceptance to path-scoped grep, explicit allow-lists, or otherwise match the mitigation strategy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Tighten the acceptance criterion to path-scoped grep and/or an explicit allow-list matching the plan mitigation.
  - From cursor-specialist-plan-fidelity-output.txt: Narrow grep scope or revise acceptance to allow migration docs, admission recovery text, and hermetic legacy fixtures.
  - From cursor-specialist-testing-output.txt: Clarify acceptance to allow-list migration literals or scope grep to prose-only paths.

### FINDING_4: Design skill clarify sub-steps 3.4–3.5 prose vs plan traceability
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: `skills/design/SKILL.md` around the clarify loop: sub-step 3.5 rationale still reads as if `needs-design-clarification` might coexist with `[DESIGNED]` even though 3.4 removes that label before 3.5, which can seed bogus “label/title desync” debugging narratives. Separately, the documented sequence (back-to-back designing then designed renames) differs from plan wording that implied a simpler planned→designed swap plus a later designing rename, adding plan-to-implementation traceability noise even if runtime behavior is consistent because clarify exits before later steps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Align prose with 3.4 then 3.5 ordering; keep only the publish/session-id and log-materialization rationale.
  - From cursor-specialist-plan-fidelity-output.txt: Document the dual-rename rationale in the plan/skill or collapse to the minimal callsites the plan listed.

### FINDING_5: `has_designed_prefix` requires exact `[DESIGNED]` plus a single ASCII space
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: `has_designed_prefix` (or equivalent) matches an exact `[DESIGNED]` token plus one space; titles like `[DESIGNED]Foo` miss the prefix gate and fail `missing-designed-prefix` at exit 5. Non-canonical GitHub titles that omit the space similarly fail the gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Document mandatory canonical spacing from tracking-issue-write or widen the matcher consistently with writers.
  - From cursor-specialist-edge-cases-output.txt: Document canonical-only requirement or normalize titles before matching.

### FINDING_6: [OUT_OF_SCOPE] Resume sentinel path skips strict title gates by design
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt
- **Concern**: The resume-sentinel path in `scripts/implement-admission.sh` intentionally skips managed-prefix, audit-label, and `[DESIGNED]` checks, creating a rare mismatch risk between strict preflight and resumed mid-flight titles if external metadata changes during outage-style recovery. This is a documented trust boundary around local `IMPLEMENT_TMPDIR` / `RUN_ID` pairing rather than a new remote exploit class.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Treat as documented trade-off per implement-admission.md; no change required for this PR unless product wants stricter resume gates.
  - From cursor-specialist-security-output.txt: None required here; operators already must protect session tmpdirs and RUN_ID pairing per contract docs.

### FINDING_7: `test-tracking-issue-write.sh` lacks symmetric negative coverage for `--state planned`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Only invalid `--state in-progress` is asserted; `planned` is not covered despite symmetric rejection requirements, so a regression could drop `planned` from the rejection set or garble the error string without harness signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Mirror the existing in-progress negative test for --state planned with the same exit and envelope assertions.

### FINDING_8: No hermetic coverage for rename `--state implementing` (critical Step 0 writer)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: There is no stubbed-`gh` fixture coverage for rename flows with `--state implementing`, so regressions in strip order, truncation, or prefix mapping for implementing could ship while `make test-tracking-issue-write` still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add stubbed gh fixtures for implementing from [DESIGNED] and optionally from legacy [IN PROGRESS].

### FINDING_9: Duplicated jq filter between harness and `fetch-combinable-issues.sh` risks silent drift
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: The combinable-issue jq filter is copy-pasted between `scripts/test-fetch-combinable-issues-filter.sh` and `.claude/skills/combine-issues/scripts/fetch-combinable-issues.sh`, so production filtering can drift from CI without failing tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a sync check or shared jq fragment and assert identity.

### FINDING_10: Combine-issues jq filter omits legacy `[IN PROGRESS]` exclusion; conflicts with “busy prefixes filtered” posture
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: The jq combinable filter’s excluded-prefix alternation no longer covers legacy `[IN PROGRESS] ` titles, so open issues with legacy in-flight prefixes can become combinable candidates again. That can route combine workflows at still-active legacy-titled tracking issues and violates the skill’s expectation that busy prefixes are filtered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Extend jq to exclude legacy IN PROGRESS/PLANNED prefixes or add fixtures/docs that encode the intended legacy posture.
  - From cursor-specialist-edge-cases-output.txt: Extend jq exclusion for legacy IN PROGRESS (and align SKILL prose + hermetic jq fixture tests).

### FINDING_11: `test-implement-admission.sh` `run_case` hardcodes managed-prefix for all exit 5 outcomes
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: `run_case` hardcodes managed-prefix expectations for every exit 5 path, so future exit-5 variants could be asserted incorrectly if the helper is reused naively.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Parameterize expected ADMISSION_RESULT for exit 5 or split helpers.

### FINDING_12: Duplicate pass coverage for plain `[DESIGNED]` titles in implement-admission tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Multiple tests cover the same `[DESIGNED]` plain-title pass case, increasing maintenance cost without adding distinct behavioral signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Collapse redundant cases or specialize one to a distinct edge.

### FINDING_13: Stale `RUN_ID` implement-admission test may not assert `ADMISSION_RESULT=managed-prefix` on exit 5
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: The stale `RUN_ID` fall-through path checks exit 5 and `TITLE=` but not managed-prefix expectations, so an incorrect `ADMISSION_RESULT` on exit 5 could slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert ADMISSION_RESULT=managed-prefix for the IMPLEMENTING stale-tmpdir scenario.

### FINDING_14: [OUT_OF_SCOPE] Release notes and commit history bundle unrelated threads
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: `[40.0.0]`-era release notes combine the prefix overhaul narrative with unrelated argv cleanup, and the branch history bundles an unrelated `/implement` argv/doc cleanup commit with prefix state-machine work, forcing readers who trace only the prefix plan to disentangle unrelated surface changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Accept as packaging or split notes in a follow-up editorial pass.
  - From cursor-specialist-plan-fidelity-output.txt: Keep commits split if the PR must map one-to-one to the prefix plan.

### FINDING_15: [OUT_OF_SCOPE] Large committed `larch-logs/implement/**` diff surface in the PR
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Large committed run-log deltas inflate PR diff noise during review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Per repo policy ignore unless reviewing log content quality.
```

**Merge / subsume notes (for voters, not separate findings):** Input **FINDING_13** (testing, `[OUT_OF_SCOPE]`) is the same behavioral risk as **FINDING_3**; it is folded into **FINDING_3** with its reviewer listed and its revision quoted verbatim. Input **FINDING_6** and **FINDING_15** are merged into **FINDING_6**. Input **FINDING_14** and **FINDING_16** are merged into **FINDING_10**. Input **FINDING_5** and **FINDING_17** are merged into **FINDING_5**. Input **FINDING_4** and **FINDING_21** are merged into **FINDING_4**. Input **FINDING_3** and **FINDING_20** are merged into **FINDING_3**. Input **FINDING_18** and **FINDING_22** are merged into **FINDING_14**.

Because this output contains one or more `### FINDING_N:` blocks, **`LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` must not appear** anywhere in the file.
