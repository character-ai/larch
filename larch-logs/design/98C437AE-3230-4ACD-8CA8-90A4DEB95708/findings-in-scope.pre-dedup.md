### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:7-27,41
- **Concern**: Plan leaves `/research` explicitly out of `SCOPE_PATTERNS` and then adds a test that codifies that exemption, so the four documented research background fences stay unmarked and the lint still cannot force future `/research` backgrounds to carry bg-wait markers.. Scenario: The PR would still ship with the exact gap called out in `skills/research/references/research-phase.md` and `skills/research/references/validation-phase.md`: `run_in_background: true` launches that never get a bg-wait marker check.
- **Proposed resolution**: Include `skills/research/**/*.md` in the lint scope, or add equivalent marker coverage for those research launches before preserving any exemption.



### FINDING_2:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/research/references/research-phase.md:133-159; skills/research/references/validation-phase.md:110-144
- **Concern**: Plan keeps `/research` out of `SCOPE_PATTERNS`, so the four existing background launches in the research docs stay unlinted and future `/research` background fences can still bypass bg-wait coverage.. Scenario: The PR would ship with the original coverage gap intact for `/research`; a future research lane can still add `run_in_background: true` without a marker and evade the storm-safety lint.
- **Proposed resolution**: Extend the lint scope to include `skills/research/**/*.md` and add markers for the four existing launches, or encode an explicit exemption only if `/research` is truly out of spec for this guarantee.



### FINDING_3:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_bg_wait_coverage.py:12-17
- **Concern**: Keeping `skills/research/**/*.md` out of `SCOPE_PATTERNS` leaves the four existing `/research` background launches unguarded, and the proposed regression test would lock that exemption in.. Scenario: The PR would still ship with the exact coverage gap the issue describes, so future `/research` background fences can keep bypassing bg-wait marker enforcement.
- **Proposed resolution**: Add `skills/research/**/*.md` to `SCOPE_PATTERNS` and arm markers for the four research fences, or explicitly convert those launches so they are no longer backgrounded.



### FINDING_4:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_bg_wait_coverage.py:39-87
- **Concern**: A single brainstorm mapping keyed only on `python/cli.py`, `agent`, `launch-review`, `--timing-task-kind`, and `-brainstorm` is too broad for a substring matcher.. Scenario: A future unrelated `launch-review` fence that happens to use a `*-brainstorm` timing kind would slip past lint, weakening the guarantee that every new backgrounded fence must carry a marker.
- **Proposed resolution**: Add two explicit mappings, one for the framing fence and one for the scope fence, keyed on their unique prompt or output-path tokens so only those two commands match.



### FINDING_5:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_bg_wait_coverage.py:13-27; python/tests/lint/test_lint_bg_wait_coverage.py:37-42
- **Concern**: The plan explicitly keeps `skills/research/**` out of `SCOPE_PATTERNS` and adds a regression test that `/research` stays unlinted, so the four known research background launches remain uncovered.. Scenario: A future backgrounded `/research` fence can still bypass bg-wait coverage, leaving the feature's stated “every real `run_in_background: true` launch maps to a marker” criterion unmet.
- **Proposed resolution**: Add `skills/research/**/*.md` to `SCOPE_PATTERNS`, arm bg-wait markers for the four research launches, and remove the test that cements the exemption.



### FINDING_6:
- **Reviewer(s)**: Codex-dyn-Lint Scope Auditor
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:18-26; python/larch/lint/lint_bg_wait_coverage.py:129-133; skills/design/references/brainstorm.md:75-85
- **Concern**: A single brainstorm CommandMapping cannot stay narrow and still cover both launch shapes under the current all-token matcher. If it relies only on shared tokens like `-brainstorm`, unrelated future `agent launch-review` fences can slip through; if it adds per-slot output tokens, one mapping will miss one of the two current commands.. Scenario: A future backgrounded launch-review fence with the same timing suffix but no bg-wait marker could be falsely accepted, so the lint would no longer enforce the “every future fence must add a marker” contract.
- **Proposed resolution**: Define two slot-specific mappings, one for framing and one for scope, keyed on unique prompt or output tokens for each fence, or extend the matcher to support explicit per-slot alternatives without broad shared tokens.



