# Review Round 1

- Mode: `diff`
- 12 accepted, 4 rejected (2 exonerated)

## Accepted Findings

### FINDING_1: AGENTS.md Conventions missing explicit BASH_AUTHORING §4 cross-reference
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: The Conventions section does not include an explicit bullet cross-referencing BASH_AUTHORING §4 (foreground fenced markers, NEVER #16, lint contract) next to existing `run_in_background` / Monitor / polling guidance, so operators who rely on Conventions may miss the normative pointer the plan/acceptance called for.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_10: BASH_AUTHORING “first vs additional anchor” prose may disagree with per-anchor linter behavior
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Documentation around first vs subsequent anchor comments may not match the linter’s per-anchor rules, confusing authors about the second-comment requirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_12: Parse-only / execution-negative harness case missing vs contract doc
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: A promised parse-only execution-negative case is not asserted in the harness, so doc/CI contract drift could allow accidental execution of fence snippets without a failing test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_14: `skills/implement/SKILL.md` Step 8 prose vs strict `**Filed URL**` gate
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Terminal disposition prose can read as if generic GitHub URLs in artifacts satisfy the gate, while strict counting ignores incidental design Description URLs—risk of confusing Step 8 failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_17: `.timing-task-kind-allowlist.md` understates Check 16 structural scope
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Rule text describes Check 16 too narrowly (dialectic retry kinds loop), understating markdown SKILL pins exercised by `test-design-structure.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_2: BASH_AUTHORING.md §4 under-specified vs acceptance (WHY, exceptions, title)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Section 4 omits acceptance-oriented rationale (e.g. breadcrumbs, turn-boundary, issue #2454, NEVER #16, FD visibility framing) and explicit Family A / Monitor carve-outs relative to binding acceptance text; title/depth may not match what the plan treated as normative.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_3: Family A regression harness targets wrong files / baselines vs plan
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: The Family A regression relies on SKILL.md grep counts (or an equivalent contract) instead of the four named reference paths from the plan, so drift in sketch-launch / dialectic / voting strings could slip through while unrelated SKILL edits could trip counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_4: CHANGELOG release notes omit foreground-marker / lint contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: The [42.0.10] changelog entry reads as OOS/disposition-only and does not surface the new foreground-marker lint/CI contract, so consumers may miss the behavior change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_5: Unterminated bash fence at EOF can skip anchor / denylist enforcement
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: When parsing ends inside an open fence (`in_fence`), anchor/denylist scanning may not run on buffered content, so truncated or malformed SKILL.md could exit clean while evading enforcement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_6: `make lint-foreground` vs shipped `lint-foreground-markers` naming drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Acceptance/playbooks refer to `lint-foreground` while the repo exposes `lint-foreground-markers`, causing “missing target” friction and doc/plan wording drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_8: `if`/`while` anchor regex may miss `if !` before a denylisted script (false negative)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: The anchor classification regex may not cover negated `if` forms before a script path without `CLAUDE`, risking false negatives versus planned `if`-test coverage unless carved out or documented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_9: Harness lacks planned fixtures / scenario matrix for `lint-foreground-markers.sh`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Concern**: Several planned harness scenarios (parse-only safety, multi-anchor, fence edge cases, command substitution, env-prefix, heredoc, commented-out forms, prose-only paths, etc.) are absent or incomplete, so refactors could reintroduce execution of fence bodies or loosen detection without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


