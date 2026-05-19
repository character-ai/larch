### FINDING_1: **Important** (`risk-integration`, `plan` / `requirements`) — [`skills/implement/SKILL.md`](skills/implement/SKILL.md) (Step 7a “Pre-bump log flush” / adjacent guidance, ~lines 1659–1711 in the diff): The umbrella `<feature_description>` and plan Part B ask for `write-final-report.sh` **before** Step 8 by inserting it into Step 7a **before** `larch-log.sh commit`. The branch instead **documents that Step 7a must not** call `write-final-report.sh` (because `ship-pr-state.sh` / `PR_URL` are not available yet) and routes the fix through [`scripts/refresh-run-logs.sh`](scripts/refresh-run-logs.sh) and [`scripts/ship-pr.sh`](scripts/ship-pr.sh) (`run_pr_create_phase` after `state_set_many PR_NUMBER`/`PR_URL`). That is a deliberate **architecture swap** vs the written AC. **Concrete scenario:** anyone or any checklist validating the issue text literally against `SKILL.md` will mark the work incomplete even if runtime behavior is fixed; any implement path that reaches merge **without** hitting those helpers could still reproduce the original “no `final-summary.md` in the pre-merge log commit” failure mode. **Suggested fix:** either update the issue / acceptance text to match the new contract, or add the Step 7a call behind a guard that still satisfies “PR_URL known” (e.g. only after first `ship-pr-state.sh` write), and add one integration-style test that asserts `final-summary.md` is present in the log tree before the post-merge sentinel for the success path you care about.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 1. **Important** (`risk-integration`, `plan` / `requirements`) — [`skills/implement/SKILL.md`](skills/implement/SKILL.md) (Step 7a “Pre-bump log flush” / adjacent guidance, ~lines 1659–1711 in the diff): The umbrella `<feature_description>` and plan Part B ask for `write-final-report.sh` **before** Step 8 by inserting it into Step 7a **before** `larch-log.sh commit`. The branch instead **documents that Step 7a must not** call `write-final-report.sh` (because `ship-pr-state.sh` / `PR_URL` are not available yet) and routes the fix through [`scripts/refresh-run-logs.sh`](scripts/refresh-run-logs.sh) and [`scripts/ship-pr.sh`](scripts/ship-pr.sh) (`run_pr_create_phase` after `state_set_many PR_NUMBER`/`PR_URL`). That is a deliberate **architecture swap** vs the written AC. **Concrete scenario:** anyone or any checklist validating the issue text literally against `SKILL.md` will mark the work incomplete even if runtime behavior is fixed; any implement path that reaches merge **without** hitting those helpers could still reproduce the original “no `final-summary.md` in the pre-merge log commit” failure mode. **Suggested fix:** either update the issue / acceptance text to match the new contract, or add the Step 7a call behind a guard that still satisfies “PR_URL known” (e.g. only after first `ship-pr-state.sh` write), and add one integration-style test that asserts `final-summary.md` is present in the log tree before the post-merge sentinel for the success path you care about.
- **Suggested revision**: Address the concern above.

### FINDING_2: **Important** `architecture` `skills/review/references/heavy-worker.md:65`  
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `architecture` `skills/review/references/heavy-worker.md:65`      The `/review --diff --subagent` contract still tells the heavy worker to write `review-summary.json` with `schema_version: 1` and no `panel` object. That path bypasses the updated `emit-tally.sh`, so standalone subagent reviews will continue producing summaries without `panel.scout_status`, `panel.static_slot_count`, `panel.dynamic_slot_count`, and `panel.total_slot_count`. Update the heavy-worker schema and return contract to match `emit-tally.sh` schema version 2.
- **Suggested revision**: Address the concern above.

### FINDING_3: **Important** `risk-integration` `scripts/ship-pr.sh:970`  
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `scripts/ship-pr.sh:970`      `write-final-report.sh` now runs after `create-pr.sh`, but `create-pr.sh` has already pushed the branch at `scripts/create-pr.sh:147-152`. The new `larch-log.sh commit` at `scripts/ship-pr.sh:996` creates a local log commit containing `final-summary.md`, but the clean happy path goes straight to CI/merge without another push, so GitHub merges the old remote head and the final summary is still absent from the merged run-log. Move final-summary rendering into a pre-push/pre-bump flush, or push the post-PR log commit before entering CI wait.
- **Suggested revision**: Address the concern above.

