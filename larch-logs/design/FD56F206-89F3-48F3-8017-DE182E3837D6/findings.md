### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-step2-dispatch.sh:115 (Test M9)
- **Concern**: Test M9 expects REASON=submodule-modified. Scenario: Dispatcher post-implementer submodule guard emits submodule-dirty at step2-implement.sh:579, not submodule-modified
- **Proposed resolution**: M9 assertion will fail in CI; implementers may wire the wrong bail token Change Test M9 expected REASON to submodule-dirty; align plan prose at step2-implement.sh recovery guard step 4 with the existing token

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:942-1052
- **Concern**: Recovery sub-branch does not override the generic claude_fallback §2.4 flow. Scenario: After RECOVERY_FROM, orchestrator still hits opportunistic questions and Implement per the materialized plan (lines 1050-1052), duplicating or fighting preserved Codex/Cursor edits
- **Proposed resolution**: At the start of §2.4, branch on RECOVERY_FROM: skip opportunistic Q&A and the full re-implement block; run only recovery steps 1-3 then jump to Step 3; update the Step 2 entry matrix row to document preserve-and-commit vs implement-from-scratch

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:95-98
- **Concern**: Plan-scope check cites plan Files to modify section only. Scenario: Canonical /design plans use ## Files to modify/create with ### NEW:/UPDATED:/REWRITTEN: headings (skills/design/SKILL.md:585; scout write_scope_files at scout-plan-archetypes-wrapper.sh:125-144); literal Files to modify misses most plans and causes false recovery-out-of-scope or missed OOS files
- **Proposed resolution**: Derive allowed paths with the same ### NEW|UPDATED|REWRITTEN regex/backtick extraction as write_scope_files (extract to a shared helper under scripts/ or skills/implement/scripts/); compare post-launch delta paths to that set

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step2-implement.sh:286-405 (proposed)
- **Concern**: Pre-launch porcelain gate lacks a concrete delta algorithm. Scenario: Plan names step2-prelaunch-porcelain.txt but not write-once timing (before run_launcher after Step 3 rm), porcelain path parsing, or set-difference vs baseline; ambiguous implementation risks wrong empty/non-empty gate
- **Proposed resolution**: Specify: write-once snapshot at first external launch; after implementer, diff current git status --porcelain --untracked-files=all against snapshot (normalize path from column 2+); gate on non-empty diff only

### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:98-99
- **Concern**: Step 4 file list is re-read from live porcelain at commit time. Scenario: Tree can change between §2.4 recovery and Step 4 (orchestrator edits, hooks); commit-implementation.sh may stage wrong paths vs dispatcher-intended post-launch delta
- **Proposed resolution**: Persist recovery file list at Step 2.4 (e.g. $IMPLEMENT_TMPDIR/step2-recovery-paths.txt from the same prelaunch diff) and pass that list to Step 4; do not re-derive from ad-hoc git status at commit time

### FINDING_6:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:989-1010
- **Concern**: §2.1 KV parse / §2.1.5 omit inverse RECOVERY_* rules. Scenario: Plan adds optional RECOVERY_FROM when STATUS=claude_fallback but not illegal RECOVERY_* on STATUS=complete|needs_qa|bailed; malformed dispatcher edits could confuse envelope handling
- **Proposed resolution**: Add parse lines for RECOVERY_FROM and RECOVERY_PRIOR_TOOL; in §2.1.5 fail-closed if RECOVERY_* present while STATUS!=claude_fallback (orchestrator-envelope-invalid)

### FINDING_7:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:937-942
- **Concern**: Entry preconditions matrix unchanged for recovery. Scenario: Row claude_fallback still says main-agent code edits per the plan with no RECOVERY_FROM exception; conflicts with NEVER preserve-edits and recovery sub-branch
- **Proposed resolution**: Extend matrix (or footnote on claude_fallback): when RECOVERY_FROM=manifest-schema-invalid, permitted actions are scope check + synthesized commit only; forbidden: re-implement from plan

### FINDING_8:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/step2-implement.sh:474-476
- **Concern**: Recovery only runs after LAUNCHER_EXIT=0. Scenario: Non-zero launcher exit with a malformed manifest on disk bails with codex-runtime-failure/cursor-runtime-failure before schema validation; same lost-work scenario as manifest-schema-invalid without recovery
- **Proposed resolution**: Document as known gap or extend recovery precheck: if MANIFEST_WRITTEN=true and manifest fails schema, consider recovery before runtime-failure bail when tree/guards pass

