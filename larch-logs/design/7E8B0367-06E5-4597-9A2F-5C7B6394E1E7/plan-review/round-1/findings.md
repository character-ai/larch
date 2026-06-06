### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-postplan-emit.sh:348-376
- **Concern**: skills/design/SKILL.md:981-983. Scenario: Drift guard is specified only in the standalone Step 2b.5 procedure, but Gate B post-apply and discussion re-emits use the merged `--with-plan-size` path that skips steps 1–6 and `_postplan_finish_merged_plan_size` exits 0 on under-threshold without reading `DRIFT_TRIGGER_FIRED`
- **Proposed resolution**: After Gate B applies findings the plan can grow past `LARCH_DESIGN_DRIFT_MULTIPLE` while still under hard caps; merged emit returns rc 0 and the operator never sees the drift `AskUserQuestion`, so the stated ratchet backstop on the main apply loop does not run Extend the merged finish path (e.g. new driver exit code after hard/partition checks) and mirror it in Step 2b and Gate B `case` arms in `SKILL.md` and `approval-gates.md`, or invoke the drift branch after every merged rc 0 under-threshold emit

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:1703-1887
- **Concern**: Plan deletes the multi-round while-loop (~1728–1887) but does not require collapsing the `ROUND_CAP_ARG_SEEN` legacy branch; `/design` always passes `--round-cap` via `run-step3-review.sh`. Scenario: Deleting only the while-loop leaves `--round-cap` callers with no review round (fall-through) or on the thin legacy path that omits `tally-error` / `degraded-empty-collector` / `zero-findings-degraded-panel` handling the plan says to keep
- **Proposed resolution**: Explicitly unify to one single-pass exit: remove the `ROUND_CAP_ARG_SEEN==0` gate, port the pre-revise terminal logic from the multi-round block into that path, then delete the while-loop and revise helpers

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-postplan-emit.sh:456-525
- **Concern**: Plan writes `drift-baseline.env` in the `--snapshot-original` branch using `PLAN_LINES` / `DIFF_LINES` from `check-plan-size.sh`, but snapshot runs at ~456–484 and `_postplan_run_plan_size` runs at ~524. Scenario: Implementer may write empty or stale baseline values, so drift ratios stay ~1× and `DRIFT_TRIGGER_FIRED` never fires after Gate B growth
- **Proposed resolution**: Write baseline after a `check-plan-size.sh` call (inline in snapshot branch or immediately after `_postplan_run_plan_size` on first `--snapshot-original` only) with a write-once guard; add the harness assertion already listed in Failure modes

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-removal-completeness
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-route.sh:322-335
- **Concern**: Plan removes `--manual-requested` from `write-design-current-env.sh` but does not list `design-route.sh`, which still jq-reads `manual_gate_b` and appends `--manual-requested true` on resume. Scenario: Resuming a pre-change session whose `run-params.json` still has `manual_gate_b: true` passes a removed flag; `write-design-current-env.sh` errors on unknown argv and `/design` resume aborts before the routed step
- **Proposed resolution**: Remove the `manual_gate_b` resume branch in `design-route.sh` and drop or replace the `test-design-structure.sh` pin at ~1547–1548

### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-postplan-emit.sh:20-41; skills/design/scripts/design-postplan-emit.sh:348-371; skills/design/references/approval-gates.md:157-158
- **Concern**: Merged post-plan fence has no proposed drift branch. Scenario: check-plan-size.sh may emit DRIFT_TRIGGER_FIRED=true after Gate B or discussion re-emits, but design-postplan-emit.sh still parses only hard/partition/soft fields and exits 0 as under-threshold, so the operator never gets the required Continue/Cancel prompt
- **Proposed resolution**: Add DRIFT_* parsing/result KVs and a distinct merged-fence drift status/exit after hard and partition checks; update the Step 2b/Gate B/discussion case arms to run the planned drift prompt before clean continuation

### FINDING_6:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-route.sh:322-335; skills/design/scripts/design-route.md:31
- **Concern**: Resume path still depends on removed manual surface. Scenario: A stale run-params.json with manual_gate_b=true makes design-route.sh append --manual-requested true to write-design-current-env.sh; the plan removes that writer flag, so paused/resumed pre-upgrade runs can fail during env refresh instead of treating manual_gate_b as harmless
- **Proposed resolution**: Remove the manual_gate_b read and --manual-requested append from design-route.sh, update design-route.md, and cover stale manual_gate_b resume as ignored

