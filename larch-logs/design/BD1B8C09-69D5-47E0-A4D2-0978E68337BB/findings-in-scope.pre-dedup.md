### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-5-resume.sh:108-112
- **Concern**: [SCOPE-REDUCTION] Planned commit-route delegation omits errexit-safe stdout capture under set -euo pipefail. Prior round-4 neutral finding still applies; the plan replaces the inline commit-fixes block but never requires the existing set +e / capture / set -e guard.. Scenario: The wrapper runs with set -euo pipefail. When implement commit-route exits non-zero without NEXT_ACTION (stall-seed failure, usage error, malformed envelope), errexit aborts before commit_output is captured or NEXT_ACTION/COMMIT_OUTCOME KVs are relayed. The orchestrator then cannot hit lacks-envelope branch 3 and may mis-route to generic Step 5 preflight. scripts/test-implement-structure.sh:369 pins the old guard and the plan drops that needle without a commit-route replacement.
- **Proposed resolution**: In step-5-resume.sh, wrap commit-route in the same set +e capture block used today (capture commit_output and commit_rc, then set -e). Parse NEXT_ACTION from commit_output before branching. Add a structure-harness pin requiring set +e around implement commit-route --site step5-resume-handoff capture.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/implement_dispatch.py:486-543
- **Concern**: _step5_resume_commit_phase lacks an explicit NEXT_ACTION=stall fail-closed return when commit-route process rc is 0.. Scenario: The plan mirrors step8_oos_checkpoint (rc 0 whenever NEXT_ACTION is emitted). After refactor, commit_route can return 0 with NEXT_ACTION=stall. _step5_resume_commit_phase today returns None only when commit succeeds; if it maps success to commit_rc==0 only, it returns None and step5_resume_main proceeds to review-and-fix step5 after a seeded commit-phase stall. That violates plan line 86 and breaks Python parity with the shell wrapper, which exits before step5 on NEXT_ACTION=stall.
- **Proposed resolution**: Specify that _step5_resume_commit_phase (and step5_resume_main) treat NEXT_ACTION=stall as a terminal commit-phase failure: relay commit KVs and NEXT_ACTION=stall, return a non-zero exit (e.g. 1) without calling review-and-fix step5, even when the shared commit-route helper returned process rc 0. Extend test_step5_resume_* to assert NEXT_ACTION=stall, no step5 relaunch, and non-zero step5_resume_main rc.



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-5-resume.sh:108-112
- **Concern**: Planned commit-route delegation omits errexit-safe stdout capture under set -euo pipefail. Scenario: The plan replaces the inline commit-fixes block with bare implement commit-route parsing but never requires the existing set +e / capture / set -e guard. Under set -euo pipefail a non-zero commit-route return without NEXT_ACTION (stall-seed failure, usage error, invalid envelope) aborts the wrapper before stdout is captured or NEXT_ACTION/COMMIT_OUTCOME are relayed, so the orchestrator cannot reach lacks-envelope branch 3 and may mis-route to generic preflight failure. The structure harness update drops the pin at scripts/test-implement-structure.sh:369 without adding an errexit-safe commit-route replacement.
- **Proposed resolution**: Add an explicit step-5-resume.sh requirement: wrap commit-route invocation in set +e, capture commit_output and commit_rc, then set -e before parsing NEXT_ACTION; relay stdout on all paths. Add a matching scripts/test-implement-structure.sh pin for that capture block (or forbid bare unguarded commit-route substitution).



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:113-124
- **Concern**: Self-review and Step 7 invalid commit-route envelopes lack terminal STALL_TRACKING / Step 18 routing. Scenario: The plan adds invalid-envelope fail-closed prose for self-review and Step 7 (log to Warnings, do not proceed) but unlike resume-handoff lacks-envelope branch 3 it never sets STALL_TRACKING=true or skip to Step 18. On seed failure or malformed stdout (no NEXT_ACTION) those foreground fences can halt mid-Step-5/7 without the teardown/stall-recovery path that COMMIT_OUTCOME failures and resume-handoff invalid envelopes use, stranding the session without Step 18 cleanup.
- **Proposed resolution**: Align self-review and Step 7 invalid-envelope handling with resume branch 3: after logging Warnings, set STALL_TRACKING=true with the site stall_step, skip to Step 18 (durable bail may be absent when seed failed), and add matching structure-harness pins so invalid-envelope prose is not only do-not-proceed.



### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-5-resume.sh:92-101
- **Concern**: Planned commit-route delegation omits errexit-safe stdout capture under set -euo pipefail. Scenario: The plan swaps the inline commit-fixes block for bare implement commit-route without set +e / capture / set -e. On seed failure, usage error, or other non-zero return with no NEXT_ACTION, errexit aborts before stdout is captured or NEXT_ACTION/COMMIT_OUTCOME KVs are relayed, so the orchestrator cannot reach lacks-envelope branch 3 and may misclassify envelope-invalid as generic preflight failure. scripts/test-implement-structure.sh:369 still pins the old errexit pattern with no replacement pin for commit-route.
- **Proposed resolution**: In step-5-resume.sh require the same set +e commit_output capture / commit_rc / set -e guard around implement commit-route; parse NEXT_ACTION from captured stdout. In scripts/test-implement-structure.sh replace the retired commit-fixes errexit needle with a pin requiring that guard around commit-route.



### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:113-124
- **Concern**: Self-review and Step 7 invalid-envelope prose omits Step 18 routing present on resume-handoff lacks-envelope branch 3. Scenario: Plan branch 3 routes missing/duplicated/malformed/non-zero-without-NEXT_ACTION to preflight/resume failure and skip to Step 18. Self-review and Step 7 only say log Warnings and do not proceed. On commit-route seed failure or usage error (no NEXT_ACTION), foreground fences can halt mid-run without Step 18 teardown/stall-recovery that today's COMMIT_OUTCOME failure paths always reach.
- **Proposed resolution**: Align self-review and Step 7 invalid-envelope handling with resume branch 3: after logging, set prompt-side STALL_TRACKING/STALL_STEP when durable seed is absent, then skip to Step 18; do not fall through or end the turn silently. ## Findings ### 1. [correctness] `skills/implement/scripts/step-5-resume.sh` The plan replaces the inline `commit-fixes` block with a direct `implement commit-route` call but never carries forward the `set +e` / capture / `set -e` guard that exists today at lines 108–112. Under `set -euo pipefail`, a non-zero `commit-route` exit without `NEXT_ACTION` (stall-seed failure, usage error, malformed envelope) can terminate the wrapper before stdout is captured or relayed, so lacks-envelope branch 3 never runs. **Suggested revision:** Wrap `implement commit-route` in the same errexit-safe capture pattern; parse `NEXT_ACTION` from captured stdout. Update `scripts/test-implement-structure.sh` to pin that guard (replacing the obsolete line-369 `commit-fixes` needle). ### 2. [risk-integration] `skills/implement/SKILL.md` (self-review and Step 7) Resume-handoff lacks-envelope branch 3 routes invalid commit-route envelopes to preflight/resume failure and **skip to Step 18**. Planned self-review and Step 7 blocks only say log to `Warnings` and do not proceed; they never route to Step 18. That drops the teardown path today's `COMMIT_OUTCOME` failure handling always uses when `commit-route` returns non-zero without `NEXT_ACTION` (e.g. seed failure after a failed commit). **Suggested revision:** Mirror resume branch 3 on self-review and Step 7: invalid envelope → log, set `STALL_TRACKING` / `STALL_STEP` when durable seed is absent, skip to Step 18. --- **Not re-raised (already in plan or prior ledger):** Step 7 `NEXT_ACTION=stall` → Step 18 (plan lines 119–124, harness line 144); `NEXT_ACTION` relay and redacted failure logging; wrapper exit 1 on relayed stall (intentional, prior rejections); stdout-before-exit-code binding (prior rejection).



### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-5-resume.sh:108-112
- **Concern**: Planned commit-route delegation omits errexit-safe capture under set -euo pipefail. Scenario: The plan swaps the inline commit-fixes block for bare implement commit-route without set +e / capture / set -e. scripts/test-implement-structure.sh:369 pins that guard today. Under set -euo pipefail a non-zero commit-route return without NEXT_ACTION (stall-seed failure, usage error) aborts the wrapper before stdout is captured or NEXT_ACTION is relayed, so the orchestrator cannot reach lacks-envelope branch 3 and may mis-route to generic preflight.
- **Proposed resolution**: Add set +e around commit-route capture in step-5-resume.sh (mirror today's commit-fixes block). Migrate scripts/test-implement-structure.sh:369 to require the same guard around implement commit-route --site step5-resume-handoff when dropping the commit-fixes errexit pin.



### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:115-124
- **Concern**: Self-review and Step 7 invalid-envelope paths omit explicit Step 18 skip. Scenario: The plan requires fail-closed handling for missing/duplicated/malformed/non-zero-without-NEXT_ACTION on self-review and Step 7 foreground fences but only says log Warnings and do not proceed. Resume-handoff lacks-envelope branch 3 routes invalid envelopes to the preflight/resume failure path (STALL_TRACKING, STALL_STEP=5, skip to Step 18). Invalid commit-route envelopes on self-review/Step 7 can halt mid-run without Step 18 teardown/stall recovery, regressing today's COMMIT_OUTCOME failure path that always skipped to Step 18.
- **Proposed resolution**: Align self-review and Step 7 invalid-envelope prose with resume branch 3: log Warnings, set STALL_TRACKING=true and site-appropriate STALL_STEP, skip to Step 18. Add matching structure-harness pins alongside the planned invalid-envelope fail-closed needles.



### FINDING_9:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/implement_dispatch.py (plan.txt:40-47,68-70)
- **Concern**: Resume porcelain failure can lose the required Tool Failures log. Scenario: The issue scope moves the whole commit-failure tree into commit-route, including execution-issues logging. The plan's ok/noop porcelain branch seeds durable stall and emits NEXT_ACTION=stall, but only the COMMIT_OUTCOME failure branch calls _commit_route_log_failure and the porcelain tests assert only state. A dirty/probe-failed resume handoff can then reach Step 18 with durable state but no committed failure log.
- **Proposed resolution**: Route the resume-handoff porcelain failure through the same bounded diagnostic and _commit_route_log_failure --redact path before emitting NEXT_ACTION=stall, and pin that in the porcelain failure tests.