### FINDING_9:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: skills/implement/scripts/step2-implement.sh:75 (plan prose)
- **Concern**: Recovery guard bullet names submodule-modified. Scenario: Matches Test M9 typo; live bail token is submodule-dirty
- **Proposed resolution**: Use submodule-dirty everywhere in plan comments and tests

### FINDING_10:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: nit
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:1044-1048
- **Concern**: No recovery-specific operator message. Scenario: Recovery claude_fallback may print Cursor unavailable or generic main-agent messages, obscuring manifest-schema-invalid salvage
- **Proposed resolution**: Add first-match message when RECOVERY_FROM is set (e.g. manifest invalid — committing prior implementer work via main agent)

### FINDING_11:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: nit
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-step2-dispatch.md:1-46
- **Concern**: Harness doc not listed in plan updates. Scenario: M1-M12 behaviors won't be documented in the contract file consumed by reviewers
- **Proposed resolution**: Add test-step2-dispatch.md bullets for M1-M12 (recovery, carve-outs, porcelain/untracked)

### FINDING_12:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: security
- **Location**: skills/implement/scripts/step2-implement.sh:574-580; skills/implement/scripts/step2-implement.sh:600-632; skills/implement/references/codex-manifest-schema.md:72-73
- **Concern**: FINDING_1 [security] Recovery submodule guard is both token-inconsistent and weaker than the complete path. Scenario: The plan says to factor only the Step 6 submodule status guard and expects REASON=submodule-modified, but current contracts use submodule-dirty for git submodule status and protected-path-modified for forbidden manifest paths. On recovery there is no valid manifest path list, so a post-launch delta under a submodule root is not covered by the complete path's Step 7a path-normalization layer.
- **Proposed resolution**: Use existing reason tokens or deliberately update every contract. Add an explicit recovery check that compares post-launch delta paths against discovered submodule roots before emitting claude_fallback, then test the chosen existing reason consistently.

### FINDING_13:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:935-943; skills/implement/SKILL.md:1013-1033
- **Concern**: FINDING_2 [architecture] The authoritative Step 2 matrix is not updated for recovery claude_fallback. Scenario: The plan adds RECOVERY_FROM behavior under Step 2.4, but the matrix still says every claude_fallback permits main-agent code edits per plan and declares itself authoritative over downstream disagreements. A recovery envelope could therefore be handled as normal fallback implementation and edit over the recovered work.
- **Proposed resolution**: Update the matrix and the 2.2 claude_fallback bullet to split RECOVERY_FROM-present recovery from ordinary fallback: recovery may inspect, validate scope, synthesize a redacted message, and commit existing deltas, but must not re-implement.

### FINDING_14:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1050-1054; skills/implement/SKILL.md:1100-1109; skills/implement/SKILL.md:1132-1139
- **Concern**: FINDING_3 [correctness] Recovery freezes the commit file list before Step 3 can mutate files. Scenario: The plan says Step 2.4 should use the initial porcelain output as the Step 4 file list, but Step 3's existing checks repair loop can apply lint fixes or main-agent repairs before Step 4. Those post-check files would be left uncommitted or bypass the recovery scope check.
- **Proposed resolution**: After Step 3 passes, recompute the working-tree delta, rerun the plan-scope check, redact or reuse the recovery commit message, and pass the final scoped file list to commit-implementation.sh.

### FINDING_15:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:989-1011
- **Concern**: FINDING_4 [risk-integration] Recovery envelope validation does not require RECOVERY_PRIOR_TOOL when RECOVERY_FROM is present. Scenario: The plan validates RECOVERY_PRIOR_TOOL only when present, but the recovery branch composes a commit message using it. A malformed dispatcher envelope with RECOVERY_FROM but no prior-tool key would pass the described validation and produce an incomplete or misleading recovery record.
- **Proposed resolution**: Make RECOVERY_FROM and RECOVERY_PRIOR_TOOL an all-or-none pair in §2.1.5: RECOVERY_FROM=manifest-schema-invalid requires RECOVERY_PRIOR_TOOL in {codex,cursor}, and RECOVERY_PRIOR_TOOL without RECOVERY_FROM is invalid.

### FINDING_16:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step2-implement.sh:482-490
- **Concern**: F1: Recovery gate treats jq parse failures the same as a deliberately missing status field. Scenario: A truncated or non-JSON manifest makes STATUS empty, so a run with partial working-tree edits can be recovered and committed even though the implementer never declared completion
- **Proposed resolution**: Distinguish parse_ok from missing field; recover empty status only for a valid JSON object matching the known legacy fingerprint, and bail on unparsable/truncated manifests

