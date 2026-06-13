### FINDING_1: Folded postplan omits full thin-fence exit-code contract
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-Requirements, Codex-Requirements, Cursor-dyn-step2b-contract, Codex-dyn-shell-wrapper-risk
- **Severity**: important
- **Concern**: The proposed fold copies only postplan return codes 0/10/12/13 into `design-step2b-drafter.sh` and is silent on the remaining arms in `design-step2b-postplan.sh` (rc 11 pause-save via `design-pause-save.sh`, rc 1/2 configuration/infrastructure hard aborts, and the default `*` fatal arm). If `design-postplan-emit.sh` exits 11 during merged postplan, or returns 1/2/unexpected, the drafter-success path can lose pause persistence, fail-closed abort behavior, or diagnostics that the terminal postplan fence preserves today.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Preserve the full existing postplan wrapper behavior in `design-step2b-drafter.sh`, including rc 11 pause-save and rc 1/2/unexpected abort arms. Use `exec design-step2b-postplan.sh` after the drafter success rows, or copy the full case block.
  - From Codex-Innovation: Copy the existing postplan rc handling into the drafter success branch, including rc 11 exec to design-pause-save.sh and the fatal 1/2/default abort arms, or delegate to a shared helper that preserves those arms.
  - From Cursor-Requirements: [SCOPE-REDUCTION] On structural success call design-step2b-postplan.sh --site step2b --snapshot-original internally instead of re-listing a partial rc matrix; or copy the full case arms including rc 11 exec pause-save and rc 1/2/* abort exits
  - From Codex-Requirements: Extend the drafter-wrapper postplan step to delegate to the existing postplan wrapper or preserve all non-success arms from design-step2b-postplan.sh, especially rc11 pause-save and rc1/2/default hard aborts
  - From Cursor-dyn-step2b-contract: Add rc 11 to the preserved contract: on rc 11 exec design-pause-save.sh with the same issue/repo threading as design-step2b-postplan.sh; or delegate success-path postplan to design-step2b-postplan.sh instead of inlining the case
  - From Codex-dyn-shell-wrapper-risk: Revise the plan to require reusing or transplanting the existing design-step2b-postplan.sh thin-fence case on drafter structural success: set +e capture, immediate display print, arms 0/10/11/12/13/2/1/*, completion sentinels, and VALIDATE_* row parsing. Prefer execing a shared helper to avoid duplicate side effects.


### FINDING_2: SKILL.md does not bind `_postplan_rc` from the merged drafter fence
- **Reviewer(s)**: Cursor-Requirements, Cursor-dyn-step2b-contract
- **Severity**: important
- **Concern**: The planned SKILL.md update still routes orchestrator logic as if postplan runs only in the retained terminal fence. After internal postplan on drafter success, the orchestrator may still treat `✅ 2b: drafter subprocess succeeded` as "run terminal postplan," never parse `POSTPLAN_RC=` / `POSTPLAN_STATUS=` from the combined fence, and miss rc 10/12/13 operator routing (validator failure, plan-size Split/Cancel, inline-retry branches) or double-run postplan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Explicitly state: after design-step2b-drafter.sh, parse POSTPLAN_RC/POSTPLAN_STATUS and capture display output for _postplan_out from that fence when postplan ran internally; use the retained terminal postplan fence only on inline-fallback/retry paths
  - From Cursor-dyn-step2b-contract: In SKILL.md require parsing POSTPLAN_RC= and POSTPLAN_STATUS= from design-step2b-drafter.sh stdout whenever the success line prints; skip the retained terminal fence for all internal-postplan outcomes not only ok


### FINDING_3: Merged drafter fence timeout may kill postplan before contract emission
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan keeps the Step 2b drafter Bash-tool timeout at 1800000 ms (1800 s) even though the same fence must now also run postplan. A drafter that succeeds near the outer timeout can be killed before `design-postplan-emit.sh` emits `POSTPLAN_RC` / `POSTPLAN_STATUS`, breaking the one-call success-path acceptance criterion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Update the plan to increase the Step 2b drafter Bash-tool timeout by a postplan cushion or lower the internal launcher timeout so the merged fence has time to finish postplan


### FINDING_4: Inline-retry gate prose still names only the terminal postplan fence
- **Reviewer(s)**: Cursor-dyn-step2b-contract
- **Severity**: important
- **Concern**: Current SKILL.md fires inline rewrite only when the terminal `design-step2b-postplan.sh` fence prints the retry warning or leaves `.step2b-postplan-inline-retry-pending`. After the fold, rc 10 inline-retry setup can occur inside `design-step2b-drafter.sh` with no terminal fence yet, so the orchestrator may skip inline rewrite on first drafter postplan defects and fall through to validator-failure handling instead.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-step2b-contract: Update SKILL.md so the inline-retry gate is: drafter fence or terminal postplan fence leaves .step2b-postplan-inline-retry-pending or prints the existing retry warning; then inline draft once and run the single retained terminal postplan fence


### FINDING_6: Folded wrapper lacks post-drafter pre-postplan pause-check boundary
- **Reviewer(s)**: Cursor-dyn-shell-wrapper-risk
- **Severity**: important
- **Concern**: Today pause requested while the external drafter runs is honored at the separate postplan fence boundary (`design-step2b-postplan.sh:89` checks `.pause-requested` before emit). A single-wrapper fold with only one pre-drafter pause-check can proceed into internal postplan without `exec design-pause-save.sh` when pause is requested during drafter execution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-shell-wrapper-risk: Pause requested while Codex/Claude drafter runs is honored today at the separate postplan fence boundary; a single-wrapper fold skips that boundary and can proceed into postplan/validator work without exec design-pause-save.sh. Add an explicit post-drafter pre-postplan pause-check mirroring design-step2b-postplan.sh:89 in the folded success branch (or subprocess-call design-step2b-postplan.sh which already owns it).


### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step2b-drafter.sh:19-40
- **Concern**: [SCOPE-REDUCTION] Folded postplan omits rc 11 pause arm from design-step2b-postplan.sh. Scenario: Plan inlines design-postplan-emit.sh and lists POSTPLAN_RC rows for 0/10/12/13 only. design-postplan-emit.sh exits 11 when pause is requested during merged postplan; design-step2b-postplan.sh handles that with exec design-pause-save.sh. Without the same arm, a pause during drafter-success postplan exits 11 or aborts instead of saving resumable state.
- **Proposed resolution**: On drafter-success path, delegate to design-step2b-postplan.sh --site step2b --snapshot-original instead of reimplementing the emit case block; or port case arm 11 verbatim (exec pause-save with REPO threading).


### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-step2b-contract
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:24-40
- **Concern**: [SCOPE-REDUCTION] Plan inlines design-postplan-emit.sh plus a hand-copied postplan wrapper layer instead of reusing design-step2b-postplan.sh on the drafter-success path. Scenario: Plan targets smallest orchestration change but duplicates the rc/sentinel case block already centralized in design-step2b-postplan.sh (108-196) including SCOUT_STALE_CLEARED=true on inline retry (159); partial copies already omit rc 11 and multiply drift risk versus Gate B and discussion callers that keep using the wrapper
- **Proposed resolution**: On drafter structural success call design-step2b-postplan.sh --site step2b --snapshot-original internally (after the success line) rather than reimplementing the postplan case arms in design-step2b-drafter.sh


### FINDING_12:
- **Reviewer(s)**: Codex-dyn-step2b-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step2b-postplan.sh:100-196; skills/design/scripts/design-postplan-emit.sh:428-453
- **Concern**: [SCOPE-REDUCTION] Drafter success path plans to reimplement the postplan thin-fence contract instead of reusing it. Scenario: design-postplan-emit.sh can exit 11 for pause-save, and the current thin fence handles that branch; the plan enumerates only 0/10/12/13 rows, so a pause requested after drafter success can lose byte-compatible routing
- **Proposed resolution**: Have design-step2b-drafter.sh call the existing design-step2b-postplan.sh --site step2b --snapshot-original internally on structural success, or require an exact shared helper that preserves every current case arm including 11




### FINDING_1: Folded prelude must replace early pause-check before Step 2a validation
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Folding `design-step2b-prelude.sh` into `design-step2b-drafter.sh` without removing the wrapper's existing early pause-check (currently at line 89, before Step 2a sentinel validation) can duplicate pause boundaries or run pause-save before invalid Step 2a artifacts are rejected. That conflicts with the folded-sentinel rule requiring validation/repair before pause and with the prelude's intended `sentinel validation → step-2a repair → single pause-check → timing mark` sequence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Merge prelude as: source-env → sentinel validation → `.completed/step-2a` repair → single pause-check → timing mark → existing `.step2b-postplan-fallback-used` init → drafter launch; delete the standalone line-89 pause once prelude pause is in place
  - From Cursor-Pragmatic: Specify merge order explicitly: after source-env, run step2b_exact_line_file sentinel checks and step-2a repair, then a single pause-check, then timing mark, then drafter work. Delete or relocate the current line 89 pause-check so it is not duplicated.
  - From Cursor-Requirements: Specify merge order explicitly: after source-env, run step2b_exact_line_file sentinel checks and step-2a repair, then a single pause-check, then timing mark, then drafter work. Delete or relocate the current line 89 pause-check so it is not duplicated.


### FINDING_2: POSTPLAN routing must use authoritative wrapper contract rows, not Bash exit code or polluted stdout
- **Reviewer(s)**: Cursor-Arch, Codex-Generic
- **Severity**: important
- **Concern**: On the drafter-success path, orchestrator routing for `_postplan_rc` / `POSTPLAN_STATUS` is unsafe in two ways. First, `design-step2b-postplan.sh` can print `POSTPLAN_RC=10|12|13` in case arms that fall through without `exit $_postplan_rc`, so the combined drafter-fence Bash exit code may be 0 while stdout carries a non-zero contract rc, misrouting to Step 3 or skipping Split/Cancel/validator handling. Second, if routing parses `POSTPLAN_*` from the full combined drafter-fence output (which includes the external drafter's plan preview), a plan line such as `POSTPLAN_RC=12` or `POSTPLAN_STATUS=ok` can be mistaken for wrapper-owned machine rows and break the rc 10/12/13 routing contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In SKILL Step 2b routing prose, require `_postplan_rc` / `POSTPLAN_STATUS` parsing from captured fence stdout (`POSTPLAN_RC=` / `POSTPLAN_STATUS=` rows) and explicitly forbid using the Bash tool exit code alone on the drafter-success path
  - From Codex-Generic: When updating the Step 2b routing, parse only wrapper-owned machine rows, for example the last whole-line ^POSTPLAN_RC= and ^POSTPLAN_STATUS= rows after DRAFTER_STATUS=succeeded, or write/read a small wrapper result sidecar. Do not grep arbitrary combined stdout.


### FINDING_3: Step 2b SKILL prose must define terminal postplan skip vs inline-retry without stale success-path wording
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: important
- **Concern**: Step 2b routing prose in `skills/design/SKILL.md` is ambiguous about when the retained terminal `design-step2b-postplan.sh` fence runs. Without an explicit inline-retry exception, an implementer can skip the retained fence even when rc 10 created `.step2b-postplan-inline-retry-pending`, blocking the one inline rewrite plus single terminal postplan retry. Separately, current success-path sentences still tell the orchestrator to "proceed directly to the retained terminal postplan fence" and "continue at the terminal postplan fence" after drafter success, which can reintroduce double-postplan even when the plan adds internal postplan in the wrapper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: State skip as: on first drafter-fence return, skip the retained terminal postplan fence only when `DRAFTER_STATUS=succeeded` (or `POSTPLAN_RC=` is present) and `.step2b-postplan-inline-retry-pending` is absent; when the pending sentinel exists, run inline rewrite once, then run the retained terminal postplan fence exactly once
  - From Cursor-Requirements: In the Step 2b drafter subsection, replace success-path wording so internal postplan completion skips the terminal `design-step2b-postplan.sh` fence and continues from parsed `POSTPLAN_RC`/`POSTPLAN_STATUS`; keep the terminal fence only for drafter-fallback and inline-retry paths. Add a structure pin that forbids the old "continue at the terminal postplan fence" success-path phrase alongside the new skip rule.


### FINDING_4: Existing drafter harness cases need folded-prelude and postplan scaffolding
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `test-design-step2b-drafter.sh` token sidecar cases (lines 47–116) lack folded-prelude artifact setup and postplan stubs while the plan only adds that scaffolding for new cases. Folding prelude guards into `design-step2b-drafter.sh` will make current success-path tests fail at sentinel validation before Codex launch and before delegated postplan, so the harness exits non-zero and never reaches token-ingestion assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Apply the planned common prelude artifact setup and a fake design-step2b-postplan.sh stub to every existing case, or fold the token sidecar scenarios into the new delegated-postplan tests




### FINDING_1: Missing fail-closed when internal postplan output is incomplete
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The proposed Step 2b routing tells the orchestrator to skip the retained terminal `design-step2b-postplan.sh` fence when the drafter wrapper reports internal postplan success. There is no fail-closed branch when `DRAFTER_STATUS=succeeded` appears but trailing whole-line `POSTPLAN_RC=` / `POSTPLAN_STATUS=` rows are absent (outer Bash timeout, truncated stdout, `exec` failure, or killed postplan). A prompt-side reader can treat the human success line as sufficient and advance to Step 3 with an unvalidated plan, bypassing plan-command validation, plan-size gates, and `.completed/step-2b` / `.completed/step-2b.5` completion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add SKILL routing: when DRAFTER_STATUS=succeeded and POSTPLAN_RC/POSTPLAN_STATUS are absent after the drafter fence, either run the retained terminal postplan fence once or abort with a loud error; pin the same rule in test-design-step2b-drafter.sh or test-design-structure.sh
  - From Cursor-Pragmatic: Add an explicit SKILL branch: if `DRAFTER_STATUS=succeeded` and no whole-line `POSTPLAN_RC=` appears after that marker, do not route to Step 3; run the retained `design-step2b-postplan.sh --site step2b --snapshot-original` fence once as fail-safe (or hard-abort). Pin this in `scripts/test-design-structure.sh` and add a drafter-harness case where the postplan stub exits before emitting `POSTPLAN_RC=`.


### FINDING_2: Plan preview can spoof wrapper-owned stdout anchors
- **Reviewer(s)**: Cursor-Innovation, Codex-Generic
- **Severity**: important
- **Concern**: On the drafter-success path, `emit-design-plan-preview.sh` prints the full `plan.txt` body (including `## Implementation Plan`) before the wrapper emits real status rows. `plan.txt` is untrusted generated content and can contain whole-line literals such as `DRAFTER_STATUS=succeeded` or `POSTPLAN_RC=0`. If SKILL.md instructs the orchestrator to parse the first `DRAFTER_STATUS=succeeded` or first `POSTPLAN_RC=` after preview output, spoofed plan-body lines can mis-bind `_postplan_rc` and make fatal, pause-save, or operator-required postplan exits (rc 10/12/13) look successful.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Anchor on the `✅ 2b: drafter subprocess succeeded` line (or the last `^DRAFTER_STATUS=succeeded$` after it), then take the last `^POSTPLAN_RC=` / `^POSTPLAN_STATUS=` rows only after that point. Pin this in `SKILL.md` and `scripts/test-design-structure.sh`.
  - From Codex-Generic: Require SKILL.md to parse after the final wrapper-emitted DRAFTER_STATUS=succeeded row, or add an unambiguous post-preview machine-row delimiter. Add the narrow structure or drafter-harness regression with spoofed preview lines before the real marker.


### FINDING_3: Folded prelude must preserve `step2b_exact_line_file` sentinel checks
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The proposal folds `design-step2b-prelude.sh` into `design-step2b-drafter.sh` but does not explicitly require porting `step2b_exact_line_file`, which today enforces single-line exact-match sentinels (`NO_SKETCHES`, `NO_CONTESTED_DECISIONS`) via awk (exactly one line, no trailing content). Reimplemented or simplified checks may accept multi-line or trailing-whitespace sentinel files and let invalid Step 2a artifacts reach the external drafter.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Port `step2b_exact_line_file` verbatim (or `source` the prelude helper) before the drafter launch; extend harness case 1 to cover trailing-newline rejection.




### FINDING_1: rc 11 pause arm omits POSTPLAN contract rows
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Generic
- **Severity**: important
- **Concern**: The plan and structure pins require `design-step2b-postplan.sh` to emit `POSTPLAN_RC=11` and `POSTPLAN_STATUS=pause-save` before `design-pause-save.sh` on the rc 11 path, but the plan’s Files section does not list the `.sh` as a code change. Today the rc 11 arm at lines 169–170 only `exec`s pause-save with no `POSTPLAN_*` rows (the line-89 pre-emit pause path has the same gap). Harness case 8 and new prompt-side fail-closed/missing-row logic expect those rows; without them pause routing can be misread and the retained postplan fail-safe may run instead of honoring pause.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: skills/design/scripts/design-step2b-postplan.sh: print POSTPLAN_RC=11 and POSTPLAN_STATUS=pause-save before exec design-pause-save.sh in the rc 11 arm (and consider the line-89 pre-emit pause path for the same rows)
  - From Cursor-Innovation: Add ### UPDATED: skills/design/scripts/design-step2b-postplan.sh: print POSTPLAN_RC=11 and POSTPLAN_STATUS=pause-save before exec design-pause-save.sh; extend test-design-step2b-drafter.sh case 8 to assert wrapper output, not only the stub
  - From Cursor-Pragmatic: Add ### UPDATED: skills/design/scripts/design-step2b-postplan.sh: print POSTPLAN_RC=11 and POSTPLAN_STATUS=pause-save immediately before the existing pause-save exec in the rc 11 case
  - From Cursor-Requirements: Add ### UPDATED: design-step2b-postplan.sh: printf POSTPLAN_RC=11 and POSTPLAN_STATUS=pause-save immediately before the existing exec design-pause-save.sh arm
  - From Codex-Generic: Add skills/design/scripts/design-step2b-postplan.sh to the plan and update the rc 11 arm to emit POSTPLAN_RC=11 and POSTPLAN_STATUS=pause-save before execing design-pause-save.sh




### FINDING_1: Sourcing prelude for sentinel helper is unsafe
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Reusing `step2b_exact_line_file` by sourcing `design-step2b-prelude.sh` inside `design-step2b-drafter.sh` is unsafe because the prelude runs top-level sentinel validation and can `exit 1` on source. An implementer following the plan could break the drafter wrapper or double-validate in the wrong order.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Replace the option with "copy the step2b_exact_line_file function body into design-step2b-drafter.sh" or extract a non-executing include; forbid sourcing design-step2b-prelude.sh for the helper


### FINDING_2: Delegated postplan exec omits pinned launcher transport argv
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The delegated postplan `exec` does not pin launcher transport argv. The plan says to pass environment and session args but does not require forwarding `--session-env-path`, `--claude-pid`, and `--plugin-root` on the exec line. Inherited exports usually work, but delegated postplan still calls `design_source_env_optional` from argv and pre-emit pause uses `ISSUE_NUMBER` and `REPO` from wrapper scope. A path without exported session keys can pause-save or emit with empty issue context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pin the exec invocation to design-step2b-postplan.sh --site step2b --snapshot-original --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" --plugin-root "$CLAUDE_PLUGIN_ROOT" and document it in design-step2b-drafter.md.


### FINDING_4: SKILL lacks `_postplan_out` slicing rule for merged fence capture
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: SKILL does not define how to slice `_postplan_out` from the merged drafter fence capture. rc 12/13 routing still references `_postplan_out` (line 459). Binding the full combined stdout (preview + delimiter + postplan) can change operator-visible plan-size output versus today's separate postplan fence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Bind `_postplan_out` only to the delegated postplan wrapper stdout segment (after `DRAFTER_STATUS=succeeded`, before wrapper exit), not the full fence capture including `## Implementation Plan` preview



