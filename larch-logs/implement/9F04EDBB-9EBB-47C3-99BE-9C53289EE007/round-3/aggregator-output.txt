Here is the normalized structured finding list (merged by shared behavioral risk; stable IDs in first-seen order; reviewer filenames preserved as source slots).

```text
### FINDING_1: Step 5 docs misdescribe review_panel and --panel forwarding
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Normative text and sibling contract docs still tie SIMPLE/HARD or session-env to `review_panel=hard` and/or forwarding `--panel hard` via `run-step5-review.sh`, but the launcher no longer defines or emits `review_panel`; maintainers grepping the script get a false model and contradict argv/session-env debugging. The unified hard panel behavior lives downstream (e.g. `review-and-fix` / `review-core`), while `run-step5-review` should be described as round-cap / session-env / argv assembly only.
- **Suggested revision**: Rewrite [skills/implement/SKILL.md](skills/implement/SKILL.md) Step 5 prose and [scripts/run-step5-review.md](scripts/run-step5-review.md) contract bullets to describe `ROUND_CAP` from `POST_PLAN_WORKFLOW_PATH` plus any degraded inflation, and attribute hard-panel selection to `review-and-fix` / `review-core`; treat `--panel` as internal past the public `review-and-fix` argv surface where applicable.

### FINDING_2: compress-skill still implies /implement runs /design internally
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Wording suggests a merge path where `/implement` self-invokes `/design`, which can cause double design runs or the belief that `/implement` self-heals missing plans.
- **Suggested revision**: State the prerequisite flow explicitly (`/design` then `/implement` only) and remove nested/self-healing design wording in [skills/compress-skill/SKILL.md](skills/compress-skill/SKILL.md).

### FINDING_3: Branch bundles unrelated product work with large run-log churn
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: One branch/PR aggregates multiple independent fixes plus a large `larch-logs` ship, which complicates review, bisect, revert attribution, and release-note scoping.
- **Suggested revision**: Split unrelated fixes across PRs/commits; keep `CHANGELOG` bullets tightly scoped per concern; keep issue-scoped diffs focused when possible.

### FINDING_4: Design skill clarify guidance risks cross-skill drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Loop/audit/clarify prose can drift from `/implement` Preflight and other skills unless anchored to a single normative doc.
- **Suggested revision**: Cross-link or anchor clarify steps to [docs/issue-anchored-plan.md](docs/issue-anchored-plan.md) (or a local design checklist) from [skills/design/SKILL.md](skills/design/SKILL.md) where loops reference implement behavior.

### FINDING_5: Stale /implement `--issue` examples after positional cutover
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Operator-facing examples/comments still show `/implement --issue …`, which mis-copies into scripts and external docs after the positional issue tail contract.
- **Suggested revision**: Update [skills/fix-issue/scripts/find-lock-issue.md](skills/fix-issue/scripts/find-lock-issue.md) and header/comments in [skills/fix-issue/scripts/find-lock-issue.sh](skills/fix-issue/scripts/find-lock-issue.sh) to positional `/implement <issue-N>` phrasing consistently.

### FINDING_6: [OUT_OF_SCOPE] Optional plan probe widens lock-helper SRP
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: A plan probe inside a multi-purpose lock script slightly increases single-responsibility surface; acceptable trade for atomic “no lock without plan,” mainly a future-refactor note.
- **Suggested revision**: No change required for this review scope; if refactors later split concerns, consider duplicating the probe at the SKILL layer instead of growing the helper.

### FINDING_7: Forked runs may query the wrong GitHub repo without explicit upstream `--repo`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt
- **Concern**: Preflight and Step 1 issue/plan reads can omit explicit upstream `--repo` while fork mode treats the positional issue as upstream-only after fork-env; in a fork clone `gh` may default to `origin`, causing wrong/missing plan reads, wrong feature context, and incorrect audit/clarify targeting.
- **Suggested revision**: When `forked_target=true`, derive `UPSTREAM_REPO` before Preflight and pass `--repo` consistently to `gh issue view`, `plan-block-read.sh`, `clarify-state.sh`, `clarify-comment-post.sh`, `clarify-label.sh`, and Step 1 feature fetch paths as appropriate.

### FINDING_8: agnix-fix delimiter-wrapped FEATURE_FILE guidance does not match /implement consumption
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Dev skill prose builds delimiter-wrapped `FEATURE_FILE`, but `/implement` overwrites feature description from `gh issue view` and may not consume the file, weakening the assumed trust boundary versus operator expectations.
- **Suggested revision**: Remove/replace the step with guidance that matches `/implement` Preflight trust wraps, or restore a supported, documented file hand-off consumed by `/implement`.

### FINDING_9: Exit code 3 is both normative and overloaded for automation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Public/normative text may disagree on audit refusal exit semantics (e.g. references to exit 0 vs exit 3), while exit 3 is also overloaded across sub-states (e.g. clarify posted vs ambiguous state without GH mutations), so wrappers inspecting only `$?` cannot branch correctly.
- **Suggested revision**: Reconcile exit semantics everywhere normative (single contract), and either split sub-cases into distinct exit codes or emit one machine-parseable outcome token on stdout before exit for each sub-case.

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

### FINDING_14: test-implement-post-design-boundary dropped missing-manifest failure-path assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Refactor may drop stdout contract checks for `read-design-manifest.sh` failure paths (e.g. breadcrumbs), letting regressions slip past CI.
- **Suggested revision**: Restore a small hermetic failure-path assertion in [scripts/test-implement-post-design-boundary.sh](scripts/test-implement-post-design-boundary.sh) or relocate with a cross-reference to a manifest-focused test.

### FINDING_15: test-fix-issue-bail-detection has a weak substring pin for issue forwarding
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Asserting bare `$ISSUE_NUMBER` can false-pass if the positional tail is removed but the number appears elsewhere in the Step 5a window.
- **Suggested revision**: Pin a distinctive args template proving last-token issue forwarding in [skills/fix-issue/scripts/test-fix-issue-bail-detection.sh](skills/fix-issue/scripts/test-fix-issue-bail-detection.sh).

### FINDING_16: test-plan-adequacy-audit omits reviewer XML envelope pins
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Missing `<reviewer_issue_body>` pin risks silent drift of the untrusted-wrap contract.
- **Suggested revision**: Add grep coverage for `reviewer_issue_body` (and optional preamble phrase) in [scripts/test-plan-adequacy-audit.sh](scripts/test-plan-adequacy-audit.sh).

### FINDING_17: [OUT_OF_SCOPE] docs/skills.md argv drift cannot be confirmed from captured diff
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: If it mirrors README skill tables, it may be stale, but diff evidence alone is insufficient.
- **Suggested revision**: Manually verify/sync [docs/skills.md](docs/skills.md) against README if it duplicates tables.

### FINDING_18: [OUT_OF_SCOPE] Large committed implement run logs add review noise
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Large `larch-logs/implement/**` diffs are expected committed artifacts per run-log policy; not a functional regression signal by themselves.
- **Suggested revision**: No functional action unless reviewing log content quality specifically.

### FINDING_19: Clarify comment may succeed while label add fails, stalling label-gated loops
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Partial GitHub mutations can leave `needs-design-clarification` missing while clarify comments exist, causing `/implement` exit-3 repair notes but design automation that keys on the label to stall.
- **Suggested revision**: Align entry conditions with state-driven fallbacks, document mandatory label repair ordering/idempotency, or adjust design skill loop triggers to not depend solely on label presence.

### FINDING_20: Fixed XML delimiter names around untrusted GitHub content (prompt-injection shaping)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Malicious issue content could echo closing tags and weaken delimiter-separated instruction boundaries for audit prompts.
- **Suggested revision**: Use per-run random sentinel delimiters in [skills/implement/SKILL.md](skills/implement/SKILL.md) audit prose (or another robust framing strategy consistent with repo policy).

### FINDING_21: clarify-label.sh swallows `gh label create` failures
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Unconditional `|| true` can hide auth/network/permission failures until later steps fail or state diverges silently.
- **Suggested revision**: Treat “label already exists” as benign; propagate other `gh label create` failures (optionally preflight with `gh label list`).

### FINDING_22: [OUT_OF_SCOPE] `--repo` forwarded to `gh` without argv hardening
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Only matters if untrusted actors can supply argv; typical operator threat model treats argv as trusted.
- **Suggested revision**: If threat model requires it, validate `OWNER/REPO` format or use `gh` env indirection in clarify/plan helper scripts.

### FINDING_23: [OUT_OF_SCOPE] SECURITY.md already states GitHub content is not neutralized for injection
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Pre-existing explicit non-goal; optional cross-link to audit wrap limits.
- **Suggested revision**: Optional documentation cross-link only; no required change for this PR scope.

### FINDING_24: [OUT_OF_SCOPE] fix-issue SKILL wording still ties normalization to removed /implement flags
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Minor confusion: helper-oriented phrasing references `--issue` alongside removed `/implement --issue`; no runtime impact asserted.
- **Suggested revision**: Clarify helpers may use `--issue` while `/implement` is positional.

### FINDING_25: Inserting a new numbered NEVER rule risks stable NEVER# references drifting
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Inserting a new NEVER #10 shifts subsequent NEVER numbers, desyncing external citations and internal references.
- **Suggested revision**: Avoid renumbering: add as sub-bullet, placeholder body per plan constraints, or a non-numbered anchor instead of inserting a new numbered NEVER at the insertion point.

### FINDING_26: Plan text vs implementation disagree on literal Step 4a vs find-lock delegation
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Plan C.4 may describe literal `plan-block-read` in SKILL while behavior delegates via `find-lock-issue --require-plan-block`, causing doc/plan fidelity drift even if behavior matches.
- **Suggested revision**: Align plan/SKILL/docs to the delegated sequence or restore the explicit Step 4a block for fidelity.

### FINDING_27: [OUT_OF_SCOPE] aggregate-findings validator/harness changes outside cutover plan scope
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Unless coupled failures appear, these changes are not required for plan fidelity of the cutover issue itself.
- **Suggested revision**: None unless failures force coupling.
```