### FINDING_17:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step2-implement.sh:405-410
- **Concern**: F2: Porcelain baseline cannot detect edits to paths already dirty before launch. Scenario: If README.md is already " M README.md" before launch and the implementer changes it again, pre/post porcelain lines are identical, so recovery sees no post-launch delta and preserves neither the implementer work nor a useful recovery signal
- **Proposed resolution**: Compare content snapshots, not just porcelain rows; for pre-dirty path overlap either fail closed with a dedicated reason or record pre/post diff hashes and require manual recovery

### FINDING_18:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1132-1139
- **Concern**: F3: Recovery commit file list is underspecified and unsafe if derived from porcelain text. Scenario: Paths with spaces, tabs, renames, copies, or quoted characters can be split or passed as "R old -> new", causing commit-implementation.sh to stage the wrong path or fail after recovery succeeded
- **Proposed resolution**: Define a NUL-safe path handoff: use porcelain -z or git diff/ls-files -z, normalize rename records to actual pathspecs, and pass an array or add --pathspec-from-file --pathspec-file-nul support

### FINDING_19:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/step2-implement.sh:574-580; skills/implement/references/codex-manifest-schema.md:71-73
- **Concern**: F4: Proposed recovery relies on a submodule guard that misses dirty submodule worktrees and names a non-existent reason token. Scenario: git submodule status can report dirty submodule contents with a clean leading status plus a dirty suffix; the existing grep only checks leading + - U, and the plan/tests expect submodule-modified while the contract is submodule-dirty
- **Proposed resolution**: Harden run_post_implementer_safety_gates to detect dirty suffixes or use git submodule foreach/git status --ignore-submodules=none, and keep the emitted token as submodule-dirty unless all docs/schema/tests are renamed together

### FINDING_20:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:1553-1557; skills/implement/scripts/step2-implement.sh:480
- **Concern**: F5: Recovery leaves manifest-raw.json available for later run-log publication even when the manifest is invalid. Scenario: After cp to manifest-raw.json, a recovery from schema-invalid can continue to Step 7a, whose log writer publishes manifest-raw.json as codex-impl-manifest-raw.json with no JSON validation; malformed or legacy-invalid data can silently enter committed run logs
- **Proposed resolution**: On recovery, remove or quarantine manifest-raw.json before Step 7a, or replace it with a valid redacted recovery metadata JSON that records RECOVERY_FROM and prior tool without publishing the invalid manifest as a JSON batch

### FINDING_21:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1031-1054
- **Concern**: Recovery path has no machine-readable post-launch path set and tells Step 2.4 to use current porcelain output. Scenario: Pre-existing dirty user files present before Step 2 are still visible in current git status and can be swept into the synthesized recovery commit despite the plan claiming they are excluded
- **Proposed resolution**: Have step2-implement.sh emit or persist a NUL-safe RECOVERY_PATHS_FILE computed as current tree minus step2-prelaunch-porcelain; Step 2.4 must validate and commit only that file list; add a test with a pre-existing dirty file plus recovered implementer edit proving only the implementer edit is staged

### FINDING_22:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/step2-implement.sh:574-580
- **Concern**: Plan introduces submodule-modified as a recovery bail reason even though the dispatcher and schema contract use submodule-dirty and protected-path-modified. Scenario: Tests or downstream reason handling will assert a token that the current contract does not define; alternatively implementation may add an undocumented token and break callers that key off the existing bail-reason list
- **Proposed resolution**: Use the existing token intentionally: submodule-dirty when factoring the current git submodule status guard, or protected-path-modified for a new porcelain-path-under-submodule check; update M9 and docs to match

### FINDING_23:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: skills/implement/scripts/step2-implement.sh:574-580
- **Concern**: Factoring only the current submodule status guard does not prove a post-launch porcelain delta under a submodule is blocked. Scenario: A modified file inside a checked-out submodule can appear as a parent porcelain change while git submodule status may not report the internal dirty worktree as a leading + - or U; recovery could authorize claude_fallback with forbidden submodule edits still present
- **Proposed resolution**: When computing the recovery delta, explicitly reject any changed path equal to or under discovered submodule roots before emitting recovery; test both gitlink HEAD movement and dirty file content inside a submodule