### FINDING_7:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/plan-review.md:46-58; skills/design/references/plan-review.md:173-195; README.md:59; docs/workflow-lifecycle.md:79-96
- **Concern**: Plan leaves normative and public docs advertising removed behavior. Scenario: Step 3 still mandates reading plan-review.md, which describes inner auto-apply, manual_gate_b, passive summary, and manual-mode application; README/workflow docs still advertise --manual even though parse-design-argv.sh will hard-error it
- **Proposed resolution**: Update plan-review.md and public /design argument docs to the single-pass, always-explicit Gate B contract in the same change that removes the flag

### FINDING_8:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-postplan-emit.sh:348-375
- **Concern**: Drift guard is wired only into standalone Step 2b.5 steps 1-6, but Gate B and discussion re-emits use merged `--with-plan-size`, which exits rc 0 on under-threshold without any drift check. Scenario: After Gate B apply (the main Gate-C re-review ratchet path), plan growth past `LARCH_DESIGN_DRIFT_MULTIPLE` never surfaces; thread 2 does not backstop the loop it targets
- **Proposed resolution**: Handle drift in `_postplan_finish_merged_plan_size` (emit `DRIFT_*` KVs / new rc) or invoke the drift branch after merged rc 0 in `approval-gates.md` and discussion-round2; update `design-postplan-emit.md` and Gate B `case` arms accordingly

### FINDING_9:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-postplan-emit.sh:348-375; skills/design/references/approval-gates.md:157-158; skills/design/references/discussion-rounds.md:126
- **Concern**: Drift guard is only specified for standalone Step 2b.5, but Gate B and discussion re-emits use the merged design-postplan-emit.sh fence and skip standalone Step 2b.5 on rc 0. Scenario: After Gate B apply or discussion-round2 grows the plan beyond the baseline multiple, check-plan-size.sh may emit DRIFT_TRIGGER_FIRED=true, but design-postplan-emit.sh still exits 0 under thresholds and the prompt continues silently
- **Proposed resolution**: Extend design-postplan-emit.sh to parse and surface DRIFT_* and return a dedicated drift outcome, or make the merged rc0 case inspect DRIFT_TRIGGER_FIRED before continuing; update Gate B and discussion case arms to run the Continue/Cancel drift prompt

### FINDING_10:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/check-plan-size.sh:75-89; skills/design/scripts/check-plan-size.sh:117-170
- **Concern**: Drift ratio computation lacks a zero-baseline rule. Scenario: An initial valid plan can have diff_lines: 0; a later nonzero diff estimate makes current > multiple * 0 true, but any integer ratio like current / BASELINE_DIFF_LINES will divide by zero under set -e
- **Proposed resolution**: Define zero-baseline semantics explicitly: trigger when baseline is 0 and current is greater than 0, emit a safe ratio token/value, and avoid division by zero for both plan lines and diff lines

### FINDING_11:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:1704-1887
- **Concern**: ROUND_CAP_ARG_SEEN bifurcation not collapsed with multi-round deletion. Scenario: Step 3 always passes --round-cap so ROUND_CAP_ARG_SEEN=1 skips the legacy block; deleting lines 1728-1887 without a replacement leaves no review round executed
- **Proposed resolution**: Collapse to one single-pass path for all argv shapes (drop the ROUND_CAP_ARG_SEEN==0 guard or make both branches run the same terminal-exit round)

### FINDING_12:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-postplan-emit.sh:314-375
- **Concern**: Drift KVs are produced by check-plan-size.sh but the merged post-plan driver is not planned to parse or branch on them. Scenario: Gate B and discussion-round2 use design-postplan-emit.sh --with-plan-size; a plan can double after apply, then return rc 0 as under-threshold and skip the required Continue/Cancel drift prompt
- **Proposed resolution**: Add DRIFT_* parsing/result KVs and a merged-driver drift branch, preferably with a distinct exit code that Gate B and discussion case arms handle before proceeding

### FINDING_13:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/plan-review.md:46-62; README.md:58-61; docs/skills.md:51-55; docs/workflow-lifecycle.md:79-96
- **Concern**: Removal plan leaves runtime and public references describing --manual, auto-apply, and the inner multi-round revise loop. Scenario: After the PR, /design Step 3 still loads plan-review.md with obsolete auto-apply/convergence semantics, and public docs advertise a now-rejected --manual flag
- **Proposed resolution**: Update plan-review.md for single-pass/no-auto-apply semantics and remove --manual/manual_gate_b/auto-apply claims from the public docs that list /design arguments

### FINDING_14:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-postplan-emit.sh:456-524
- **Concern**: Drift baseline write is scoped to the `--snapshot-original` block before `check-plan-size.sh` runs. Scenario: `PLAN_LINES` / `DIFF_LINES` are only produced by `_postplan_run_plan_size` (line 524+); writing `drift-baseline.env` inside the early snapshot branch leaves baseline empty or forces a second size pass
- **Proposed resolution**: Defer the write-once baseline to after `_postplan_run_plan_size` (or invoke `check-plan-size.sh` there) while keeping `SNAPSHOT_ORIGINAL` + do-not-overwrite guards

