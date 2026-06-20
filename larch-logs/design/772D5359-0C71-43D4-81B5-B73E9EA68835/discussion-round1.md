## Decision 1: #4884 fix scope and operator-facing report behavior
- **Question**: Report-side, source-side, or both? Deterministic relabel/annotate vs. semantic/LLM suppression?
- **Resolution**: **Both, deterministic report.** Report-side = deterministically relabel the Step 4 "Unimplemented Plan Review Suggestions" section so it no longer implies a real gap, and annotate it as "considered but not adopted (often already addressed)". Entries stay listed; there is **NO** semantic/LLM suppression and no fragile heuristic that could drop genuine gaps. Source-side = add a reviewer-prompt instruction to verify a concern is not already addressed in the current plan before raising it (and confirm later-round reviewers receive the latest `plan.txt`).
- **Source**: user

## Decision 2: #4838 breadcrumb removal scope
- **Question**: Remove the pre-launch static `📊 Reviewers:` table only, or the whole reviewer status table?
- **Resolution**: Remove **only** the pre-launch static all-pending (⏳) table that prints before the panel launches. **Keep** the post-notification table that shows real ✅/❌/⊘ statuses after the panel completes (it reflects reality and has value). The SKILL.md "exactly twice" cadence becomes "once, post-notification".
- **Source**: user

## Decision 3: Audit scope across /design and /implement
- **Question**: Fix clearly-stale breadcrumbs in both /design and /implement now, or only /design and OOS the rest?
- **Resolution**: In this change, remove unambiguously-stale pre-launch breadcrumbs found in **both** /design and /implement. Defer any ambiguous ones to OOS rather than guessing.
- **Source**: user

## Decision 4: Audit-artifact fidelity (hard constraint)
- **Question**: Should the on-disk `rejected-findings.md` (committed to the run log for audit) be modified, or only the operator-facing emit?
- **Resolution**: Leave on-disk `rejected-findings.md` untouched (audit fidelity; matches the existing `emit_rejected_findings` contract that the on-disk file is left as-is). Change only the operator-facing presentation (the section label/annotation the orchestrator prints) and the reviewer prompts.
- **Source**: codebase

## Decision 5: Non-goal — review churn dynamic
- **Question**: Is the round-sum churn / plan-doubling (run-to-cap) dynamic in scope?
- **Resolution**: No. The issue explicitly defers that to the #4808 umbrella. This change is review-phase **output hygiene** only (report label + reviewer prompt + breadcrumb removal). Do not touch continuation/round-cap logic.
- **Source**: user (issue text)

## Decision 6: Hard constraints — tests + lint
- **Question**: What validation must this change preserve?
- **Resolution**: Keep existing identity-key suppression tests green; add regression coverage in `python/test_plan_review.py` for the relabel/annotate report behavior. Run `make lint`, and (Python files change) `make py-lint` + `make py-test`. Per `.claude/rules/launcher-argv-test-coverage.md`, any `python/cli.py plan-review` output-grammar change needs same-PR harness updates.
- **Source**: codebase