### FINDING_24:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:1031-1054; skills/implement/scripts/commit-implementation.sh:23-44
- **Concern**: Finding 1: Recovery Step 2.4 has no concrete post-launch path set and tells Step 4 to use porcelain output as the commit file list. Scenario: `git status --porcelain --untracked-files=all` includes pre-existing dirty files as well as recovery edits, and its raw lines are not valid path arguments for `commit-implementation.sh`; a recovery can either commit operator pre-existing dirt or fail/mis-stage paths like ` M file`
- **Proposed resolution**: Have `step2-implement.sh` write a deterministic recovery delta artifact, preferably NUL-delimited paths computed against the pre-launch snapshot, emit its path, and make Step 2.4 scope-check and commit exactly those paths; add a regression with a pre-existing dirty file plus a post-launch recovery edit

### FINDING_25:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step2-implement.sh:574-580; skills/implement/references/codex-manifest-schema.md:72-73
- **Concern**: Finding 2: Plan uses a non-existent `submodule-modified` bail token for the recovery safety gate. Scenario: Current dispatcher and schema use `submodule-dirty`; implementing the plan literally makes M9 expect the wrong reason and drifts the stdout/bail-token contract
- **Proposed resolution**: Change the plan/tests/recovery helper to preserve `REASON=submodule-dirty`, or explicitly rename the token everywhere including schema docs, stdout docs, tests, and any downstream reason routing

### FINDING_26:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-step2-dispatch.sh:114
- **Concern**: skills/implement/scripts/step2-implement.sh:579. Scenario: Test M9 and emit_manifest_invalid_or-recover prose expect REASON=submodule-modified
- **Proposed resolution**: Dispatcher and step2-implement.md document submodule-dirty; M9 would fail or force a wrong new bail token Align plan and M9 to submodule-dirty (same token as Step 6c today)

### FINDING_27:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:933-943
- **Concern**: Recovery sub-branch conflicts with the authoritative Step 2 matrix. Scenario: The plan only extends section 2.4, but the matrix says claude_fallback permits main-agent code edits per the plan and explicitly wins over downstream disagreement, so RECOVERY_FROM runs can still be interpreted as ordinary reimplementation instead of commit-only recovery
- **Proposed resolution**: Update the matrix and section 2.2 row to carve out RECOVERY_FROM=manifest-schema-invalid: no Edit/Write reimplementation, only scope sanity, redacted message synthesis, and Step 4 commit over the approved recovery delta

### FINDING_28:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:999-1011
- **Concern**: RECOVERY_PRIOR_TOOL is optional despite being used by recovery. Scenario: The plan validates RECOVERY_PRIOR_TOOL only when present, but Step 2.4 uses it in the synthesized message whenever RECOVERY_FROM is present; a malformed envelope can produce an empty prior-tool label or fail under strict shell handling
- **Proposed resolution**: Make RECOVERY_PRIOR_TOOL required when RECOVERY_FROM=manifest-schema-invalid, require codex|cursor, and fail closed with orchestrator-envelope-invalid when missing or invalid

### FINDING_29:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: skills/implement/scripts/commit-implementation.sh:44; scripts/git-commit.sh:70-91
- **Concern**: Recovery commit can include pre-existing staged user changes. Scenario: The plan says Step 4 needs no changes and should pass recovery porcelain files to commit-implementation.sh, but git-commit.sh commits any already staged content; a user-staged file from before launch can be swept into the synthesized recovery commit
- **Proposed resolution**: Add a recovery-safe commit mode using git commit --only -- <post-launch-delta-files>, or fail closed when the pre-launch index is non-empty; add tests with pre-existing staged and unstaged dirty files

### FINDING_30:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step2-implement.sh:574-580
- **Concern**: Plan invents the submodule-modified bail token. Scenario: The current dispatcher and schema use submodule-dirty for the post-implementer submodule guard, but the plan and M9 expect submodule-modified, causing test/doc drift or an unrecognized reason token
- **Proposed resolution**: Use the existing submodule-dirty token in the shared guard, tests, and docs, or explicitly add submodule-modified to the schema and all routing docs

### FINDING_31:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: skills/implement/references/codex-manifest-schema.md:13-31
- **Concern**: Inline template exact-shape acceptance lacks validation. Scenario: The plan requires the inline template to match the canonical manifest shape, but the proposed prompt tests only grep three substrings and would pass if required keys like lines_added, todos_left, or oos_observations were omitted
- **Proposed resolution**: Add a test that extracts/parses the inline JSON template or at least asserts every canonical required field and nested field appears in both generated implementer prompts