### FINDING_15:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md:157-158; skills/design/scripts/design-postplan-emit.sh:314-374
- **Concern**: Drift guard is planned only for standalone Step 2b.5/check-plan-size, but normal Gate B re-emits use design-postplan-emit --with-plan-size and skip standalone Step 2b.5. Scenario: After Gate B doubles the plan without tripping hard size or partition, design-postplan-emit exits rc0 under-threshold and continues to Step 3.6 with no Continue/Cancel drift prompt
- **Proposed resolution**: Add drift handling to the merged post-plan fence: parse/persist DRIFT_* from check-plan-size, return a distinct branch before under-threshold, and update Gate B/discussion case arms to prompt Continue/Cancel

### FINDING_16:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-route.sh:322-335
- **Concern**: Manual surface removal misses the resume route that still reads manual_gate_b and passes removed --manual-requested. Scenario: A paused pre-upgrade run with manual_gate_b=true resumes, write-design-current-env.sh rejects the removed option, and /design aborts despite the plan claiming stale manual_gate_b is harmless
- **Proposed resolution**: Remove the _manual_resume read and --manual-requested append from design-route.sh, and update design-route.md/tests accordingly

### FINDING_17:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/references/plan-review.md:48-62,177-194
- **Concern**: The mandatory Step 3 plan-review reference is not in the update list and still describes multi-round auto-apply and manual_gate_b semantics. Scenario: Step 3 requires reading this file before launch, so the prompt contract conflicts with the new single-pass always-explicit Gate B behavior
- **Proposed resolution**: Add plan-review.md to the updated files and rewrite the Multi-round/legacy/manual references to the single-pass contract

### FINDING_18:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: README.md:59-61; docs/skills.md:51-55; docs/workflow-lifecycle.md:79-96
- **Concern**: Public docs still advertise --manual/-m and default Gate B auto-apply after the planned full removal. Scenario: Users following shipped docs pass --manual and get a hard error, or expect auto-apply when Gate B is now explicit
- **Proposed resolution**: Update the canonical user docs in the same PR to remove --manual/-m and describe the new explicit Gate B behavior

### FINDING_19:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:1703-1726
- **Concern**: Plan deletes the multi-round body but not the ROUND_CAP_ARG_SEEN gate; SKILL.md Step 3 always passes --round-cap. Scenario: SKILL.md:1069 passes --round-cap on every /design Step 3 run; after deleting lines ~1728-1887 only the legacy branch (ROUND_CAP_ARG_SEEN==0) runs one round — production would fall through with no review or a bogus default LOOP_STATUS
- **Proposed resolution**: Remove the bifurcation: always run one _run_plan_review_round then terminal-exit; keep --round-cap argv validation only

### FINDING_20:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-postplan-emit.sh:20-42,350-375
- **Concern**: The plan adds DRIFT_* output in check-plan-size.sh but does not route merged Step 2b/Gate B/discussion postplan callers through a drift branch. Scenario: After Gate B apply doubles the plan while staying below hard thresholds, design-postplan-emit --with-plan-size can still exit 0 under-threshold; the retained Step 2b.5 drift AskUserQuestion never runs, so the new acceptance criterion silently fails
- **Proposed resolution**: Add design-postplan-emit.sh/md to the plan: parse and persist DRIFT_* KVs, branch after hard and partition checks but before under-threshold, and update SKILL.md/approval-gates handling plus tests for that merged drift outcome

### FINDING_21:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-route.sh:323-335
- **Concern**: The --manual removal plan omits the pause/resume reader that still consumes manual_gate_b and passes --manual-requested. Scenario: If a stale resumed run has manual_gate_b=true, design-route.sh will pass --manual-requested true to write-design-current-env.sh after the plan removes that flag, aborting resume despite the plan claiming stale manual_gate_b is harmless
- **Proposed resolution**: Update the plan to remove manual_gate_b resume handling from design-route.sh and design-route.md, and cover it in the relevant route/structure tests

### FINDING_22:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: README.md:59-61, docs/skills.md:51-55, docs/workflow-lifecycle.md:79-96
- **Concern**: The plan removes the public --manual/-m surface but omits shipped consumer docs that still advertise it. Scenario: Users following README/docs will pass --manual and hit the new unrecognized-flag hard error
- **Proposed resolution**: Add the README.md, docs/skills.md, and docs/workflow-lifecycle.md references to the plan’s removal list or explicitly narrow the plan if those docs are intentionally left for a separate change