### FINDING_4: **Latent** (`risk-integration`, `plan`) — [`skills/review/scripts/review-core.sh:331-351`](skills/review/scripts/review-core.sh): On `THRESHOLD_OK=false` (`REVIEW_CORE_STATUS=panel-failed`), the script clears artifacts, flushes the round log, and `exit 2` **without** calling `emit-tally.sh`. The branch adds a structured `panel` block and bumps `schema_version` for paths that **do** emit (including the new zero-findings emit path), but **not** for threshold failures even though `dispatch-panel.sh` has already produced `SCOUT_STATUS`, `DYNAMIC_SLOTS`, and `STATIC_SLOT_COUNT`. **Concrete scenario:** automated or human analysis that only reads `review-summary.json` for scout/panel telemetry will see a missing or stale file exactly when the panel is degraded enough to stall Step 5—the case where observability is most useful. **Suggested fix:** invoke `emit-tally.sh` (with zeroed counts and current scout/slot args) before `exit 2` in the panel-failed branch, or document that `scout-roundN-status.env` is the canonical source when `review-summary.json` is absent.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 2. **Latent** (`risk-integration`, `plan`) — [`skills/review/scripts/review-core.sh:331-351`](skills/review/scripts/review-core.sh): On `THRESHOLD_OK=false` (`REVIEW_CORE_STATUS=panel-failed`), the script clears artifacts, flushes the round log, and `exit 2` **without** calling `emit-tally.sh`. The branch adds a structured `panel` block and bumps `schema_version` for paths that **do** emit (including the new zero-findings emit path), but **not** for threshold failures even though `dispatch-panel.sh` has already produced `SCOUT_STATUS`, `DYNAMIC_SLOTS`, and `STATIC_SLOT_COUNT`. **Concrete scenario:** automated or human analysis that only reads `review-summary.json` for scout/panel telemetry will see a missing or stale file exactly when the panel is degraded enough to stall Step 5—the case where observability is most useful. **Suggested fix:** invoke `emit-tally.sh` (with zeroed counts and current scout/slot args) before `exit 2` in the panel-failed branch, or document that `scout-roundN-status.env` is the canonical source when `review-summary.json` is absent.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] **(architecture)** [`larch-logs/implement/5F7568AE-E8DA-4B76-8E08-E03C1DA604FC/`](larch-logs/implement/5F7568AE-E8DA-4B76-8E08-E03C1DA604FC/) (new): Large committed run-log tree including `plan-goals-test.md` mirrors long-form plan text; per repo guidance this is intentional shipping noise, not a change-induced security issue.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **(architecture)** [`larch-logs/implement/5F7568AE-E8DA-4B76-8E08-E03C1DA604FC/`](larch-logs/implement/5F7568AE-E8DA-4B76-8E08-E03C1DA604FC/) (new): Large committed run-log tree including `plan-goals-test.md` mirrors long-form plan text; per repo guidance this is intentional shipping noise, not a change-induced security issue. --- **Commits** (`git merge-base HEAD main`..HEAD):   `865efffe` Fix review observability run-log artifacts · `c5c37d6e` chore(larch-logs): flush implement run 5F7568AE-… · `701101bb` / `af1dfe14` / `62467e26` Address code review feedback (rounds 1–3). No TSV block (no in-scope findings and no out-of-scope items that meet the “finding” bar with severity/focus/scenario/fix columns; observations above are contextual only).
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] **(risk-integration)** [`skills/implement/SKILL.md`](skills/implement/SKILL.md) (modified): The branch documents **not** calling `write-final-report.sh` in Step 7a and instead relies on [`scripts/refresh-run-logs.sh`](scripts/refresh-run-logs.sh) and [`scripts/ship-pr.sh`](scripts/ship-pr.sh) for an early `larch:final-summary` refresh. That diverges from the original Part (B) wording in the pasted `<feature_description>` / plan (Step 7a insertion). Out of scope as pre-existing “spec vs branch” unless you treat the feature tag as binding; it is not a direct security defect.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **(risk-integration)** [`skills/implement/SKILL.md`](skills/implement/SKILL.md) (modified): The branch documents **not** calling `write-final-report.sh` in Step 7a and instead relies on [`scripts/refresh-run-logs.sh`](scripts/refresh-run-logs.sh) and [`scripts/ship-pr.sh`](scripts/ship-pr.sh) for an early `larch:final-summary` refresh. That diverges from the original Part (B) wording in the pasted `<feature_description>` / plan (Step 7a insertion). Out of scope as pre-existing “spec vs branch” unless you treat the feature tag as binding; it is not a direct security defect.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] **Out of scope** (`risk-integration`) — Historical committed run logs under `larch-logs/implement/**/round-*/review-summary.json` still use `schema_version: 1` without `panel`; only new runs emit v2. That predates or is orthogonal to “new code wrong”; consumers must tolerate mixed versions when scanning the whole tree.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 1. **Out of scope** (`risk-integration`) — Historical committed run logs under `larch-logs/implement/**/round-*/review-summary.json` still use `schema_version: 1` without `panel`; only new runs emit v2. That predates or is orthogonal to “new code wrong”; consumers must tolerate mixed versions when scanning the whole tree. --- ```tsv schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix 1	in_scope	important	risk_integration	skills/implement/SKILL.md:1659-1711;scripts/refresh-run-logs.sh:171-172;scripts/ship-pr.sh:215-217	Part B fixes final-summary via refresh-run-logs and ship-pr pr-create instead of adding write-final-report to Step 7a before larch-log commit as required by feature_description and plan.	Issue AC or internal checklist that requires literal Step 7a ordering fails; any merge path that skips refresh-run-logs and pr-create timing could still miss final-summary in the intended pre-merge commit.	Reconcile acceptance text with the new architecture or implement Step 7a (or equivalent) with correct PR_URL timing plus an integration test for the success path. 2	in_scope	latent	risk_integration	skills/review/scripts/review-core.sh:331-351	panel-failed branch still skips emit-tally.sh so review-summary.json never gains schema_version 2 panel fields despite dispatch output.	Downstream consumers reading only review-summary.json get no scout_status or slot counts when the panel threshold fails—the stall case where telemetry matters most.	Call emit-tally with zero counts and scout args before exit 2 or document an alternate canonical artifact for this branch. 1	out_of_scope	nit	risk_integration	larch-logs/implement/*/round-*/review-summary.json (historical)	Older committed run logs remain schema_version 1 without panel.	Mixed-version scans across old and new runs need tolerant parsers.	None required for this branch; document consumer expectations if needed. ```
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] architecture: larch-logs/implement/5F7568AE-E8DA-4B76-8E08-E03C1DA604FC/plan-goals-test.md
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Shipped run-log embeds a plan snapshot that still describes Step 7a write-final-report while SKILL.md now forbids it. Confusing historical doc inside logs only. Out of scope per reviewer rules on larch-logs noise; optional editorial fix in a future log flush.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] architecture: skills/review/scripts/review-core.sh:331-351
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] panel-failed exit still skips emit-tally review-summary.json Structured summary absent on panel-failed path; unchanged by this branch’s primary observability goal. None required for this review scope.
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] architecture: skills/review/scripts/review-core.sh:501-518
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] main-agent-vote-required path still skips emit-tally. Observability gap versus zero-findings is pre-existing; this diff does not introduce it. Only if you want parity: emit a minimal summary on that exit path too.
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] code-quality: skills/review/scripts/review-core.sh:331-351
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] panel-failed path still skips emit-tally so no review-summary.json with panel. Pre-existing; not introduced by this diff. No action required for this branch unless product wants panel on threshold failure.
- **Suggested revision**: Address the concern above.