### FINDING_32:
- **Reviewer(s)**: Cursor-dyn-variable-scope
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step2-implement.sh:579
- **Concern**: skills/implement/scripts/test-step2-dispatch.sh (Test M9). Scenario: Plan and Test M9 expect REASON=submodule-modified but dispatcher emits submodule-dirty
- **Proposed resolution**: Implementer copies plan token; M9 fails while production uses submodule-dirty, or code emits wrong token and breaks SKILL.md / codex-manifest-schema.md routing Align plan step 4 and Test M9 with existing token submodule-dirty (skills/implement/scripts/step2-implement.sh:579, step2-implement.md:28)

### FINDING_33:
- **Reviewer(s)**: Codex-dyn-variable-scope
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step2-implement.sh:574-580; skills/implement/references/codex-manifest-schema.md:71-74
- **Concern**: The plan uses the non-existent bail token submodule-modified for the factored safety gate and Test M9, but the current dispatcher and schema use submodule-dirty. Scenario: The recovery helper would either implement the plan literally and introduce a new undocumented REASON, or the planned M9 assertion would fail against the existing success-path-compatible behavior
- **Proposed resolution**: Change the plan and M9 to expect submodule-dirty, or explicitly add and document a token rename across step2-implement.sh, step2-implement.md, codex-manifest-schema.md, SECURITY.md, and tests

### FINDING_34:
- **Reviewer(s)**: Cursor-dyn-predicate-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: agents/_implementer-base.md:33-49
- **Concern**: Proposed self-validate jq uses strict .schema_version == "1" while dispatcher shell check accepts jq -r stringification of numeric 1. Scenario: Implementer writes "schema_version": 1 (JSON number); prompt jq -e fails and blocks rename; dispatcher [[ "$SCHEMA_VERSION" != "1" ]] passes after jq -r → false-negative self-validation and unnecessary rewrite loops
- **Proposed resolution**: Align predicate with dispatcher: e.g. ((.schema_version | tostring) == "1") or document string-only and add the same rule to the shell SCHEMA_VERSION gate at skills/implement/scripts/step2-implement.sh:486-487

### FINDING_35:
- **Reviewer(s)**: Codex-dyn-predicate-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:44-49; skills/implement/scripts/step2-implement.sh:510-545; skills/implement/references/codex-manifest-schema.md:133-139
- **Concern**: needs_qa self-validation omits the dispatcher companion qa-pending.json predicate. Scenario: The prompt-side jq can pass a needs_qa manifest while qa-pending.json is missing or malformed; the dispatcher then bails with qa-pending-missing at lines 541-545, so the prevention layer is weaker than the actual needs_qa branch
- **Proposed resolution**: Add a second self-validation command for <QA_PENDING_PATH>.tmp or <QA_PENDING_PATH> requiring .questions array length > 0 before any needs_qa manifest rename; keep the manifest check as-is

### FINDING_36:
- **Reviewer(s)**: Codex-dyn-predicate-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:23-25; skills/implement/references/codex-manifest-schema.md:13-31; skills/implement/scripts/step2-implement.sh:489-507
- **Concern**: The proposed template field list omits tests_added_or_modified and does not explicitly list status. Scenario: The prose says the JSON template is complete, but the enumerated fields skip a dispatcher-required complete field; an implementer following the parenthetical can emit a complete manifest that fails .tests_added_or_modified type == array or status enum validation
- **Proposed resolution**: Replace the prose-only parenthetical with the literal canonical JSON template including schema_version, status, files_touched path/lines_added/lines_removed, tests_added_or_modified, summary_bullets, commit_message, todos_left, oos_observations, bail_reason, and needs_qa.questions id/text

### FINDING_37:
- **Reviewer(s)**: Codex-dyn-predicate-parity
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:75-75; <TMPDIR>/plan.txt:113-114; skills/implement/scripts/step2-implement.sh:574-580; skills/implement/references/codex-manifest-schema.md:72-73
- **Concern**: Submodule recovery/test expectation uses submodule-modified instead of the dispatcher token submodule-dirty. Scenario: The factored safety gate would preserve current dispatcher behavior, but the plan and Test M9 assert a different reason token, causing the planned regression test or docs to reject correct output
- **Proposed resolution**: Change the planned guard reason and Test M9 expectation to submodule-dirty