### FINDING_23:
- **Reviewer(s)**: Cursor-dyn-kv-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-route.sh:322-335
- **Concern**: Plan omits design-route.sh/design-route.md but resume still reads manual_gate_b and passes --manual-requested to write-design-current-env.sh. Scenario: After writer drops --manual-requested, pause/resume on sessions with stale run-params.json manual_gate_b:true fails env refresh (unknown argument); contradicts plan edge case that stale manual_gate_b is harmless
- **Proposed resolution**: Add design-route.sh and design-route.md to Files; remove _manual_resume/manual_gate_b jq and --manual-requested append; update test-design-structure.sh pin at scripts/test-design-structure.sh:1548

### FINDING_24:
- **Reviewer(s)**: Codex-dyn-kv-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:41-43,76-83; skills/design/scripts/design-postplan-emit.sh:20-43,162-183,348-375; skills/design/SKILL.md:973-983
- **Concern**: Drift KVs are only planned for check-plan-size.sh and retained Step 2b.5, but merged post-plan callers go through design-postplan-emit.sh and currently only forward the existing plan-size KVs. Scenario: Gate B and discussion re-emits use design-postplan-emit.sh --with-plan-size, then SKILL.md continues on rc=0; a drift trigger can be computed but never surfaced to the operator
- **Proposed resolution**: Add the DRIFT_* and BASELINE_* keys to design-postplan-emit.sh parsing/result-env output and add an explicit merged-mode drift branch/return path that SKILL.md handles before the rc=0 continue path

### FINDING_25:
- **Reviewer(s)**: Codex-dyn-kv-contract
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:70-74,91-97; skills/design/scripts/design-route.sh:322-335; scripts/write-design-current-env.sh:72-88
- **Concern**: The plan says stale manual_gate_b is harmless and removes write-design-current-env.sh --manual-requested, but omits design-route.sh’s pause-resume reader that still converts manual_gate_b into --manual-requested. Scenario: A resumed run with stale manual_gate_b=true calls write-design-current-env.sh with a removed flag, causing resume env refresh to fail instead of being harmless
- **Proposed resolution**: Include skills/design/scripts/design-route.sh in the manual-removal changes: stop reading manual_gate_b and never append --manual-requested on resume, and adjust its tests/pins accordingly

### FINDING_26:
- **Reviewer(s)**: Codex-dyn-removal-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-route.sh:323-335; skills/design/scripts/design-route.md:31
- **Concern**: The removal plan leaves pause-resume as a manual_gate_b reader and --manual-requested caller. Scenario: After write-design-current-env.sh drops --manual-requested, a resumed run with stale run-params.json manual_gate_b=true makes design-route.sh append the deleted flag and abort env refresh; this also contradicts the plan's stale manual_gate_b is harmless/all readers removed claim
- **Proposed resolution**: Add design-route.sh/design-route.md to the plan: delete the manual_gate_b jq read and _wdce_resume_args+=(--manual-requested true), and update the related design-route/test-design-structure pins

### FINDING_27:
- **Reviewer(s)**: Codex-dyn-removal-completeness
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/references/plan-review.md:46-55; skills/design/references/plan-review.md:173-194
- **Concern**: Step 3's mandatory reference still describes the removed multi-round/manual_gate_b contract. Scenario: The orchestrator must read this file before Step 3; if it remains stale, it will still say --round-cap drives an auto-apply loop, manual_gate_b changes Gate B application, and finding templates surface per manual_gate_b after those constructs are removed
- **Proposed resolution**: Update plan-review.md in the plan to describe single-pass review, inert/deprecated round cap, and always-explicit Gate B; update any structure pins tied to the old text

### FINDING_28:
- **Reviewer(s)**: Codex-dyn-removal-completeness
- **Severity**: latent
- **Focus area**: correctness
- **Location**: docs/configuration-and-permissions.md:272-276; docs/installation-and-setup.md:231-233
- **Concern**: Public docs still present LARCH_DESIGN_ROUND_CAP as active. Scenario: After code makes --round-cap inert and deprecates the env var, operators reading canonical env docs still expect it to bound inner multi-round loop and tune SIMPLE-tier cost
- **Proposed resolution**: Add minimal docs updates to mark LARCH_DESIGN_ROUND_CAP deprecated/no multi-round effect and revise SIMPLE-tier cost wording; no code complexity needed

### OOS_1:
- **Description**: Normative multi-round / `manual_gate_b` prose in `plan-review.md` is not in the plan file list; `test-design-structure.sh` pins some of it today (~1374–1375). Scenario: After harness pins are swapped, `plan-review.md` can still describe auto-apply and manual Gate B while `SKILL.md` / `approval-gates.md` say otherwise, confusing later edits
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/plan-review.md:48-62
- **Phase**: design
