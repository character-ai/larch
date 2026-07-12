### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_commit_route.py
- **Concern**: Step 5 resume and review reuse classifiers are conflated. Scenario: The plan assigns one Step 5 canonical classifier with full handoff keys to both adapters. Today `step-5-review.sh` clears stall envelopes (including zero-rc stall) and relaunches, while `step-5-resume.sh` treats `STEP5_REVIEW_STATUS` in {complete, stall} with `BGJOB_RC=0` as reusable and waits. Sharing the review classifier on resume would refuse valid MAV resume results; sharing the resume classifier on review would reuse stale stall envelopes instead of relaunching.
- **Proposed resolution**: Split validation in `dispatch_commit_route.py`: port `step5_canonical_result_env_state` for `implement-step5-review` and `step5_resume_result_env_state` for `implement-step5-resume`; call the matching classifier before `start_or_reattach` on each parent. Add resume-specific reuse/clear tests in `test_implement_dispatch.py` or a resume harness.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/bgjob/model.py
- **Concern**: `JobSpec` extension is missing from the plan file list. Scenario: The plan adds caller-owned `merge_result_env` and `initial_merge_rows` on `JobSpec`, but only lists `python/larch/bgjob/adapt.py`. `JobSpec` is defined in `model.py`, and `daemon.write_result` reads `spec.merge_result_env`. Omitting `model.py` invites an adapt-only shim or an incomplete typed contract.
- **Proposed resolution**: Add `### UPDATED: python/larch/bgjob/model.py` with `initial_merge_rows` on `JobSpec` (and any validation helpers). Wire the field through `adapt._prepare_launch_spec` and parent `JobSpec` builders in `dispatch_commit_route.py`.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/tests/bgjob/test_bgjob_adapt.py
- **Concern**: Foundation adapt changes lack a mandated test deliverable. Scenario: The plan updates `adapt.py` with caller-selected merge paths and atomic `initial_merge_rows`, and the testing strategy says to run bgjob adapt tests, but no `### UPDATED: python/tests/bgjob/test_bgjob_adapt.py` row exists. Without new cases, truncation/seed preservation and custom merge-path behavior are unverifiable in CI.
- **Proposed resolution**: List `python/tests/bgjob/test_bgjob_adapt.py` as updated. Add cases for caller `merge_result_env`, `initial_merge_rows` surviving launch prep, and live-reattach with only seeded identity rows.



### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/implement/dispatch_commit_route.py
- **Concern**: Step 5 resume merge publication contract is unspecified. Scenario: The plan pins review to `IMPLEMENT_TMPDIR/.step5-review-result.env`, but resume today uses `bgjob/implement-step5-resume.merge.env` and child mode atomically tees worker stdout (checks relay, `NEXT_ACTION`, commit KVs, review loop output) into that merge file. The plan does not state which merge path resume uses or that tee/publication must move into Python child mode. Reusing the review merge path or relying on `review_and_fix.py` file writes alone would drop resume merge rows and break `bgjob wait` envelopes for MAV and `--checks-site` paths.
- **Proposed resolution**: Document and implement separate resume `JobSpec.merge_result_env` and child publication: tee captured stdout into the merge env for `implement-step5-resume`, keep `.step5-review-result.env` for review only, and test `--checks-site` plus ready-to-commit commit-route relay rows in the shared merge env.



### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/bgjob/model.py:21-35
- **Concern**: JobSpec has no planned initial_merge_rows field, although the plan requires typed adapter specs to carry atomic identity seeds. Scenario: Dispatch cannot construct the specified JobSpec; a workaround can omit CHECKS_INPUT_* rows and break live rejoin identity validation
- **Proposed resolution**: Add initial_merge_rows to JobSpec with validated row typing, and list model.py in the plan