### FINDING_38:
- **Reviewer(s)**: Cursor-dyn-baseline-snapshot
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:74
- **Concern**: Post-launch delta gate lacks a set-difference algorithm. Scenario: Edge case promises pre-existing dirty is excluded, but gate 3 only says compare snapshots and bail if delta is empty; a naive `[[ -n "$(git status --porcelain …)" ]]` check would false-positive recover on pre-launch dirtiness; M2/M7 do not catch that
- **Proposed resolution**: Specify implementation: capture `git -C "$REPO_ROOT" status --porcelain --untracked-files=all` into `$TMPDIR_ARG/step2-prelaunch-porcelain.txt` on first write (Step 1), then `comm -13 <(sort pre) <(sort post)` (or equivalent) for non-empty delta; add harness case with pre-seeded dirty file + empty post-stub delta

### FINDING_39:
- **Reviewer(s)**: Codex-dyn-baseline-snapshot
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:74; skills/implement/scripts/step2-implement.sh:239-291,371-405
- **Concern**: Prelaunch porcelain baseline is not anchored to the shared external launch point. Scenario: Current dispatcher has one shared codex/cursor external path: the coder case only assigns variables, then step2-baseline.txt writes a HEAD SHA and run_launcher is shared. "Top of the cursor/codex launch path" can be implemented in a duplicated or wrong location, leaving M2/M7/M8/M10 dependent on hand-seeded files or covering only one tool.
- **Proposed resolution**: Define PRELAUNCH_PORCELAIN_FILE next to BASELINE_FILE and write it once in the shared external path after stale output cleanup and immediately before the first run_launcher call; do not write it per coder; add assertions that both codex and healthy cursor external paths create it.

### FINDING_40:
- **Reviewer(s)**: Codex-dyn-baseline-snapshot
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:74,102-115; skills/implement/scripts/step2-implement.sh:144-146,244-248,382-399; skills/implement/scripts/test-step2-dispatch.sh:577-583
- **Concern**: Recovery delta can include dispatcher tmpdir artifacts such as manifest.json. Scenario: step2 accepts any existing tmpdir and launchers write manifest/transcript/sidecar paths under it. If a scratch test or unusual run puts TMPDIR_ARG under REPO_ROOT, post-launch porcelain includes manifest.json or the prelaunch snapshot itself, so M2 empty-tree becomes non-empty and recovers for dispatcher artifacts rather than repo edits.
- **Proposed resolution**: Either reject TMPDIR_ARG inside REPO_ROOT or filter all TMPDIR_ARG-relative paths from the pre/post porcelain delta; make M2/M7/M8/M9/M10 fixtures explicitly keep tmpdirs outside scratch repos and add one regression proving manifest-only tmpdir artifacts do not satisfy the delta gate.

### FINDING_41:
- **Reviewer(s)**: Codex-dyn-baseline-snapshot
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:75,113-114; skills/implement/scripts/step2-implement.sh:574-580
- **Concern**: Plan/test expect submodule-modified but the existing safety gate emits submodule-dirty. Scenario: If recovery reuses the same guard as instructed, M9's REASON=submodule-modified assertion fails; if only recovery emits the new token, the complete path and recovery path no longer share the same guard contract.
- **Proposed resolution**: Use the existing submodule-dirty token in the plan/docs/tests, or explicitly rename the bail token everywhere including dispatcher, schema/docs, and harness expectations.

### FINDING_42:
- **Reviewer(s)**: Codex-dyn-baseline-snapshot
- **Severity**: important
- **Focus area**: security
- **Location**: <TMPDIR>/plan.txt:75,113-114; skills/implement/scripts/step2-implement.sh:574-580,604-632
- **Concern**: Factoring the current submodule guard is not enough for malformed-manifest recovery. Scenario: git submodule status catches gitlink, uninitialized, and conflict states, but not every dirty worktree edit inside an initialized submodule; with a malformed manifest, Step 7 path normalization cannot reject submodule manifest paths because validation failed, so a submodule working-tree delta can pass into claude_fallback.
- **Proposed resolution**: In run_post_implementer_safety_gates, compare post-launch porcelain paths against submodule roots and bail on any path equal to or under a submodule; make M9 include both a gitlink-change case and a dirty-file-inside-submodule case.

### OOS_1:
- **Description**: Plan-scope logic duplicated inline in SKILL.md. Scenario: write_scope_files is embedded Python in design scout only; recovery scope check will drift from design path extraction
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/scripts/scout-plan-archetypes-wrapper.sh:115-147
- **Phase**: design
