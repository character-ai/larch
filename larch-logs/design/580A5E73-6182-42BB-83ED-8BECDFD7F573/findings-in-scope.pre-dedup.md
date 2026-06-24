### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:28-34
- **Concern**: Prior accepted fix incomplete: per-status Step 5b mapping still omits explicit NEXT_ACTION=skip-pipeline on three skip arms. Scenario: Line 24 requires every skip status to emit NEXT_ACTION=skip-pipeline, but skip-already-filed-sentinel, skip-no-items, and skip-all-security bullets list only OOS_SKIP_BREADCRUMB and conditional annotate flags. An implementer following the per-status block can omit NEXT_ACTION while tests and Step 5b prose expect it on every skip path.
- **Proposed resolution**: Add NEXT_ACTION=skip-pipeline to each of the three skip-arm bullets (mirror skip-sentinel) so the per-status table matches the global rule and parametrized tests.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:785-790
- **Concern**: Step 5b lacks an authoritative bind surface for wrapper-only dispatch keys. Scenario: `step5b_prepare_main` writes `oos-filing-prepare.env` from `file_oos_prepare` stdout only, then emits `NEXT_ACTION`, `OOS_SKIP_BREADCRUMB`, and `STEP5B_NEEDS_ANNOTATE` on prepare-fence stdout afterward. Planned Step 5b prose still centers parsing `FILE_DESIGN_OOS_STATUS` and `WARN=` from the env file and never names prepare-fence stdout capture as the primary bind source for the new keys.
- **Proposed resolution**: Orchestrator never binds `NEXT_ACTION` and can fall through to the legacy five-way status tree or unknown-status repair despite the wrapper emitting the new contract. In Step 5b SKILL prose, require binding `NEXT_ACTION`, `OOS_SKIP_BREADCRUMB`, and `STEP5B_NEEDS_ANNOTATE` from the `design-step5b-prepare.sh` Bash-fence stdout capture first; keep `oos-filing-prepare.env` only for pass-through `FILE_DESIGN_OOS_*` and `WARN=` rows.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:789-790
- **Concern**: Step 5b prepare-failure routing is not ordered before legacy env-status parsing. Scenario: On `prep_rc != 0` the wrapper exits 0 with `STEP5B_STATUS=prepare-failed-continue` and (per plan) `NEXT_ACTION=skip-pipeline`, often without `FILE_DESIGN_OOS_STATUS` in `oos-filing-prepare.env`. Planned Step 5b still gates on non-zero `_oos_prep_rc` or parses env status before `NEXT_ACTION` binding.
- **Proposed resolution**: The unified `NEXT_ACTION=skip-pipeline` branch is skipped and control can enter the zero-exit env parse or unknown-status repair instead of continuing to Step 5b.5. Replace Step 5b item 1 dual-path prose with a single flow: run prepare, bind `NEXT_ACTION` from stdout, branch on it first; treat prepare-failure via `NEXT_ACTION=skip-pipeline` (not fence exit code or env status alone).



### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:206-224
- **Concern**: Structure-test and numbered settle-directive updates are not pinned in the plan. Scenario: The plan generically says to update rc-only pins, but `test-design-structure.sh` still requires the exact Dispatch-key `$?` paragraph (line 206) and four `assert_followed_count_at_least` adjacency needles pairing settle-rc-dispatch reads with branching on `$?` in approval-gates, discussion-rounds, and SKILL (lines 221-224). The plan updates settle-rc-dispatch.md and caller prose at a high level but does not explicitly revise approval-gates step 8.2, discussion-rounds step 2, or SKILL numbered steps 407-408 and 702-703.
- **Proposed resolution**: Prose can migrate to `SETTLE_NEXT_ACTION`-first while structure pins still demand `$?`-first wording, causing `make lint` / `test-design-structure.sh` failure or leaving obsolete rc-primary directives in live orchestrator paths. List explicit updates in `### UPDATED: scripts/test-design-structure.sh`: replace line 206 Dispatch-key needle, retarget lines 221-224 adjacency second needles to `SETTLE_NEXT_ACTION`-first wording, and add matching edits to approval-gates step 8.2, discussion-rounds step 2, and SKILL Gate A/B numbered settle steps.



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:28-34
- **Concern**: [Prior round 4 accepted; still incomplete] Per-status Step 5b mapping omits explicit NEXT_ACTION=skip-pipeline on skip-already-filed-sentinel, skip-no-items, and skip-all-security. Scenario: Line 24 requires every skip status to emit NEXT_ACTION=skip-pipeline, but those three per-status bullets list only OOS_SKIP_BREADCRUMB (and conditional annotate). Tests and design-step5b-prepare.md require the key on every skip path. An implementer following the per-status block can omit NEXT_ACTION while still emitting breadcrumbs.
- **Proposed resolution**: Add NEXT_ACTION=skip-pipeline to each of the three skip arms in the per-status mapping, mirroring skip-sentinel.



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:785-790
- **Concern**: Step 5b plan lacks an authoritative bind surface for wrapper-only dispatch keys. Scenario: step5b_prepare_main writes oos-filing-prepare.env from file_oos_prepare stdout only, then emits NEXT_ACTION, OOS_SKIP_BREADCRUMB, and STEP5B_NEEDS_ANNOTATE on prepare-fence stdout afterward. Planned Step 5b prose still centers FILE_DESIGN_OOS_STATUS and WARN= from oos-filing-prepare.env and does not require binding wrapper-only keys from the prepare-fence stdout capture. NEXT_ACTION stays unbound and the five-way status tree or unknown-status repair can persist.
- **Proposed resolution**: In skills/design/SKILL.md Step 5b, require parsing the prepare-fence stdout capture first for NEXT_ACTION, OOS_SKIP_BREADCRUMB, and STEP5B_NEEDS_ANNOTATE; use oos-filing-prepare.env only for FILE_DESIGN_OOS_* pass-through rows already relayed there.



### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:789-790
- **Concern**: Prepare-failure routing not ordered before legacy env-status parsing. Scenario: On prep_rc != 0, prepare exits 0 with STEP5B_STATUS=prepare-failed-continue and (per plan) NEXT_ACTION=skip-pipeline, often without FILE_DESIGN_OOS_STATUS in oos-filing-prepare.env. Planned Step 5b keeps prepare-failure warning semantics but does not delete the legacy On non-zero _oos_prep_rc gate or require NEXT_ACTION-first routing before the zero-exit env parse. The orchestrator can miss the unified skip-pipeline branch and fall through to unknown-status repair.
- **Proposed resolution**: Replace the non-zero _oos_prep_rc branch with: on prepare-fence stdout, if NEXT_ACTION=skip-pipeline (including prepare-failed-continue), run the skip-pipeline path; only parse FILE_DESIGN_OOS_STATUS from env when NEXT_ACTION=file-issues or as explicit fallback when NEXT_ACTION is missing.



### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:206,221-224
- **Concern**: Structure-test plan omits specific settle dispatch needle updates. Scenario: The plan generically says to update rc-only pins. test-design-structure.sh still contains literals requiring rc-primary dispatch (line 206 settle-rc-dispatch.md contains text; assert_followed_count_at_least pairs approval-gates.md, discussion-rounds.md, and SKILL.md Gate guards with branching on the settle wrapper exit status ($?)). Prose may migrate to SETTLE_NEXT_ACTION-first while structure pins still require $?, causing make lint failure or blocking removal of obsolete rc-primary text.
- **Proposed resolution**: Name the exact needles to replace in scripts/test-design-structure.sh and require matching updates to approval-gates.md step 8.2 and discussion-rounds.md step 2 so numbered directives branch on SETTLE_NEXT_ACTION when present before $ fallback.



### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:28-34
- **Concern**: Per-status Step 5b mapping still omits explicit NEXT_ACTION=skip-pipeline on three skip arms. Scenario: Line 24 requires every skip status to emit NEXT_ACTION=skip-pipeline, but skip-already-filed-sentinel, skip-no-items, and skip-all-security list only OOS_SKIP_BREADCRUMB (and conditional annotate). An implementer following the per-status block can omit the key while tests and Step 5b prose expect it on every skip path
- **Proposed resolution**: Add NEXT_ACTION=skip-pipeline to each of the three skip-arm bullets, matching skip-sentinel



### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:785-790
- **Concern**: Step 5b prose lacks an authoritative bind surface for wrapper-only dispatch keys and still gates prepare failure on non-zero _oos_prep_rc. Scenario: step5b_prepare_main writes oos-filing-prepare.env from file_oos_prepare stdout only; NEXT_ACTION, OOS_SKIP_BREADCRUMB, and STEP5B_NEEDS_ANNOTATE are emitted afterward on prepare-fence stdout. Planned Step 5b still centers parsing FILE_DESIGN_OOS_STATUS from the env file and item 1 gates on non-zero _oos_prep_rc even though the prepare fence exits 0 on prep failure while emitting NEXT_ACTION=skip-pipeline. The orchestrator can leave NEXT_ACTION unbound and miss the unified skip-pipeline branch
- **Proposed resolution**: State that the orchestrator must parse NEXT_ACTION, OOS_SKIP_BREADCRUMB, and STEP5B_NEEDS_ANNOTATE from the design-step5b-prepare.sh fence stdout capture (last whole-line row per key); route on NEXT_ACTION before any legacy FILE_DESIGN_OOS_STATUS tree; replace item 1 non-zero _oos_prep_rc gate with NEXT_ACTION=skip-pipeline when STEP5B_STATUS=prepare-failed-continue



### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:206-224
- **Concern**: Structure-test plan is too generic for the planned SETTLE_NEXT_ACTION-primary migration. Scenario: Plan lines 176-178 replace rcx-first dispatch prose in settle-rc-dispatch.md, but test-design-structure.sh line 206 requires that rcx-first string and lines 221-224 pin adjacency to branching on the settle wrapper exit status ($?). Line 235 only says to update rc-only pins generically. After the reference migration, make lint fails even when runtime settle dispatch is correct
- **Proposed resolution**: Name the conflicting needles (206, 221-224, and any rcx-primary contains) and require replacing them with SETTLE_NEXT_ACTION-primary pins while keeping the rc fallback table pins at 208-216 and the ## Branch on wrapper rc section at 232



### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:28-34
- **Concern**: Per-status Step 5b mapping still omits explicit NEXT_ACTION=skip-pipeline on three skip arms. Scenario: Line 24 requires every skip status to emit NEXT_ACTION=skip-pipeline, but skip-already-filed-sentinel, skip-no-items, and skip-all-security list only OOS_SKIP_BREADCRUMB (and conditional annotate). An implementer following the per-status block can omit NEXT_ACTION; tests and Step 5b prose expect it on every skip path.
- **Proposed resolution**: Add NEXT_ACTION=skip-pipeline to each of the three per-status bullets, matching skip-sentinel.



### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:785-795
- **Concern**: Planned Step 5b prose lacks an authoritative bind surface for wrapper-only dispatch keys. Scenario: step5b_prepare_main writes oos-filing-prepare.env from file_oos_prepare stdout only, then emits NEXT_ACTION, OOS_SKIP_BREADCRUMB, and STEP5B_NEEDS_ANNOTATE on prepare-fence stdout afterward. Planned SKILL still centers FILE_DESIGN_OOS_STATUS parsing from oos-filing-prepare.env and does not require binding wrapper-only keys from the prepare-fence stdout capture first.
- **Proposed resolution**: Orchestrator never binds NEXT_ACTION and can fall through to the legacy five-way status tree or unknown-status repair. In Step 5b SKILL updates, require binding NEXT_ACTION, OOS_SKIP_BREADCRUMB, and STEP5B_NEEDS_ANNOTATE from the prepare-fence stdout capture before any env-only FILE_DESIGN_OOS_STATUS routing; keep WARN= parse from stdout or env as fallback only.



### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:789-790
- **Concern**: Prepare-failure routing not ordered before legacy env-status parse. Scenario: On prep_rc != 0, step5b_prepare_main exits 0 with STEP5B_STATUS=prepare-failed-continue and (per plan) NEXT_ACTION=skip-pipeline, often without FILE_DESIGN_OOS_STATUS in oos-filing-prepare.env. Current and planned Step 5b prose still gate on non-zero _oos_prep_rc or parse env status on zero wrapper exit before NEXT_ACTION binding.
- **Proposed resolution**: Orchestrator misses the unified skip-pipeline branch and mis-routes toward unknown-status repair. Retire the non-zero _oos_prep_rc / zero-exit env-only tree; after prepare fence returns, branch on NEXT_ACTION=skip-pipeline when STEP5B_STATUS=prepare-failed-continue or NEXT_ACTION is present, then handle file-issues.



### FINDING_15:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:206-224
- **Concern**: Structure-test plan omits specific settle dispatch needle updates. Scenario: The plan only generically says to update rc-only pins. test-design-structure.sh still contains literals pinning $?-primary dispatch (line 206 contains check; lines 221-224 assert_followed_count_at_least adjacency requiring branch on settle wrapper exit status ($?)). After settle-rc-dispatch.md migrates to SETTLE_NEXT_ACTION-first, make lint can fail unless these needles are updated.
- **Proposed resolution**: Name and update the line 206 contains literal, the four assert_followed_count_at_least adjacency pairs, and any not_contains pins that assume rc-only dispatch; replace $?-first wording with SETTLE_NEXT_ACTION-first adjacency to match approval-gates.md and discussion-rounds.md edits.



