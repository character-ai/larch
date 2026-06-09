### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/emit-design-plan-preview.sh:61-84
- **Concern**: Plan requires using fresh plan-summary.md but never defines freshness. Scenario: After Gate B or inline fallback rewrites plan.txt, Step 3 and Gate C can still print a stale drafter summary for large plans
- **Proposed resolution**: Specify and implement one rule in emit-design-plan-preview.sh and its .md sibling (e.g. use plan-summary.md only when mtime is >= plan.txt mtime, or record a PLAN_SUMMARY_GENERATED_AT KV at drafter write); add harness cases for stale vs fresh

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/emit-design-plan-preview.sh:1-4
- **Concern**: Generated-summary preview update is targeted at missing root path scripts/emit-design-plan-preview.sh. Scenario: Step 3 and Gate C invoke skills/design/scripts/emit-design-plan-preview.sh, so implementing the planned root scripts/ path would leave the real preview renderer unchanged and large drafter plans would still show the synthetic outline instead of fresh plan-summary.md
- **Proposed resolution**: Retarget the plan entries and harness/docs to skills/design/scripts/emit-design-plan-preview.sh, skills/design/scripts/emit-design-plan-preview.md, and skills/design/scripts/test-emit-design-plan-preview.sh

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/emit-design-plan-preview.sh:61-84
- **Concern**: Generated-summary freshness rule is not pinned in the plan. Scenario: After drafter or inline fallback rewrites plan.txt (or Gate B revises it), a stale plan-summary.md can still be emitted at Step 3/Gate C if implementers treat existence/non-empty as sufficient; voters/operators see the wrong plan body
- **Proposed resolution**: Define freshness mechanically in plan + emit-design-plan-preview.md (e.g. use plan-summary.md only when mtime is >= plan.txt mtime; otherwise synthetic outline) and add harness cases for stale-summary-after-rewrite

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/emit-design-plan-preview.sh:1-3
- **Concern**: Plan updates the wrong preview script path. Scenario: The plan names scripts/emit-design-plan-preview.sh and scripts/emit-design-plan-preview.md, but the Step 3/Gate C renderer lives under skills/design/scripts; implementing literally can leave generated plan-summary.md unused in the real preview flow.
- **Proposed resolution**: Change the plan targets to skills/design/scripts/emit-design-plan-preview.sh, skills/design/scripts/emit-design-plan-preview.md, and skills/design/scripts/test-emit-design-plan-preview.sh.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:283-300
- **Concern**: UPDATED paths name scripts/emit-design-plan-preview.sh but the live preview helper is skills/design/scripts/emit-design-plan-preview.sh (harness skills/design/scripts/test-emit-design-plan-preview.sh). Scenario: An implementer editing scripts/emit-design-plan-preview.* misses the real file; Step 3/Gate C never prefer generated plan-summary.md
- **Proposed resolution**: Retarget all preview/harness bullets to skills/design/scripts/emit-design-plan-preview.{sh,md} and skills/design/scripts/test-emit-design-plan-preview.{sh,md}

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/emit-design-plan-preview.sh:1-132
- **Concern**: Plan targets nonexistent root preview files instead of the shipped design preview renderer. Scenario: The plan's UPDATED sections name scripts/emit-design-plan-preview.sh and scripts/emit-design-plan-preview.md, but Step 3 and Gate C call skills/design/scripts/emit-design-plan-preview.sh; following the plan would leave generated plan-summary.md unused in the actual preview path, so the required summary/full presentation for large drafted plans would be missing before voting/Gate C
- **Proposed resolution**: Retarget those UPDATED sections and harness/docs references to skills/design/scripts/emit-design-plan-preview.sh, skills/design/scripts/emit-design-plan-preview.md, and skills/design/scripts/test-emit-design-plan-preview.sh; avoid creating root-level preview files

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:283-300
- **Concern**: Wrong path for emit-design-plan-preview updates. Scenario: Lists scripts/emit-design-plan-preview.sh but the script lives at skills/design/scripts/emit-design-plan-preview.sh; implementer may edit a nonexistent path and miss the real preview harness skills/design/scripts/test-emit-design-plan-preview.sh
- **Proposed resolution**: Retarget all emit-design-plan-preview and preview-harness bullets to skills/design/scripts/emit-design-plan-preview.sh, skills/design/scripts/emit-design-plan-preview.md, and skills/design/scripts/test-emit-design-plan-preview.sh

### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:283-294; skills/design/scripts/emit-design-plan-preview.sh:1
- **Concern**: Plan targets nonexistent preview files under scripts/. Scenario: The Step 3 and Gate C preview code actually lives under skills/design/scripts, so following the plan literally would leave the real preview path unchanged and generated plan-summary.md would not be used outside Step 2b
- **Proposed resolution**: Retarget these plan entries and harness updates to skills/design/scripts/emit-design-plan-preview.sh, skills/design/scripts/emit-design-plan-preview.md, and skills/design/scripts/test-emit-design-plan-preview.sh/.md.

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:450-497
- **Concern**: Plan has Testing strategy but no ## Acceptance section with checkable completion criteria. Scenario: The binding scope requires a side-effect-free `claude --model claude-fable-5` probe before relying on Fable, plus C1–C3 deliverables (drafter delegation with inline fallback, `LARCH_VOTER_MODEL` default, Sonnet fallback-reviewer pins, docs). `/implement` preflight plan-adequacy audit requires ≥1 verifiable `## Acceptance` criterion; without it completion and the mandated Fable probe are not operator-checkable at handoff
- **Proposed resolution**: Add `## Acceptance` listing concrete checks: Step 2b produces `plan.txt` via drafter or eligible inline fallback; Voter 1 resolves `LARCH_VOTER_MODEL` default `claude-fable-5` through `launch-claude-review.sh` for `/design` and `/review`; fallback reviewer dispatches use `claude-sonnet-4-6` with no `claude-opus-4-7` pins; pre-merge stdin probe exit 0 for `claude --model claude-fable-5` (per verify-external-tool-invocations); `make test-launch-claude-drafter` and expanded `test-launch-claude-review` pass; `bash scripts/relevant-checks.sh` passes

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/emit-design-plan-preview.sh:61-80
- **Concern**: `plan-summary.md` freshness rule is named but not specified. Scenario: Plan requires preferring fresh `plan-summary.md` at Step 3/Gate C and says stale summaries fall back to the synthetic outline, but never defines freshness (e.g. mtime vs `plan.txt`, content hash, or clearing summary on inline fallback). After drafter failure → inline fallback regenerates `plan.txt` while leaving an older `plan-summary.md`, preview can show wrong large-plan text at Step 3 or Gate C
- **Proposed resolution**: Define and document freshness in the `emit-design-plan-preview.sh` update (e.g. use summary only when `plan-summary.md` is non-empty and `plan-summary.md` mtime ≥ `plan.txt` mtime, or delete `plan-summary.md` on any inline fallback that rewrites `plan.txt`); add harness cases for stale/missing summary after fallback

### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/launch-claude-drafter.sh (new); SECURITY.md:157
- **Concern**: Drafter launcher plan omits the existing design-tmpdir allowlist and does not constrain the repo-root read grant. Scenario: The new launcher accepts --design-tmpdir and --repo-root, writes plan/status files under the former, and grants Claude repo read tools via the latter, but the plan only requires non-symlink canonicalization; a misconfigured or malicious invocation could write outside the allowed design session roots or expose an arbitrary directory through --add-dir
- **Proposed resolution**: Add launch-claude-drafter.sh requirements to source scripts/lib-design-tmpdir.sh and run larch_design_tmpdir_validate before any write/read under --design-tmpdir; also constrain --repo-root to the actual current repo/worktree root used by /design, and add harness cases for rejected disallowed design tmpdirs and broad/non-repo read roots

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-cli-allowlist-contract
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-launch-claude-subprocess.sh:282-287
- **Concern**: Planned drafter harness requires CMD_JSON to match probe-proven native argv (plan lines 49-50, 129, 492-496) but defines no committed single source of truth and mirrors the subprocess harness grep-substring style that never exercises the real claude CLI. Scenario: Implementer can land test-launch-claude-drafter.sh with allowedTools/plan substring asserts against a PATH stub; CI stays green while production argv uses an unprobed multi-tool shape the installed claude rejects or mis-parses (silent allowlist ignore)
- **Proposed resolution**: Add one committed fixture (e.g. scripts/fixtures/claude-drafter-native-argv.json) populated by the mandatory pre-merge probe; launch-claude-drafter.sh must assemble CMD_JSON from it; test-launch-claude-drafter.sh must jq-compare the written CMD_JSON= line to the same fixture byte-for-byte (not grep fragments)

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-fallback-reentry-invariant
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:276-281
- **Concern**: Step 11 says postplan may re-enter inline fallback and rerun the terminal postplan fence exactly once but specifies no sentinel file state variable or bash guard. Scenario: The orchestrator can invoke inline fallback plus postplan again on every failure with no cap; a second inline-fallback postplan failure has no defined terminal branch distinct from another re-entry
- **Proposed resolution**: Add a mechanical once constraint in the Step 2b SKILL fence e.g. touch/check $DESIGN_TMPDIR/.step2b-postplan-inline-retry-done before inline fallback from postplan failure and refuse a second retry routing to existing rc=10 Gate A or abort

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-fallback-reentry-invariant
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1030-1088
- **Concern**: Step 2b postplan fallback says to rerun the terminal fence once, but the proposed SKILL.md structure does not add a retry sentinel, plan-source reset, or guard around the existing postplan fence.. Scenario: If a drafter plan reaches the postplan fence and fails validation, the fallback inline plan can re-enter the same failure branch without a concrete state check, allowing a third postplan/fallback cycle instead of falling through to the existing rc handling.
- **Proposed resolution**: Add a minimal shell guard such as _drafter_postplan_fallback_used=false before the first fence, set it true and set plan source to inline before invoking inline fallback, and only permit the drafter-postplan fallback branch when the guard is still false.

### FINDING_15:
- **Reviewer(s)**: Cursor-dyn-voter-caller-surface
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:283-300; staged-context/scope-files.txt:10-12
- **Concern**: [SCOPE-REDUCTION] Plan and scope-files target scripts/emit-design-plan-preview.sh and bare emit-design-plan-preview.sh but the canonical script is skills/design/scripts/emit-design-plan-preview.sh. Scenario: Implementer edits or creates wrong paths; preview changes for fresh plan-summary.md never land on the script SKILL.md and run-step3-review.sh already call
- **Proposed resolution**: Rename plan entries and scope-files lines to skills/design/scripts/emit-design-plan-preview.sh .md and skills/design/scripts/test-emit-design-plan-preview.sh; remove stale scripts/ and bare duplicates

### FINDING_16:
- **Reviewer(s)**: Codex-dyn-voter-caller-surface
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:283-300; skills/design/scripts/emit-design-plan-preview.sh:1-17; skills/design/scripts/run-step3-review.sh:116-133; skills/design/SKILL.md:1474-1482
- **Concern**: Plan scopes generated-summary preview updates to scripts/emit-design-plan-preview.sh and an unqualified harness, but the live preview renderer and harness are under skills/design/scripts. Scenario: Implementer may create or edit a non-called scripts/emit-design-plan-preview.sh while Step 3 and Gate C keep invoking skills/design/scripts/emit-design-plan-preview.sh, so drafter plan-summary.md is not used for the required large-plan presentation
- **Proposed resolution**: Retarget the plan entries at lines 283-300 to skills/design/scripts/emit-design-plan-preview.sh, skills/design/scripts/emit-design-plan-preview.md, and skills/design/scripts/test-emit-design-plan-preview.sh, and keep the Makefile target wired to that harness.

### OOS_1:
- **Description**: C2 relies on dispatch voters passing --role voter without --model but plan verifies only test-launch-claude-review.sh not dispatch call sites. Scenario: A future edit could add --model to a dispatcher and silently bypass LARCH_VOTER_MODEL without a failing test
- **Reviewer**: Cursor-dyn-voter-caller-surface
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/dispatch-plan-voters.sh:97-105; scripts/dispatch-code-voters.sh:120-127; plan.txt:483-486
- **Phase**: design
