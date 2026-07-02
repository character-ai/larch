### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan: Files to modify/create / MAY_UPDATE: python/skill-closure-baseline.json
- **Concern**: Issue acceptance requires ratcheted panel-tier token reduction, but baseline commit is optional. Scenario: Implementer can compress prose, run skill-closure report showing lower panel-tier tokens, and still skip baseline regen because MAY_UPDATE allows it; lint skill-closure-growth only blocks growth, so acceptance is not mechanically enforced and later churn can erase savings
- **Proposed resolution**: Promote baseline update to firm when panel-tier closure_content_estimated_tokens decreases: regenerate via make regen-skill-closure-baseline and commit python/skill-closure-baseline.json; treat report-only as insufficient for done



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan: Approach / Testing strategy
- **Concern**: Plan conflates runtime render_voter_main savings with panel-tier acceptance metric. Scenario: python/larch/lint/lint_skill_closure_growth.py scan_panel_tier counts agents/*.md, skills/shared/reviewer-templates.md, and skills/shared/voting-protocol.md only; rendering.py is not in that set, so heavy compression there does not move panel-tier tokens while issue acceptance is panel-tier ratchet
- **Proposed resolution**: Add an explicit completion gate: panel-tier closure_content_estimated_tokens must drop versus baseline (driven primarily by skills/shared/voting-protocol.md); treat rendering.py compression as runtime-only benefit called out separately in the PR



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/shared/voting-protocol.md:85-112 / python/larch/rendering/rendering.py:1137-1163
- **Concern**: Parallel voter prose in the fenced template and render_voter_main lacks a post-compression sync check beyond OOS sites. Scenario: Independent folding of the template fence and runtime static blocks can drift on severity floor, default-deny, or anti-style lines while OOS four-site parity passes; voters follow runtime text, maintainers follow voting-protocol
- **Proposed resolution**: Add implementation-note step: after edits, diff compressed in-scope voter guidance between the fence block and render_voter_main static prelude (not only the OOS paragraph quad)



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/shared/voting-protocol.md:81-96
- **Concern**: Fenced voter template still embeds stale OOS YES criteria that diverge from the canonical paragraph. Scenario: Line 83 routes OOS votes through the OOS Acceptance Rubric materiality gate; line 96 inside the template fence still says vote YES when concrete/important enough with file:line or repro signals. A density pass that only shortens line 83 or line 96 independently can leave contradictory OOS guidance in one doc and reintroduce the remedy/materiality confusion the edge cases warn about.
- **Proposed resolution**: In the ### UPDATED voting-protocol.md step, require reconciling line 96 with line 83: keep structural YES/NO meanings and the render-voter pointer, delete the redundant concrete/important-enough substitute, and fold any kept OOS template prose into the same compressed canonical wording used at rendering.py:1161-1163.



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/tests/rendering/test_rendering.py:1019-1034
- **Concern**: No test pins the OOS remedy-informational boundary that the plan treats as failure-prone. Scenario: Tests pin panel severity rubric and immediate-action strings but not OOS text such as informational only or do not vote NO because you disagree. render_voter_main OOS paragraphs at rendering.py:1161-1163 are explicit edit targets with zero regression guard, so compression can drop the remedy boundary while pytest still passes.
- **Proposed resolution**: Add one minimal substring assertion in test_rendering.py for the OOS remedy rule on both finding-only and finding-oos renders, e.g. informational only plus disagree with the proposed fix, alongside the existing severity-rubric pins.



### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/lint/test_lint_skill_closure_growth.py:979-996
- **Concern**: `python/skill-closure-baseline.json` is optional even though shrinking `skills/shared/voting-protocol.md` makes the committed baseline stale. Scenario: The plan’s core change reduces the panel-tier source set, but the freshness test asserts the committed baseline equals a fresh scan in both directions; leaving the baseline unchanged can pass the one-way growth lint while failing the Python test suite
- **Proposed resolution**: Promote `python/skill-closure-baseline.json` from `MAY_UPDATE` to `UPDATED`, regenerate it after the prose compression, and keep the full generated file in the PR



### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/lint/lint_skill_closure_growth.py:543-576
- **Concern**: Plan omits that panel-tier acceptance is measured only from agents/*.md, reviewer-templates.md, and voting-protocol.md. Scenario: Heavy compression of render_voter_main static prose can look successful in runtime prompts while panel-tier closure_content_estimated_tokens barely moves, so the issue acceptance criterion can fail even with a green lint skill-closure-growth run (lint only blocks growth above baseline)
- **Proposed resolution**: Add an explicit acceptance gate: before/after skill-closure report must show panel-tier closure_content_estimated_tokens (and closure_lines) strictly below the pre-edit snapshot; note render_voter_main output is outside the panel-tier scan and voting-protocol.md is the primary ratcheted source in this PR



### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/tests/rendering/test_rendering.py:1019-1026
- **Concern**: Testing strategy pins panel severity rubric substrings but not the mandatory nit severity floor or OOS remedy-informational boundary called out in plan Edge cases. Scenario: A prose pass can drop "do not vote NO because you disagree with the proposed fix" or the in-scope nit floor while test_render_voter_includes_panel_severity_rubric still passes, changing voter behavior without CI catching it
- **Proposed resolution**: Extend planned test_rendering.py pins to cover at least the OOS remedy-disagreement guard and the in-scope nit severity-floor sentence (both id-grammar branches), matching the plan's own failure-mode list



### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:135-139
- **Concern**: Testing strategy claims tally coverage but omits the actual tally harnesses required by acceptance.. Scenario: The listed command runs voting plus findings-ledger tests, but skips existing tally coverage in python/tests/review/test_review_tally.py and plan-review tally cases in python/tests/review/test_plan_review.py, so the plan cannot demonstrate "Voting and tally harnesses pass."
- **Proposed resolution**: Add the focused tally harnesses to the command, for example python3 -m pytest python/tests/review/test_voting.py python/tests/review/test_review_tally.py python/tests/review/test_plan_review.py -k tally_plan_review; keep python/tests/review/test_findings_ledger.py only if ledger coverage is still desired.



### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-review-structure.sh:407-415
- **Concern**: Testing strategy omits test-review-structure.sh grep pins on voting-protocol.md OOS Security Tag prose. Scenario: The plan targets OOS-section compression in skills/shared/voting-protocol.md, but scripts/test-review-structure.sh (20a)-(20c) require exact substrings such as the security-tagged findings guard, Match discrimination procedure, and Security counter-invariant clause. Compressing that subsection can fail CI even when pytest voting/rendering suites pass.
- **Proposed resolution**: Add make test-review-structure (or bash scripts/test-review-structure.sh) to Testing strategy and note that the OOS Security Tag bullets must keep those three pinned phrases byte-stable.



### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/lint/lint_skill_closure_growth.py:543-576
- **Concern**: Plan does not tie issue acceptance to panel-tier closure measurement excluding render_voter_main. Scenario: Issue acceptance requires token reduction on the ratcheted panel tier, but scan_panel_tier counts only agents/*.md, skills/shared/reviewer-templates.md, and skills/shared/voting-protocol.md. python/cli.py render voter output from render_voter_main is not in that metric, so large rendering.py savings alone would not satisfy acceptance even though that is the per-slot runtime payload.
- **Proposed resolution**: State explicitly that acceptance requires a before/after python3 python/cli.py skill-closure report showing lower panel-tier closure_estimated_tokens driven by skills/shared/voting-protocol.md edits, and treat render_voter_main compression as complementary runtime savings verified via updated test_rendering.py assertions.



### FINDING_12:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:135-139; Makefile:554-555,886-887
- **Concern**: Testing strategy omits the repository tally harnesses required by the acceptance criteria. Scenario: The feature acceptance says voting and tally harnesses pass, but the plan's tally command runs test_voting.py plus test_findings_ledger.py. The Makefile names the actual plan-review and code-review tally harnesses as test-tally-plan-review and test-tally-code-votes, so a parser-facing prose/template regression in those tally paths could ship unverified.
- **Proposed resolution**: Add the focused tally harnesses to the testing strategy, preferably make test-tally-plan-review test-tally-code-votes, or their equivalent pytest slices, alongside the existing render and voting tests.



