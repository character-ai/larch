### External Reviewer Issues

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 1)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-arch-output.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=1|FAILURE_REASON=Failed with exit code 1 after 20s. Output size: 0 bytes.

## Reviewer output (<TMPDIR>/codex-primary-plan-arch-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	skills/implement/SKILL.md:1378-1397	Step 8+ prose still routes on LARCH_STATUS_FILE and monitor_rc after trap removal	Stage 3 made larch_quiet_append_done_trap a no-op; collapsing fences removes status-file allocation but L1378 still tells the orchestrator to parse EXIT_CODE from $LARCH_STATUS_FILE and L1397 still distinguishes monitor_rc vs writer_rc — empty/missing status files or wrong stall/bail routing	In the implement/SKILL.md edit, explicitly replace post-Invoke guidance (L1378, L1397, and related Step 2/5 wrapper notes) to use the foreground Bash tool exit code plus ship-pr-state.sh keys only; drop monitor_rc / breadcrumb-monitor routing entirely
2	in_scope	important	correctness	scripts/test-lib-quiet.sh:167-171	Shim regression case not in plan change set	Plan deletes larch_quiet_append_done_trap / larch_quiet_write_paired_pid_file from lib-quiet.sh but leaves test #11 invoking both; make lint / test-lib-quiet fails with command not found	Add scripts/test-lib-quiet.sh to Files to modify: remove or rewrite case 11 after shim deletion (plan already lists the harness in Testing strategy but not Files)
3	in_scope	important	correctness	scripts/test-collect-agent-results.sh:211-222	C_DONE case still exports removed env vars	Plan only says update the Stage-3 shim comment; C_DONE still passes LARCH_DONE_SENTINEL and LARCH_STATUS_FILE into the collector, so the final grep gate for those tokens fails and the case no longer matches post-rip-out behavior	Extend the test-collect-agent-results.sh step: drop sentinel/status env from C_DONE (assert on collector stdout/exit only) or delete the case if redundant
4	in_scope	important	risk-integration	plan.txt:108-118 vs repo harnesses	Grep-gate harness sweep incomplete in plan file list	Final grep must be zero for LARCH_BREADCRUMB_STREAM / LARCH_DONE_SENTINEL / etc. outside exclusions, but Files omits harnesses that still reference them: skills/design/scripts/test-assess-plan-round.sh, test-dispatch-plan-assessors.sh, test-tally-plan-assessor.sh, scripts/test-ci-wait.sh, skills/review/scripts/test-review-core.sh, test-dispatch-panel.sh, skills/upgrade-larch/scripts/test-upgrade-larch.sh, test-upgrade-larch-prune.sh, skills/implement/scripts/test-implement-bootstrap.sh	Add these paths to Files (or Approach step 1 pre-flight) with “remove obsolete breadcrumb env unset/mock lines”; keep larch-logs/** and forensics breadcrumbs/ exclusions as already documented

**1. [correctness] `skills/implement/SKILL.md:1378-1397` — status-file routing prose survives fence collapse**

The plan correctly targets Family-B fence collapse and NEVER #9/#16 tombstoning, but Step 8+ **non-fence** blockquotes still prescribe parsing `EXIT_CODE` from `$LARCH_STATUS_FILE` and splitting `monitor_rc` vs `writer_rc` after Stage 3 removed the trap that populated that file. Collapsing fences alone leaves orchestrator guidance that no longer matches runtime.

**Suggested revision:** In the `skills/implement/SKILL.md` bullet, require updating L1378, L1397, and any parallel Step 2/5 wrapper-routing prose to use the foreground Bash exit code and `ship-pr-state.sh` only.

---

**2. [correctness] `scripts/test-lib-quiet.sh:167-171` — shim test omitted from Files**

Case 11 still calls `larch_quiet_append_done_trap` and `larch_quiet_write_paired_pid_file`. The plan deletes those functions but does not list this harness under Files to modify (only under Testing strategy).

**Suggested revision:** Add `scripts/test-lib-quiet.sh` to Files; remove or replace case 11 when shims are deleted.

---

**3. [correctness] `scripts/test-collect-agent-results.sh:211-222` — C_DONE still uses removed env contract**

The plan’s test step is comment-only, yet C_DONE still exports `LARCH_DONE_SENTINEL` / `LARCH_STATUS_FILE`, which conflicts with the stated final grep gate and post-rip-out collector behavior.

**Suggested revision:** Strip those env vars from C_DONE or drop the case; align the harness with foreground-only collector invocation.

---

**4. [risk-integration] Plan harness inventory vs repo-wide grep gate**

Several offline harnesses outside the plan’s Files list still unset or inject `LARCH_BREADCRUMB_*` / sentinel vars (design assessor tests, `test-ci-wait.sh`, review/upgrade/bootstrap harnesses). The plan’s grep gate is repo-wide; relying on discovery at step 6 without listing these paths risks a partial commit that fails `make lint` late.

**Suggested revision:** Extend Approach step 1 or Files with the harness paths above so the rip-out and grep gate stay in one atomic change.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-arch-output.txt.diag)

Failed with exit code 1 after 20s. Output size: 0 bytes.

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-edge-output-phase3.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/codex-primary-plan-edge-output-phase3.txt)

(file missing: <TMPDIR>/codex-primary-plan-edge-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/codex-primary-plan-edge-output-phase3.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-edge-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 1)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-innovation-output.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=1|FAILURE_REASON=Failed with exit code 1 after 10s. Output size: 0 bytes.

## Reviewer output (<TMPDIR>/codex-primary-plan-innovation-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/test-lib-quiet.sh:167-171	Case 11 still exercises deleted shims	Deleting `larch_quiet_append_done_trap` / `larch_quiet_write_paired_pid_file` without updating this harness makes `make test-lib-quiet` fail with `command not found`	Add an explicit `### UPDATED: scripts/test-lib-quiet.sh` step to remove or replace case 11 (the plan lists the harness in Testing strategy but not Files to modify)
2	in_scope	important	correctness	skills/implement/SKILL.md:1378-1397	Step 8 post-invoke prose still routes via `LARCH_STATUS_FILE` and `breadcrumb-monitor.sh`	After the proposed plain-foreground `ship-pr.sh` fence, those paths are not created and `ship-pr.sh` does not write `LARCH_STATUS_FILE`; following L1378/L1397 mis-routes stalls and resume	Extend the `skills/implement/SKILL.md` edit to reframe post-return handling on the Bash exit code plus `ship-pr-state.sh`, and drop monitor/`LARCH_STATUS_FILE` wrapper-routing text in the exit matrix
3	in_scope	important	architecture	skills/implement/references/stall-recovery.md:6-53	Stall-recovery monitor contract trimmed as one fence only	The file has no Family-B bash fence; lines 6, 23-24, and 53 still mandate background+monitor pairs and `breadcrumb-monitor.sh`, so the final grep gate and Step 18a redispatch stay wrong	Expand the `stall-recovery.md` task to reframe all dispatch bullets and Safety Constraints for plain foreground + `<task-notification>` (same model as Step 8), not a single fence collapse
4	in_scope	important	risk-integration	plan.txt:137-143	Final grep gate omits several live harness/doc hits	Post-change grep for `LARCH_BREADCRUMB_*`, `LARCH_PAIRED_PID_FILE`, and `breadcrumb-monitor` will still match files such as `skills/design/scripts/test-assess-plan-round.sh` (`LARCH_BREADCRUMB_MONITOR_SH`), `skills/design/scripts/test-dispatch-plan-assessors.sh`, `scripts/test-ci-wait.sh`, and `skills/implement/references/rebase-rebump-subprocedure.md:189-192`	Add those paths to Files to modify (trim or rename test-only symbols) or narrow the grep gate patterns so forensics/test isolation strings are not accidental failures

1. **correctness** — `scripts/test-lib-quiet.sh:167-171`: Case 11 still calls the shims the plan deletes. The harness is named in Testing strategy but not in Files to modify; `make test-lib-quiet` will break unless case 11 is removed or rewritten.

2. **correctness** — `skills/implement/SKILL.md:1378-1397`: After collapsing the Step 8 fence, L1378 still tells the orchestrator to parse `EXIT_CODE` from `$LARCH_STATUS_FILE`, and L1397 still distinguishes `monitor_rc` from writer stalls. `ship-pr.sh` does not populate `LARCH_STATUS_FILE`, and Stage 3 already made the done trap a no-op. Extend the SKILL edit to use foreground exit code + `ship-pr-state.sh` only.

3. **architecture** — `skills/implement/references/stall-recovery.md:6-53`: The plan scopes this file as one Family-B fence collapse, but the file is procedural prose (monitor pairs, six `LARCH_*` paths, `breadcrumb-monitor.sh` failure surface, Safety Constraint line 53). Without a broader trim, Step 18a redispatch and the grep gate stay inconsistent with Stage 4.

4. **risk-integration** — `plan.txt:137-143`: The mandatory zero-hit grep list will fail on harness/doc files not listed under Files to modify—notably `skills/design/scripts/test-assess-plan-round.sh` (env name `LARCH_BREADCRUMB_MONITOR_SH` matches the `breadcrumb-monitor` pattern), design/review/implement test `unset` barriers, and `rebase-rebump-subprocedure.md:189-192` (`LARCH_PAIRED_PID_FILE` / monitor pairing note). Enumerate them in the plan or adjust grep patterns.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

Failed with exit code 1 after 10s. Output size: 0 bytes.

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 1)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-pragmatic-output.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=1|FAILURE_REASON=Failed with exit code 1 after 10s. Output size: 0 bytes.

## Reviewer output (<TMPDIR>/codex-primary-plan-pragmatic-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/test-lib-quiet.sh:167-171	Plan lists make test-lib-quiet in Testing strategy but not in Files to modify; case 11 still invokes removed shims	Final grep gate requires zero larch_quiet_append_done_trap / larch_quiet_write_paired_pid_file; test-lib-quiet.sh fails grep and exercises deleted symbols	Add scripts/test-lib-quiet.sh to Files to modify: drop or rewrite case 11 after shim removal
2	in_scope	important	correctness	scripts/test-collect-agent-results.sh:211-222	Plan only updates the Stage-3 comment; C_DONE still exports LARCH_DONE_SENTINEL and LARCH_STATUS_FILE	Final grep gate forbids those env vars outside allowed paths; make test-collect-agent-results may pass while repo grep fails	Remove sentinel/status env from C_DONE or rewrite the case for plain foreground collector behavior only
3	in_scope	important	correctness	skills/implement/SKILL.md:1378-1397	Step 8+ prose still routes on LARCH_STATUS_FILE monitor_rc writer_rc and breadcrumb-monitor failures after fences become plain foreground	Orchestrator may parse a status file the trap no longer writes or treat monitor infrastructure failures as ship-pr stalls	Add explicit Step 8/18a prose update: use foreground exit code and ship-pr-state.sh keys only; drop monitor wrapper routing
4	in_scope	important	risk-integration	skills/implement/references/stall-recovery.md:5-53	skills/review/references/heavy-worker.md:55	skills/shared/voting-protocol.md:184	skills/design/SKILL.md:668	skills/implement/references/rebase-rebump-subprocedure.md:189-192	Plan says collapse Family-B fence but these paths are prose-only (or mis-targeted file for dispatch-plan-voters); grep gate will still hit breadcrumb-monitor LARCH_PAIRED_PID_FILE must be paired with	Implementer completes fence collapse yet final grep or stall-recovery dispatch guidance stays wrong	Expand each listed file entry to trim surviving prose (foreground collector / plain ship-pr / ci-wait sync) not only fences
5	in_scope	important	correctness	scripts/ship-pr.md:183-185	Top-level Family B / LARCH_PAIRED_PID_FILE note not in plan file list	Grep gate matches LARCH_PAIRED_PID_FILE; doc contradicts post-Stage-4 model	Add scripts/ship-pr.md to Files to modify: reword nested ci-wait note without paired-PID / Family-B monitor vocabulary
6	in_scope	important	architecture	skills/implement/SKILL.md:390-1280	skills/design/SKILL.md:362-1038	Nine # Foreground required: see BASH_AUTHORING.md §4 anchors survive §4 deletion; plan scopes implement/design edits to Family-B fence collapse only	Final grep requires zero BASH_AUTHORING.md §4; anchors become dead pointers	When deleting BASH_AUTHORING.md §4 add explicit step to retarget or remove non-Family-B foreground fence comments in both SKILL files

**1. Test harnesses omitted from the change set** (`scripts/test-lib-quiet.sh:167-171`, `scripts/test-collect-agent-results.sh:211-222`). The plan’s final grep gate forbids `larch_quiet_append_done_trap`, `larch_quiet_write_paired_pid_file`, `LARCH_DONE_SENTINEL`, and `LARCH_STATUS_FILE`, but only `test-collect-agent-results.sh` appears under Files to modify—and only for a comment refresh. Case 11 in `test-lib-quiet.sh` still calls both shims; C_DONE still exports sentinel/status env vars the collector no longer uses.

**2. Step 8 orchestration prose not tied to fence collapse** (`skills/implement/SKILL.md:1378-1397`, plus related blocks at ~981, ~762). Collapsing Family-B fences to plain foreground calls does not update instructions to parse `EXIT_CODE` from `$LARCH_STATUS_FILE` or branch on `monitor_rc` vs `writer_rc`. After Stage 3, the done trap is a no-op; after Stage 4, the monitor wrapper is gone—this prose becomes actively misleading for stall and resume routing.

**3. “Collapse fence” entries that are prose-only or mis-targeted** (`stall-recovery.md`, `heavy-worker.md`, `voting-protocol.md:184`, `design/SKILL.md:668`, `rebase-rebump-subprocedure.md:189-192`). `stall-recovery.md` and `heavy-worker.md` have no `breadcrumb-monitor.sh` fence to collapse—only dispatch/resume prose. `voting-protocol.md` does not host the `dispatch-plan-voters.sh` fence (that lives in `plan-review.md`); line 184 still mandates `run_in_background` + monitor pairing. `design/SKILL.md:668` is free-standing prose outside the seven collector-fence refs. `rebase-rebump-subprocedure.md` has no ci-wait/ship-pr monitor fence but still documents `LARCH_PAIRED_PID_FILE` / `breadcrumb-monitor.sh` (grep gate hit).

**4. `scripts/ship-pr.md` grep survivor** (`183-185`). Documents top-level Family B and `LARCH_PAIRED_PID_FILE` removal in Stage 3; not listed in Files to modify. Will fail the planned repo-wide grep unless trimmed.

**5. `BASH_AUTHORING.md §4` foreground anchors** (`skills/implement/SKILL.md` seven `# Foreground required` lines; `skills/design/SKILL.md:362`, `1038`). Deleting §4 is in scope; retargeting these non–Family-B fence comments is not. The testing grep gate requires zero `BASH_AUTHORING.md §4` hits—implementers need an explicit step beyond Family-B fence collapse.

[OUT_OF_SCOPE] `docs/configuration-and-permissions.md` — plan’s conditional trim appears unnecessary today (no `LARCH_BREADCRUMB_*` live-stream env docs found; only unrelated “step breadcrumb” wording at ~229).

## Reviewer stderr (<TMPDIR>/codex-primary-plan-pragmatic-output.txt.diag)

Failed with exit code 1 after 10s. Output size: 0 bytes.

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-requirements-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-requirements-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-requirements-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-requirements-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-requirements-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-requirements-output-phase3.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/codex-primary-plan-requirements-output-phase3.txt)

(file missing: <TMPDIR>/codex-primary-plan-requirements-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/codex-primary-plan-requirements-output-phase3.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-requirements-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-dyn-doc-cross-ref-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-dyn-doc-cross-ref-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-dyn-doc-cross-ref-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-dyn-doc-cross-ref-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-dyn-doc-cross-ref-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-doc-cross-ref-output-phase3.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-doc-cross-ref-output-phase3.txt)

(file missing: <TMPDIR>/codex-primary-plan-dyn-doc-cross-ref-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-doc-cross-ref-output-phase3.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-doc-cross-ref-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-dyn-harness-sync-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-dyn-harness-sync-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-dyn-harness-sync-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-dyn-harness-sync-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-dyn-harness-sync-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-harness-sync-output-phase3.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-harness-sync-output-phase3.txt)

(file missing: <TMPDIR>/codex-primary-plan-dyn-harness-sync-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-harness-sync-output-phase3.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-harness-sync-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 1)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-arch-output.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=1|FAILURE_REASON=Failed with exit code 1 after 20s. Output size: 0 bytes.

## Reviewer output (<TMPDIR>/codex-primary-plan-arch-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/test-ship-pr.sh:11; skills/design/scripts/test-dispatch-plan-assessors.sh:5; skills/design/scripts/test-assess-plan-round.sh:5; skills/design/scripts/test-tally-plan-assessor.sh:5; skills/review/scripts/test-dispatch-panel.sh:12; skills/review-and-fix/scripts/test-review-and-fix.sh:11; skills/implement/scripts/test-run-step2-dispatch.sh:68	Final grep gate lists LARCH_DONE_SENTINEL / LARCH_STATUS_FILE / LARCH_PAIRED_PID_FILE / LARCH_BREADCRUMB_STREAM but the file list omits these harness unset lines	PR can pass skill/doc edits yet still fail the plan’s own zero-hit grep gate on test-only env hygiene	Extend the plan file list (or add one “grep-gate harness sweep” step) to strip or narrow these unset lines in the same PR
2	in_scope	important	correctness	skills/implement/SKILL.md:390,644,800,947,1217,1245,1280; skills/design/SKILL.md:362,1038	Foreground fences still cite deleted BASH_AUTHORING.md §4; grep gate explicitly forbids that string	Operators keep a dead cross-reference; acceptance grep fails even if Family-B fences collapse cleanly	While editing those skills, retarget “Foreground required” comments to surviving BASH_AUTHORING guidance (or drop the §4 pointer) everywhere §4 is removed
3	in_scope	important	correctness	skills/implement/references/stall-recovery.md:23-24,53; skills/implement/references/rebase-rebump-subprocedure.md:189-192; skills/review/references/heavy-worker.md:55; skills/shared/voting-protocol.md:184	Plan labels these as “collapse fence (1 ref)” but they are prose-only (no breadcrumb-monitor fence); rebase still documents LARCH_PAIRED_PID_FILE / breadcrumb-monitor routing	Implementer may skip post-collapse routing rewrites; stall recovery and Step 18a can keep monitor-failure semantics after monitors are deleted	Add explicit prose-only tasks: rewrite stall-recovery dispatch to plain foreground ship-pr/run-step5-review; delete rebase-rebump L189-192 paired-PID paragraph; update heavy-worker and voting-protocol collector guidance to foreground collect-agent-results (no breadcrumb-monitor)


- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 1)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-edge-output.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=1|FAILURE_REASON=Failed with exit code 1 after 10s. Output size: 0 bytes.

## Reviewer output (<TMPDIR>/codex-primary-plan-edge-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	skills/implement/references/stall-recovery.md:5-53	Plan scopes stall-recovery as “collapse the Family-B fence (1 ref)” but the file has no `breadcrumb-monitor.sh` fence—only contract/dispatch prose mandating background+monitor pairs and monitor-specific Exit 4 routing	A fence-only pass leaves Step 18a `step5-review` / `step8-shippr` dispatch and Safety Constraints still prescribing deleted machinery; recovery can mis-route stalls after Stage 4	Replace the listed edit with explicit prose rewrite: plain foreground `run-step5-review.sh` / `ship-pr.sh`, drop six-path exports and monitor-failure branch; align with FINDING_1 (use Bash exit code + `ship-pr-state.sh` only)
2	in_scope	important	correctness	skills/review/references/heavy-worker.md:55	Plan scopes heavy-worker as “collapse the Family-B fence (1 ref)” but the only monitor reference is Wait Discipline prose, not a fence	Fence-only work leaves “collect-agent-results + breadcrumb-monitor” as the sole wait mechanism; subagent workers can still follow removed pairing	Expand the heavy-worker task to rewrite Wait Discipline (foreground collector, harness auto-background on overrun); do not assume a fence collapse exists
3	in_scope	important	risk-integration	skills/implement/references/stall-recovery.md:24	skills/implement/SKILL.md FINDING_1 rewrites Step 8+ routing but stall-recovery Exit 4 text still splits wrapper `monitor_rc` from writer `EXIT_CODE=4`	After fences become plain foreground, Step 18a may still treat a normal `ship-pr.sh` stall exit as monitor infrastructure and skew `same-cause-repeat` / `RESUME_HINT`	Update stall-recovery `step8-shippr` Exit 4 handling in the same PR as implement SKILL FINDING_1: classify from foreground exit + `ship-pr-state.sh` only; remove `breadcrumb-monitor.sh` timeout/argv branch
4	in_scope	latent	architecture	plan.txt:147-148	Final grep gate omits phrases like `background+monitor` and `Family B background+monitor` that lack removed token substrings	Post-gate pass can leave misleading dispatch guidance in files that grep clean on `breadcrumb-monitor` / `LARCH_STATUS_FILE`	Add those phrases to the final grep gate, or enumerate prose-only files (stall-recovery, heavy-worker, `run-step2-dispatch.md`) in the Approach step

**1. `stall-recovery.md` mis-scoped (correctness)**  
The plan lists “Collapse the Family-B fence (1 ref)” for `skills/implement/references/stall-recovery.md`, but that file has no monitor fence—only prose at L5, L23–24, and L53 about background+monitor dispatch and monitor-specific Exit 4 routing. A fence-only edit would leave Step 18a recovery instructing deleted machinery.

**2. `heavy-worker.md` mis-scoped (correctness)**  
Same pattern: the plan cites one fence, but `skills/review/references/heavy-worker.md:55` is Wait Discipline prose requiring `collect-agent-results.sh` paired with `breadcrumb-monitor.sh`, with no Family-B fence in the file.

**3. FINDING_1 vs stall-recovery Exit 4 (risk-integration)**  
FINDING_1 correctly targets `skills/implement/SKILL.md` Post-Invoke / Exit-4 wrapper routing (~L1378, L1397). `stall-recovery.md:24` still teaches monitor-vs-writer Exit 4 split; it must be updated in the same change or Step 18a classification can diverge from the collapsed foreground model.

**4. Grep gate gap (latent)**  
The planned final grep (plan L147–148) would not catch surviving phrases like “Family B background+monitor pair” without removed tokens. Extending the gate or naming prose-only files in Approach reduces doc drift after a green grep.

[OUT_OF_SCOPE] **Companion script docs** — `scripts/run-step5-review.md:9-11` and `skills/implement/scripts/run-step2-dispatch.md:10-13` still describe top-level Family B / historical monitor pairing; the plan only trims the shim bullet on `run-step2-dispatch.md`, not these paragraphs. Worth a follow-up doc sweep; not required for fence collapse correctness if skill fences and grep gate pass.

[OUT_OF_SCOPE] **`skills/design/scripts/test-assess-plan-round.sh:282-354`** — sets `LARCH_BREADCRUMB_MONITOR_SH` to a mock script, but `assess-plan-round.sh` no longer reads that override (forensics `breadcrumbs/` dir only). Dead harness noise; no runtime breakage from Stage 4.

The plan’s shim ordering, FINDING_1 post-invoke rewrite, `test-design-structure.sh` / `test-lib-quiet.sh` / `test-collect-agent-results.sh` lockstep, and “breadcrumb” overload guardrails are otherwise aligned with the repo; `run-step5-review.sh` has no `larch_quiet_append_done_trap` caller (plan edge-case check is satisfied).

## Reviewer stderr (<TMPDIR>/codex-primary-plan-edge-output.txt.diag)

Failed with exit code 1 after 10s. Output size: 0 bytes.

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-innovation-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-innovation-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-innovation-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-innovation-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-innovation-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-pragmatic-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-pragmatic-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-pragmatic-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-pragmatic-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-pragmatic-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-pragmatic-output-phase3.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/codex-primary-plan-pragmatic-output-phase3.txt)

(file missing: <TMPDIR>/codex-primary-plan-pragmatic-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/codex-primary-plan-pragmatic-output-phase3.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-pragmatic-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-requirements-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-requirements-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-requirements-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-requirements-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-requirements-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-requirements-output-phase3.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/codex-primary-plan-requirements-output-phase3.txt)

(file missing: <TMPDIR>/codex-primary-plan-requirements-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/codex-primary-plan-requirements-output-phase3.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-requirements-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-dyn-caller-census-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-dyn-caller-census-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-dyn-caller-census-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-dyn-caller-census-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-dyn-caller-census-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-caller-census-output-phase3.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-caller-census-output-phase3.txt)

(file missing: <TMPDIR>/codex-primary-plan-dyn-caller-census-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-caller-census-output-phase3.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-caller-census-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 1)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-xref-sweep-output.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=1|FAILURE_REASON=Failed with exit code 1 after 20s. Output size: 0 bytes.

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-xref-sweep-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	skills/implement/SKILL.md:139	Rebase Checkpoint Macro still cites deleted `scripts/lint-foreground-markers.sh` denylist	Post-PR operators follow a dead script path for foreground-marker rules	Add an explicit implement-SKILL edit to drop or replace the L139 denylist pointer (e.g. point at `rebase-checkpoint-probe.md` only)
2	in_scope	important	correctness	skills/implement/SKILL.md:390,644,800,947,1217,1245,1280; skills/design/SKILL.md:362,1038	Plan mandates removing `# Background pair required: see BASH_AUTHORING.md §4` but not the `# Foreground required: see BASH_AUTHORING.md §4` variant	Mechanical pass leaves §4 anchors in non–Family-B fences; grep gate may catch late but plan step 2 underspecifies the comment family	Extend the implement/design SKILL edit bullets to delete or retarget all `BASH_AUTHORING.md §4` in-fence comments, not only Background-pair lines
3	in_scope	important	integration	skills/implement/references/stall-recovery.md:6,23-24,53	Plan says “Collapse the Family-B fence (1 ref)” but file has prose-only background+monitor / `breadcrumb-monitor.sh` / six-path wiring, no fence	Stall-recovery dispatch prose still instructs deleted monitor pairing and monitor-failure routing after Stage 4	Add an explicit stall-recovery trim: Contract L6, Procedure `step5-review`/`step8-shippr` bullets, Safety L53 — plain foreground + `ship-pr-state.sh` / Bash exit codes only
4	in_scope	important	integration	skills/review/references/heavy-worker.md:55	Plan says “Collapse the Family-B fence (1 ref)” but Wait Discipline is prose-only `breadcrumb-monitor.sh` pairing	No fence to collapse; heavy-worker subagent contract keeps deleted wait mechanism	Rewrite L55 to require plain foreground `collect-agent-results.sh` (or `<task-notification>` where applicable); drop monitor pairing sentence
5	in_scope	latent	correctness	skills/implement/references/rebase-rebump-subprocedure.md:189-192	`LARCH_PAIRED_PID_FILE` / `breadcrumb-monitor.sh` explanatory prose outside the ci-wait fence	Plan highlights only fence collapse; L189-192 can survive until grep gate	Fold into the rebase-rebump bullet: reframe ci-wait as nested synchronous under `ship-pr.sh` without monitor/paired-PID vocabulary
6	out_of_scope	nit	architecture	scripts/implement-bootstrap.md:163	Stale `lint-foreground-markers.sh` DENYLIST pointer after Stage 3 deletion	Contributors bootstrapping implement may search for a removed linter	Add a one-line bootstrap trim in a follow-up or widen Stage 4 public-doc sweep
7	out_of_scope	nit	correctness	scripts/relevant-checks.sh:137	Stale `# lint-foreground-markers: ok` comment on collect-agent-results routing	Misleading grep hits for removed linter	Remove or retarget the comment when touching relevant-checks (optional nit; not blocking Stage 4 grep gate)

**1. [correctness] `skills/implement/SKILL.md:139` — dead denylist pointer**

The Rebase Checkpoint Macro still says foreground markers + denylist come from `scripts/lint-foreground-markers.sh`, which Stage 3 deleted. The plan rewrites implement fences and NEVER rules but never calls out L139.

**2. [correctness] `# Foreground required` §4 comments omitted from plan wording**

Implement and design SKILLs still carry `# Foreground required: see BASH_AUTHORING.md §4` at the line ranges above. The plan only names `# Background pair required` removal for implement; design is covered only by generic “collapse fences.” A fence-only pass can miss these anchors until the final grep.

**3. [integration] `skills/implement/references/stall-recovery.md` — prose-only monitor contract**

There is no Family-B fence here. Contract L6, Procedure L23–24, and Safety L53 still require the background+monitor pair, six `LARCH_*` paths, and `breadcrumb-monitor.sh` infrastructure-failure routing. The plan’s “1 ref” fence collapse does not map to this file.

**4. [integration] `skills/review/references/heavy-worker.md:55` — prose-only monitor contract**

Same pattern: Wait Discipline mandates `collect-agent-results.sh` + `breadcrumb-monitor.sh` with no matching fence in the file.

**5. [latent] `skills/implement/references/rebase-rebump-subprocedure.md:189-192`**

Explanatory paired-PID / monitor prose remains after the planned ci-wait/ship-pr fence work. The final grep gate should force cleanup; the plan should still name this prose explicitly so the rebase-rebump edit is not fence-only.

**[OUT_OF_SCOPE] `scripts/implement-bootstrap.md:163`** — `lint-foreground-markers.sh` DENYLIST reference; not on the plan file list.

**[OUT_OF_SCOPE] `scripts/relevant-checks.sh:137`** — stale `lint-foreground-markers` comment; not on the plan file list (nit).

**AGENTS.md L57–58 (exonerated):** The plan trims the Family B exception, drops `BASH_AUTHORING.md §4`, `scripts/breadcrumb-monitor.md`, and `make lint-foreground*`, and restates long-script completion via `<task-notification>`. `scripts/test-implement-anti-polling-rule.sh` pins only the opening polling-ban literals (`Don't spawn a Monitor or a Bash`, etc.), not the deleted tail — so the rewrite should not break CI if executed as written.

**`.claude/rules/*.md`:** No hits for the searched literals.

**`larch-logs/**` and `CHANGELOG.md`:** Historical hits only; the plan’s grep gate excludes them.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-xref-sweep-output.txt.diag)

Failed with exit code 1 after 20s. Output size: 0 bytes.

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-dyn-test-gap-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-dyn-test-gap-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-dyn-test-gap-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-dyn-test-gap-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-dyn-test-gap-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-test-gap-output-phase3.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-test-gap-output-phase3.txt)

(file missing: <TMPDIR>/codex-primary-plan-dyn-test-gap-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-test-gap-output-phase3.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-test-gap-output-phase3.txt.diag)

  ```
### 1. correctness — grep-gate harnesses omitted from the file list

The plan’s final grep gate forbids `LARCH_DONE_SENTINEL`, `LARCH_STATUS_FILE`, `LARCH_PAIRED_PID_FILE`, and `LARCH_BREADCRUMB_STREAM` outside `larch-logs/**` and `CHANGELOG.md`, but several live test harnesses still `unset` those names and are not listed under **Files to modify/create** (only `test-design-structure.sh`, `test-lib-quiet.sh`, and `test-collect-agent-results.sh` are). Examples: `scripts/test-ship-pr.sh:11`, `skills/design/scripts/test-dispatch-plan-assessors.sh:5`, `skills/review/scripts/test-dispatch-panel.sh:12`.

**Suggested revision:** Add one sweep step (or enumerate these paths) so harness hygiene is updated in the same PR as the grep gate.

### 2. correctness — foreground fences still point at deleted §4

Deleting `BASH_AUTHORING.md` §4 is in scope, and the grep gate includes `BASH_AUTHORING.md §4`, but multiple **non–Family-B** fences still carry `# Foreground required: see BASH_AUTHORING.md §4` in `skills/implement/SKILL.md` (e.g. `390`, `644`, `800`) and `skills/design/SKILL.md` (`362`, `1038`). The plan’s skill edits focus on Family-B collapse, not these anchors.

**Suggested revision:** Retarget or remove those foreground comments during the same skill pass so §4 deletion and the grep gate stay aligned.

### 3. correctness — prose-only monitor routing not specified

Several listed files have **no** Family-B fence to collapse but still teach monitor/paired-PID semantics that must disappear:

- `skills/implement/references/stall-recovery.md:23-24,53` — `background+monitor envelope`, `breadcrumb-monitor.sh` infrastructure failures, “Family B background+monitor pair”
- `skills/implement/references/rebase-rebump-subprocedure.md:189-192` — `LARCH_PAIRED_PID_FILE` / `breadcrumb-monitor.sh` (no ci-wait/ship-pr fence exists here; only sync ci-wait policy at `187`)
- `skills/review/references/heavy-worker.md:55` — collector must pair with `breadcrumb-monitor.sh` (prose only)
- `skills/shared/voting-protocol.md:184` — same for voter collection (dispatch fence lives in `plan-review.md`, which is covered)

**Suggested revision:** Replace “collapse fence (1 ref)” with explicit prose rewrites for these locations so FINDING_1-style routing and the grep gate are not left stale.

[OUT_OF_SCOPE] `/.gitleaks.toml:25-26` still allowlists deleted `scripts/test-breadcrumb-monitor*` paths; harmless but stale after shim deletion—optional cleanup in a follow-up.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-arch-output.txt.diag)

Failed with exit code 1 after 20s. Output size: 0 bytes.

  ```