### FINDING_6:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_commit_route.py:planned JobSpec construction
- **Concern**: The plan does not preserve the existing explicit owner-PID fallback when constructing adapter specs. Scenario: Without LARCH_CLAUDE_PID or CLAUDE_PID, daemon.owner_identity_from_env fails before launch, so converted adapters emit an error instead of starting
- **Proposed resolution**: Derive the owner identity with the existing LARCH_CLAUDE_PID-or-PPID policy and test the missing-environment fallback



### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/bgjob/model.py
- **Concern**: The plan extends JobSpec in adapt.py with caller-owned merge_result_env and initial_merge_rows, but model.py is not listed. JobSpec is defined only in model.py today.. Scenario: An implementer can update adapt.py alone, leave JobSpec untyped, and either fail to compile or bolt initial_merge_rows onto adapt-local structs. That breaks the shared bgjob contract other callers rely on.
- **Proposed resolution**: Add ### UPDATED: python/larch/bgjob/model.py with merge_result_env retention and initial_merge_rows on JobSpec, plus validation helpers used by adapt launch preparation.



### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_commit_route.py
- **Concern**: Child-mode merge publication for step-5-resume, run-step-checks, and step-6-entry is not spelled out. Bash child modes tee or tmp+mv worker stdout into --merge-result-env; only review-and-fix writes .step5-review-result.env directly.. Scenario: bgjob publish merges spec.merge_result_env at daemon exit. If the Python child path only prints KVs to stdout, resume and checks composite runs can finish with an empty or identity-only merge file. bgjob wait then lacks NEXT_ACTION, checks relay rows, or STEP5_REVIEW_STATUS even when worker output looked successful.
- **Proposed resolution**: In each child entrypoint, require an atomic merge writer around the worker: capture stdout rows or explicit KV tuples, validate launch identity when CHECKS_INPUT_* seeds exist, write integrity-failure rows on drift, and replace merge_result_env via tmp+mv before exit. State this beside the --checks-site and checks identity bullets.



### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/tests/bgjob/test_bgjob_adapt.py
- **Concern**: The plan changes adapt launch semantics (caller merge paths and initial_merge_rows) but does not list bgjob adapt regression tests. test_bgjob_adapt.py currently asserts only the default bgjob/<step>.merge.env path and empty truncation.. Scenario: Completed reuse, live rejoin, and fresh launch can regress to the old behavior: adapt ignores caller merge_result_env, truncates away CHECKS_INPUT_* seeds, or publishes without preserved rows. make py-test can pass while implement adapters ship broken.
- **Proposed resolution**: Add ### UPDATED: python/tests/bgjob/test_bgjob_adapt.py covering caller-selected merge_result_env, initial_merge_rows surviving truncation, child flag forwarding to the same path, and merge-row publication after child writes.



### FINDING_10:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/bgjob/model.py:21-31
- **Concern**: Plan requires extending JobSpec with initial_merge_rows, but omits the file that defines JobSpec. Scenario: Dispatch cannot construct the required atomic identity seed, so checks rejoin can lose CHECKS_INPUT_* rows and violate the feature contract
- **Proposed resolution**: Add python/larch/bgjob/model.py to the firm file set and extend JobSpec, updating affected constructors and tests 1. **[correctness] `python/larch/bgjob/model.py:21-31`** The plan extends `JobSpec` with `initial_merge_rows` but does not include the file that defines it. Without that field, dispatch cannot pass atomic identity seeds to `bgjob adapt`, so checks reattachment can lose `CHECKS_INPUT_*` rows. Add the model update and affected constructor/test changes.



### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/bgjob/model.py
- **Concern**: JobSpec extension is not listed in the plan file set. Scenario: The plan says to extend JobSpec with caller-owned merge_result_env and initial_merge_rows under python/larch/bgjob/adapt.py, but JobSpec is defined in python/larch/bgjob/model.py. A literal adapt.py-only edit cannot add typed fields without either changing model.py or introducing a parallel spec type that dispatch_commit_route.py and tests must also learn.
- **Proposed resolution**: Add ### UPDATED: python/larch/bgjob/model.py with initial_merge_rows (and any validated merge-path fields) on JobSpec, and keep adapt.py launch prep consuming that typed surface.



### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_commit_route.py:step5_resume_main
- **Concern**: Step 5 resume child merge publication is underspecified. Scenario: Current step-5-resume.sh child mode tees all worker stdout into bgjob/implement-step5-resume.merge.env. That merge path is not .step5-review-result.env; review-and-fix persists there but resume completion still depends on stdout KVs such as STEP5_REVIEW_STATUS, NEXT_ACTION, and commit-route relays from checks-step5-resume and commit-route. A child mode that only forwards subprocesses without atomic merge-env capture will leave the daemon with an empty or partial merge env and bgjob wait will miss required Step 5 resume KVs.
- **Proposed resolution**: Specify that step5_resume_main --bgjob-child must mirror the bash tee contract: capture the full worker stdout stream (checks-site composite, ready-to-commit commit-route branch, and review-and-fix resume) into the adapter merge env before exit, and add a regression that asserts STEP5_REVIEW_STATUS and NEXT_ACTION land in implement-step5-resume.merge.env after child completion.



### FINDING_13:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/bgjob/model.py:21-30
- **Concern**: `JobSpec` change is assigned to the wrong file. Scenario: `model.JobSpec` has no `initial_merge_rows` field, so planned construction fails or launch identity seeds cannot reach `adapt`
- **Proposed resolution**: Add `python/larch/bgjob/model.py` as UPDATED and define the typed, defaulted field there



### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/bgjob/model.py:20-30
- **Concern**: JobSpec initial_merge_rows field missing from firm file list. Scenario: Plan adds initial_merge_rows under adapt.py only; JobSpec lives in model.py so the typed contract cannot land cleanly
- **Proposed resolution**: Add ### UPDATED: python/larch/bgjob/model.py extending JobSpec with initial_merge_rows and wire adapt.py to it



### FINDING_15:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_commit_route.py
- **Concern**: Checks child launch-identity argv not specified alongside merge seeding. Scenario: Step 6 and run-step-checks child modes require --repo-root and --launch-head/--launch-fp/--launch-schema for validate_child_identity; seeding CHECKS_INPUT_* rows alone does not satisfy child argv contract
- **Proposed resolution**: Require parent JobSpec.command to forward launch-identity flags and Step 6 original args in addition to initial_merge_rows seeding



### FINDING_16:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-5-resume.sh:102-127
- **Concern**: Step 5 resume reuse validation not distinguished from review canonical classifier. Scenario: Review reuse requires full handoff keys; resume reuse today accepts DONE with only STEP5_REVIEW_STATUS plus STEP/BGJOB_RC; one classifier applied to both steps can break resume or accept stale partial resume results
- **Proposed resolution**: Port separate reuse validators for implement-step5-review vs implement-step5-resume and add resume-specific adapter tests



### FINDING_17:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/tests/bgjob/test_bgjob_adapt.py:146-154
- **Concern**: adapt foundation tests omitted from firm file list. Scenario: Caller merge paths and initial_merge_rows change adapt launch prep; existing tests assume default merge path and empty truncate
- **Proposed resolution**: Add ### UPDATED: python/tests/bgjob/test_bgjob_adapt.py covering caller merge paths and preserved initial_merge_rows



### FINDING_18:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/bgjob/model.py:21-31
- **Concern**: The accepted identity-seed fix omits the file that defines `JobSpec`. Scenario: The plan requires `initial_merge_rows` on `JobSpec`, but `model.py` is absent from the firm file set. Construction will fail or identity rows cannot reach `adapt`, so checks seeds are erased.
- **Proposed resolution**: Add `### UPDATED: python/larch/bgjob/model.py` and define the typed, defaulted `initial_merge_rows` field.