### FINDING_12: `62467e26` Address code review feedback (round 3)  
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - `62467e26` Address code review feedback (round 3)
- **Suggested revision**: Address the concern above.

### FINDING_13: `701101bb` Address code review feedback (round 1)  
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - `701101bb` Address code review feedback (round 1)
- **Suggested revision**: Address the concern above.

### FINDING_14: `865efffe` Fix review observability run-log artifacts  
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - `865efffe` Fix review observability run-log artifacts   Note: the supplied `diff.txt` ends mid-hunk inside `skills/review/scripts/test-review-core.sh` (around the `panel-failed` test); anything after that line in the real branch diff was not visible in the cache file.
- **Suggested revision**: Address the concern above.

### FINDING_15: `af1dfe14` Address code review feedback (round 2)  
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - `af1dfe14` Address code review feedback (round 2)
- **Suggested revision**: Address the concern above.

### FINDING_16: `c5c37d6e` chore(larch-logs): flush implement run 5F7568AE-E8DA-4B76-8E08-E03C1DA604FC  
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - `c5c37d6e` chore(larch-logs): flush implement run 5F7568AE-E8DA-4B76-8E08-E03C1DA604FC
- **Suggested revision**: Address the concern above.

### FINDING_17: code-quality: scripts/test-refresh-run-logs.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Stub setup expanded for write-final-report and tracking-issue-summary. More moving parts when write-final-report dependencies change. Consider a shared stub fragment or comment listing required stub contracts.
- **Suggested revision**: Address the concern above.

