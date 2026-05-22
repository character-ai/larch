# Review Round 3

- Mode: `diff`
- Accepted findings: 11
- Rejected findings: 0
- Exonerated findings: 8
- Neutral findings: 1

## Accepted Findings

### FINDING_1: Step 5 docs misdescribe review_panel and --panel forwarding
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Normative text and sibling contract docs still tie SIMPLE/HARD or session-env to `review_panel=hard` and/or forwarding `--panel hard` via `run-step5-review.sh`, but the launcher no longer defines or emits `review_panel`; maintainers grepping the script get a false model and contradict argv/session-env debugging. The unified hard panel behavior lives downstream (e.g. `review-and-fix` / `review-core`), while `run-step5-review` should be described as round-cap / session-env / argv assembly only.
- **Suggested revision**: Rewrite [skills/implement/SKILL.md](skills/implement/SKILL.md) Step 5 prose and [scripts/run-step5-review.md](scripts/run-step5-review.md) contract bullets to describe `ROUND_CAP` from `POST_PLAN_WORKFLOW_PATH` plus any degraded inflation, and attribute hard-panel selection to `review-and-fix` / `review-core`; treat `--panel` as internal past the public `review-and-fix` argv surface where applicable.


### FINDING_10: README /fix-issue row documents removed flags
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Features table still documents `--auto/--inline/--hard` after removal from the skill, misleading operators and downstream doc mirrors.
- **Suggested revision**: Align [README.md](README.md) `/fix-issue` row with [skills/fix-issue/SKILL.md](skills/fix-issue/SKILL.md) and sweep literals for stale tokens.


### FINDING_11: README vs SKILL `argument-hint` vs harness disagree on /implement argv
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: README documents argv that the SKILL front matter / `argument-hint` may not declare (or tests pin a shorter hint), causing integration confusion and brittle CI.
- **Suggested revision**: Make one canonical argv string across [README.md](README.md), [skills/implement/SKILL.md](skills/implement/SKILL.md) (`argument-hint` / flags table), [scripts/test-implement-positional-issue.sh](scripts/test-implement-positional-issue.sh), and [.claude-plugin/plugin.json](.claude-plugin/plugin.json) if it duplicates the surface.


### FINDING_12: test-run-step1-plan-log harness may be stale for issue-body plan materialization
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Planned harness updates appear missing from the diff; Step 1 issue-anchored plan behavior could regress without CI noticing if pins still reflect manifest-era assumptions.
- **Suggested revision**: Update [scripts/test-run-step1-plan-log.sh](scripts/test-run-step1-plan-log.sh) assertions for issue-body plan materialization or replace pins with equivalent coverage elsewhere.


### FINDING_13: test-design-driver lacks tier/budget mapping pins
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Only comment disclaimers; `--trivial/--simple/--hard` and sketch budget / quick-mode mapping can drift while `make test-design-driver` stays green.
- **Suggested revision**: Add grep pins in [skills/design/scripts/test-design-driver.sh](skills/design/scripts/test-design-driver.sh) for tier flags and run-param mapping as intended.


### FINDING_16: test-plan-adequacy-audit omits reviewer XML envelope pins
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Missing `<reviewer_issue_body>` pin risks silent drift of the untrusted-wrap contract.
- **Suggested revision**: Add grep coverage for `reviewer_issue_body` (and optional preamble phrase) in [scripts/test-plan-adequacy-audit.sh](scripts/test-plan-adequacy-audit.sh).


### FINDING_2: compress-skill still implies /implement runs /design internally
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Wording suggests a merge path where `/implement` self-invokes `/design`, which can cause double design runs or the belief that `/implement` self-heals missing plans.
- **Suggested revision**: State the prerequisite flow explicitly (`/design` then `/implement` only) and remove nested/self-healing design wording in [skills/compress-skill/SKILL.md](skills/compress-skill/SKILL.md).


### FINDING_21: clarify-label.sh swallows `gh label create` failures
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Unconditional `|| true` can hide auth/network/permission failures until later steps fail or state diverges silently.
- **Suggested revision**: Treat “label already exists” as benign; propagate other `gh label create` failures (optionally preflight with `gh label list`).


### FINDING_26: Plan text vs implementation disagree on literal Step 4a vs find-lock delegation
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Plan C.4 may describe literal `plan-block-read` in SKILL while behavior delegates via `find-lock-issue --require-plan-block`, causing doc/plan fidelity drift even if behavior matches.
- **Suggested revision**: Align plan/SKILL/docs to the delegated sequence or restore the explicit Step 4a block for fidelity.


### FINDING_7: Forked runs may query the wrong GitHub repo without explicit upstream `--repo`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt
- **Concern**: Preflight and Step 1 issue/plan reads can omit explicit upstream `--repo` while fork mode treats the positional issue as upstream-only after fork-env; in a fork clone `gh` may default to `origin`, causing wrong/missing plan reads, wrong feature context, and incorrect audit/clarify targeting.
- **Suggested revision**: When `forked_target=true`, derive `UPSTREAM_REPO` before Preflight and pass `--repo` consistently to `gh issue view`, `plan-block-read.sh`, `clarify-state.sh`, `clarify-comment-post.sh`, `clarify-label.sh`, and Step 1 feature fetch paths as appropriate.


### FINDING_8: agnix-fix delimiter-wrapped FEATURE_FILE guidance does not match /implement consumption
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Dev skill prose builds delimiter-wrapped `FEATURE_FILE`, but `/implement` overwrites feature description from `gh issue view` and may not consume the file, weakening the assumed trust boundary versus operator expectations.
- **Suggested revision**: Remove/replace the step with guidance that matches `/implement` Preflight trust wraps, or restore a supported, documented file hand-off consumed by `/implement`.


