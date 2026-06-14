# Review Round 1

- Mode: `diff`
- 4 accepted, 3 rejected (3 neutral)

## Accepted Findings

### FINDING_1: Fetch failure staging uses non-allowlisted bail-reason tokens
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `stage_failed_clarify` uses bail-reason `clarify-fetch-failed` and source-script `design-clarify`, which are not in stall-recovery generic allowlists. Fetch failure leaves `design-failure-terminal-state.env` unstaged; `design-failure-report.sh` writes missing-terminal-state fallback instead of filing a failed-clarify report.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use allowlisted clarify-hard-halt / clarify-loop tokens or extend stall-recovery allowlists and test staging


### FINDING_16: Route-state read failure exits 2 without staging or summary KVs
- **Reviewer(s)**: dyn-bash-contract-output.txt
- **Severity**: important
- **Concern**: When `.design-step0-route-state.env` exists but `read-result-env.sh` fails, the wrapper calls `fail` and exits 2 without writing fetch result env, emitting `SUMMARY_OUTCOME=failed-clarify`, or calling `stage_failed_clarify`. Other fetch failures exit 1 with staged terminal state and explicit summary KVs. Step 0b prose assumes non-zero fetch exits are `failed-clarify` with Final summary handling; exit 2 without `SUMMARY_OUTCOME` is an inconsistent integration surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-contract-output.txt: Treat unreadable route state like other fetch failures: write `.design-clarify-fetch-result.env`, call `stage_failed_clarify`, emit `CLARIFY_FETCH_STATUS=route-state-read-failed` and `SUMMARY_OUTCOME=failed-clarify`, then exit **1**.


### FINDING_2: SKILL.md omits publish non-zero orchestrator branches
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-clarify-flow-output.txt
- **Severity**: important
- **Concern**: SKILL documents Final summary only for fetch/plan-write failures and publish exit 0, not for publish-phase comment-post or label failures. After comment-post or label removal fails, the wrapper exits 1 with `SUMMARY_OUTCOME=failed-clarify` while the orchestrator may skip Final summary per SKILL. The old clarify branch documented a `design-step0-clarify-hard-halt.sh` path for unrecovered helper failure; that orchestration hook is gone without a publish-failure replacement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add explicit publish non-zero branches: parse SUMMARY_OUTCOME and run Final summary before exit
  - From cursor-specialist-edge-cases-output.txt: Document publish failure branches: parse CLARIFY_PUBLISH_STATUS/SUMMARY_OUTCOME from wrapper output, export SUMMARY_OUTCOME, run Final summary, then exit.
  - From dyn-clarify-flow-output.txt: Add an explicit orchestrator branch: on publish fence non-zero, parse `SUMMARY_OUTCOME` / `CLARIFY_PUBLISH_STATUS` from wrapper stdout (or `.design-clarify-publish-result.env`), run the Final summary block, and exit; restore or replace the hard-halt/staging contract for publish-side `failed-clarify`.


### FINDING_3: Publish overwrites handoff ISSUE_NUMBER without equality check
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-clarify-flow-output.txt, dyn-bash-contract-output.txt
- **Severity**: important
- **Concern**: Publish reloads request state but overwrites `ISSUE_NUMBER` with `--issue` without comparing it to the stored handoff value. A mismatched publish call can post a clarify response and mutate the plan block on the wrong GitHub issue while still using the fetch-time `REQUEST_ID`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Fail closed unless --issue matches stored ISSUE_NUMBER from fetch handoff
  - From cursor-specialist-edge-cases-output.txt: Fail closed when handoff ISSUE_NUMBER != --issue; optionally re-validate clarify state before comment-post.
  - From dyn-clarify-flow-output.txt: After sourcing request state, fail closed unless `"$ISSUE" = "${ISSUE_NUMBER}"` (and optionally re-validate `REQUEST_ID` against a fresh `clarify state` read) before any `named-block write`, `comment-post`, or `label` calls.
  - From dyn-bash-contract-output.txt: After loading `.design-clarify-request.env`, fail closed unless `--issue` matches the stored `ISSUE_NUMBER` (and keep using that single bound issue for every downstream `gh` call).


