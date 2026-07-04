### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/research/test_research_eval.py
- **Concern**: Testing strategy omits bullet-after-no-findings rejection case. Scenario: The plan Edge cases require rejecting a no-findings phrase plus bullet findings, but Testing strategy lists only headings pass, thin narration fail, and mixed-line fail. A too-permissive helper could accept template-shaped headers with a bullet finding and still pass substantive validation.
- **Proposed resolution**: Add an explicit negative case: ### In-Scope Findings, No in-scope issues found., then a bullet finding line; assert validate_research_output returns 2 in validation_mode.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/research/test_research_eval.py
- **Concern**: No negative test for bare no-findings line without section headers. Scenario: The plan requires a strict allowlist with ### In-Scope Findings plus exact No in-scope issues found., but the listed tests do not pin rejection of the bare sentence alone. A substring or single-line matcher could accept thin outputs without the shipped template shape and weaken substantive gating.
- **Proposed resolution**: Add a negative case where the body is only No in-scope issues found. with no section header; assert validation_mode returns 2.



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/research/research_eval.py:410-424
- **Concern**: Prose allowlist omits exact-line NO_ISSUES_FOUND for multi-line reviewer bodies. Scenario: Reviewers trained on dynamic scaffold or legacy prompts may emit ### In-Scope Findings / No in-scope issues found. / ### Out-of-Scope Observations / NO_ISSUES_FOUND. Whole-file NO_ISSUES_FOUND is already accepted, but a four-line body fails the new allowlist, still scores 7/30 words, and stays NOT_SUBSTANTIVE so TRIVIAL static coverage can fail again
- **Proposed resolution**: Add NO_ISSUES_FOUND as an exact allowlisted line in the validation-mode prose helper (same strict line-equality rule as other tokens)



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/research/test_research_eval.py:48-68
- **Concern**: Testing strategy omits rejection regressions for two plan edge cases. Scenario: The plan Edge cases section requires rejecting No in-scope issues found, but ... and no-findings prose coexisting with TSV rows or bullet findings. Without explicit tests, an overly broad matcher can slip through and recreate failure mode 1 (lazy or partial output passes validation)
- **Proposed resolution**: Add focused validation-mode tests that assert exit code 2 for those two rejection shapes in test_validation_mode_sentinels_and_thresholds or a sibling test



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/larch/research/research_eval.py:410-425
- **Concern**: Prose fast path should pin first nonblank line to ### In-Scope Findings. Scenario: Shipped reviewer-templates.md and agents/reviewer-edge-cases.md require the response to begin with that header. Allowlisting the header without requiring it first would accept a bare No in-scope issues found. line and weaken the anti-narration contract the matcher is meant to enforce
- **Proposed resolution**: Require the first trimmed line to be exactly ### In-Scope Findings before accepting the prose no-findings template; add a one-line negative test for headerless prose **1. [correctness]** `python/larch/research/research_eval.py` — The allowlist should include exact-line `NO_ISSUES_FOUND`, not only `No out-of-scope observations.` variants. Multi-line bodies with an OOS sentinel still fail today’s 30-word floor; without this token, a valid no-findings response can remain `NOT_SUBSTANTIVE`. **2. [correctness]** `python/tests/research/test_research_eval.py` — The plan’s Edge cases section names two rejection shapes, but Testing strategy does not require tests for them. Add explicit exit-code-2 coverage so a too-broad matcher cannot regress. **3. [latent/correctness]** `python/larch/research/research_eval.py` — Require the first nonblank line to be `### In-Scope Findings` so the fast path matches the shipped template and does not accept headerless five-word prose. **Assessment:** The validation-layer fix is the right minimum-change root cause repair; prompt-only or threshold-only alternatives would be less reliable. The proposed collector regression test is proportionate E2E coverage for the reported `panel-failed` path. No finding targets current-state behavior the plan already fixes.



### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/agents/_review_launcher.py:945-1045
- **Concern**: The no-work Cursor guard stays sentinel-only while the new validation-mode path will accept prose no-findings output.. Scenario: A low-input Cursor slot can still emit "No in-scope issues found." from the reviewer template, and collect-results will score it OK instead of downgrading it to CURSOR_DEGRADED_RESPONSE, so a broken reviewer can be counted as clean and suppress fallback.
- **Proposed resolution**: Teach _review_cursor_normalize_no_issues() and _review_cursor_result_is_no_issues() to recognize the same prose no-findings shape, or normalize that prose to the existing JSON sentinel before validation.



