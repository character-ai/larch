### FINDING_1: Capture lifecycle title prefix token before branching
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Step 0b documents a bare `if title_has_lifecycle_reject_prefix "$ISSUE_TITLE"` even though the predicate writes the matched token to stdout. That can leak raw stdout and leaves the stderr template without the actual token substitution. The prose should capture the token first, branch on whether it is non-empty, and use the captured value in the rejection banner.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: Bash title-skip mirror can drift from jq archival filter
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `title_skipped_by_bash_mirror` re-implements archival prefix semantics instead of deriving them from `LARCH_TITLE_ARCHIVAL_PREFIX_JQ_FILTER`. Future changes to the jq filter could leave the bash mirror stale while tests still pass, letting production list filtering diverge from the harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Export contract for title eligibility constants is inconsistent
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The contract and acceptance text imply four exported constants, but only `LARCH_TITLE_ARCHIVAL_PREFIX_JQ_FILTER` is exported. Either the three bash regex constants should be exported too, or the documentation and acceptance language should be narrowed to sourced-only visibility plus the exported jq fragment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_4: Run Logs Audit Report fixture disagrees with plan intent
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The plan lists `[Run Logs Audit Report …]` as a report hit, while the harness and jq/bash grammar currently treat it as a miss because `Report` must abut `]`. This mismatch can confuse future maintainers and may either preserve an unintended miss or cause someone to “fix” the test in a way that breaks jq parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_5: Step 6 loses title-prefix brainstorm auto-enable
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Step 0b sub-step 2.5 can auto-enable brainstorm from a `Brainstorm:` issue title, but Step 6 reinitializes `brainstorm_requested` from argv/upgrade paths only. `/design --simple N` on a brainstorm-prefixed issue can print the auto-enable banner, persist `brainstorm_requested=false`, and skip Step 1d.5.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_6: Brainstorm reference omits title-prefix trigger
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `skills/design/references/brainstorm.md` does not mention Step 0b sub-step 2.5 title-prefix auto-enable as a Step 1d.5 trigger. Operators may see the auto-enable banner but then read documentation that only explains argv or other triggers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_7: Already-planned ad-hoc Q&A gate ignores title-prefix brainstorm
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The already-planned ad-hoc Q&A branch only checks argv `--brainstorm`, not `brainstorm_requested` from the Step 0b 2.5 title-prefix path. A brainstorm-prefixed issue with an existing `larch:plan` can therefore skip mandatory Step 1d.5 in branch (b).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_8: Harness does not cover stale CLAUDE_PLUGIN_ROOT fallback
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `scripts/test-lib-title-eligibility.sh` does not exercise `list-issues.sh` plugin root resolution when `CLAUDE_PLUGIN_ROOT` is stale. A broken repo-root fallback could fail at runtime while the title eligibility harness still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: nocasematch restore may leak shell option state
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `shopt -p nocasematch` restore handling may be unreliable on Bash 3.2, allowing `nocasematch` to leak in a long-lived sourced shell after lifecycle checks. That can affect later `=~` checks unexpectedly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_10: Predicate ordering for lifecycle plus brainstorm titles is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The harness does not simulate the mandatory Step 0b 2.5 predicate short-circuit order. A future reorder could pass structure checks while breaking combined titles such as `[DESIGNING] Brainstorm: foo`, where lifecycle rejection should take precedence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: Bare Brainstorm title fixture is missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The brainstorm hit fixtures omit the standalone title `Brainstorm`. A regression that breaks end-of-string matching for the bare prefix could pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_12: Structure test does not pin title eligibility library sourcing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `test-design-structure.sh` check (20) does not assert that `skills/design/SKILL.md` sources `lib-title-eligibility.sh`. The source line could be removed while other anchors still satisfy the test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: Title-prefix brainstorm auto-enable lacks explicit user confirmation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Step 0b sub-step 2.5 enables external brainstorm slots from the issue title alone. In a multi-writer repo, another collaborator could rename an issue with a `Brainstorm:` prefix, causing `/design` to launch Cursor/Codex brainstorm flows without an explicit argv opt-in from the operator.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