### FINDING_18: code-quality: skills/implement/SKILL.md:1679;scripts/refresh-run-logs.sh;scripts/ship-pr.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Part B was specified as adding write-final-report.sh to Step 7a before pre-bump larch-log commit; branch instead forbids Step 7a and splits logic across ship-pr + refresh-run-logs. Future edits can miss one hook and regress final-summary commit behavior while SKILL still reads coherent. Either align code with the written plan (single Step 7a call pattern) or update the plan/issue text to this multi-hook design and cross-link all three locations.
- **Suggested revision**: Address the concern above.

### FINDING_19: code-quality: skills/review-and-fix/scripts/review-and-fix.sh (render_rejected_findings_for_tally)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Tally helper strips markdown heading markers from Round sections. Consumers expecting markdown headings inside code-review-tally body see plain lines. Document intent next to the helper or preserve ## lines if downstream prefers markdown.
- **Suggested revision**: Address the concern above.

### FINDING_20: code-quality: skills/review-and-fix/scripts/review-and-fix.sh:635-730
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] write_rejected_findings_aggregate duplicates identical find|awk|sort pipelines. Drift between the two copies could change which rounds count as having full detail vs which get emitted. Factor the sorted round list into one variable or temp file reused by both loops.
- **Suggested revision**: Address the concern above.

### FINDING_21: code-quality: skills/review/scripts/dispatch-panel.sh (unchanged in diff)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Plan named dispatch-panel.sh as part of SCOUT_STATUS wiring; no diff hunk there. If main did not already export scout/slot vars consumed by review-core.sh panel fields stay at defaults despite dispatch. Confirm wiring on main or add the missing dispatch-panel.sh change.
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: skills/implement/SKILL.md:1679
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Part B plan (Step 7a write-final-report) not implemented; doc forbids Step 7a call Branch contradicts the supplied implementation plan and relocates behavior to refresh/pr-create. Reconcile docs/plan with chosen design or implement the plan’s Step 7a placement if that contract is load-bearing.
- **Suggested revision**: Address the concern above.

### FINDING_23: correctness: skills/implement/SKILL.md:Step_7a_pre-bump_block
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Implementation plan Part B required write-final-report.sh before larch-log.sh commit in Step 7a; diff forbids Step 7a and moves calls to refresh-run-logs.sh and ship-pr.sh. Operators or automation following the written plan would not match shipped behavior; plan checklist item for Part B is unmet as written. Reconcile plan and code: add Step 7a call as specified or update the plan/spec to the refresh/pr-create/Step_17_18 architecture.
- **Suggested revision**: Address the concern above.

### FINDING_24: correctness: skills/review-and-fix/scripts/review-and-fix.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] render_rejected_findings_for_tally heading strip is strict on line 1 Leading blank line or non-exact heading prevents strip; duplicate headings possible in tally body. Skip leading blanks / trim before matching the top heading.
- **Suggested revision**: Address the concern above.

### FINDING_25: correctness: skills/review/scripts/review-core.sh:394
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] New emit-tally.sh invocation in the zero-findings path runs under set -e. emit-tally.sh non-zero (bad tally path jq failure) turns a previously survivable zero-findings round into a hard failure before REVIEW_CORE_STATUS is emitted. Wrap emit in explicit rc handling (log + continue with degraded summary) or match previous best-effort semantics.
- **Suggested revision**: Address the concern above.

### FINDING_26: risk-integration: scripts/refresh-run-logs.sh:71-72
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] refresh invokes write-final-report before PR_URL exists on bump Trigger C First bump refresh runs before pr-create; write-final-report upserts tracking with PR N/A and larch-log commit may record final-summary with PR N/A until a later pre-push refresh. Gate GitHub upsert on PR_URL present or split local render from upsert; avoid calling full write-final-report pre-pr-create.
- **Suggested revision**: Address the concern above.

### FINDING_27: risk-integration: scripts/refresh-run-logs.sh:71-72
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] write-final-report couples GitHub upsert to every refresh CI/push retry loops multiply tracking-issue upserts vs token/timing-only refresh. Throttle upserts or separate markdown refresh from GitHub comment updates.
- **Suggested revision**: Address the concern above.

