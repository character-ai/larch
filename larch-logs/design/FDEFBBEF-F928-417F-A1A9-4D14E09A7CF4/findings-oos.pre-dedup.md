### OOS_1: Hand-maintained testing specialist still embeds default-test-to-OOS without the plan-mandated carve-out
- **Description**: Hand-maintained testing specialist still embeds default-test-to-OOS without the plan-mandated carve-out. Scenario: Proposer prompts may still route some plan-mandated test gaps to OOS before they reach voters; this issue targets slot-v2 voter behavior on findings already on the ballot
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: agents/reviewer-testing.md:47-50
- **Phase**: design



### OOS_2: Rubric/lens fixes do not change 2-of-3 `accept_finding` quorum
- **Description**: Rubric/lens fixes do not change 2-of-3 `accept_finding` quorum. Scenario: Plan-mandated findings can still fail panel acceptance when validity and pragmatism vote NO even after plan-fidelity YES improves; issue non-goals explicitly exclude threshold changes
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/voting.py:1190-1198
- **Phase**: design



### OOS_3: Hand-maintained testing specialist still embeds default-test-to-OOS without the carve-out
- **Description**: Hand-maintained testing specialist still embeds default-test-to-OOS without the carve-out. Scenario: `review-acceptance-rubric.md` Update triggers require direct edits here, but the plan excludes this path. Pre-render regen snapshots the stale Necessity gate into `agents/pre-rendered/reviewer-testing-body.txt`, so the testing proposer lane can keep suppressing plan-mandated deliverable findings even after voter rubric fixes.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: agents/reviewer-testing.md:47-50
- **Phase**: design



### OOS_4: Prompt-only rubric fixes do not change 2-of-3 accept_finding quorum
- **Description**: Prompt-only rubric fixes do not change 2-of-3 accept_finding quorum. Scenario: Plan-mandated findings can still fail panel acceptance when validity and pragmatism vote NO even if plan-fidelity YES-rate improves after calibration. The issue acceptance criterion may show better v2 votes while user-visible rejection rate is unchanged.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/voting.py:1190-1198
- **Phase**: design



### OOS_5: [SCOPE-REDUCTION] Jsonl/findings.md ballot reconstruction may be heavier than committing frozen fixtures for every cohort row
- **Description**: [SCOPE-REDUCTION] Jsonl/findings.md ballot reconstruction may be heavier than committing frozen fixtures for every cohort row. Scenario: The companion labeled set is small and fixed. A manifest of frozen ballot+plan+diff per row satisfies acceptance replay with less reconstruction logic and fewer truncation or heading-shape failure modes.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: plan.txt:91-101
- **Phase**: design



### OOS_6: Prompt-only rubric and lens fixes do not change 2-of-3 accept_finding quorum, so plan-mandated findings can still fail panel acceptance when validity and pragmatism vote NO even if plan-fidelity YES-rate improves.
- **Description**: Prompt-only rubric and lens fixes do not change 2-of-3 accept_finding quorum, so plan-mandated findings can still fail panel acceptance when validity and pragmatism vote NO even if plan-fidelity YES-rate improves.. Scenario: Operators may interpret improved plan-fidelity calibration as guaranteed panel acceptance for plan-mandated missing-test findings. Real findings stay blocked on other axes.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/voting.py:1190-1198
- **Phase**: design



### OOS_7: [OUT_OF_SCOPE] Prompt and rubric fixes do not change 2-of-3 accept_finding quorum; plan-mandated findings can still fail panel acceptance when validity and pragmatism vote NO even after plan-fidelity YES improves
- **Description**: [OUT_OF_SCOPE] Prompt and rubric fixes do not change 2-of-3 accept_finding quorum; plan-mandated findings can still fail panel acceptance when validity and pragmatism vote NO even after plan-fidelity YES improves. Scenario: Real plan-mandated missing-test findings may remain panel-rejected despite higher plan-fidelity YES-rate; acceptance criterion only measures v2 axis
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/voting.py:1190-1198
- **Phase**: design



### OOS_8: [OUT_OF_SCOPE] Required acceptance replay depends on live Codex or Cursor availability at PR time with no offline or recorded-vote fallback
- **Description**: [OUT_OF_SCOPE] Required acceptance replay depends on live Codex or Cursor availability at PR time with no offline or recorded-vote fallback. Scenario: CI or reviewer environments without the historical external tool cannot run the mandatory before/after replay; merge gate becomes environment-dependent rather than repo-verifiable
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: plan.txt:229-230
- **Phase**: design



