### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:54-71
- **Concern**: Failure mode 1 mitigation claims before-pause ordering pins for all absorbed sentinels but the proposed assert_folded_sentinel_writes only maps step IDs to host fences (step-6 excepted). Scenario: A host fence can gain the literal write yet place it after design-pause-save.sh; resume would replay completed work while tests still pass
- **Proposed resolution**: Extend assert_folded_sentinel_writes to assert source-env → folded write → pause-check ordering for every absorbed prior-step sentinel host fence, mirroring the step-6 after-pause/before-cleanup special case

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:699-764
- **Concern**: HARD zero-sketch degraded branch must write step-2a and step-2a.5 before jumping to Step 2b but the plan does not pin a host Bash fence (item 6 removes the current Step 2a success-boundary write without naming the replacement site). Scenario: Implementer may drop the only pre-2b write site and rely on prose; pause/resume STEP resolution can treat zero-sketch HARD runs as still inside Step 2a until Step 2b prelude
- **Proposed resolution**: Pin item 6 to a concrete fence in the zero-sketches guard (new small Bash block before the jump to Step 2b) and add a matching assert_folded_sentinel_writes row for that degraded path

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1446-1449; scripts/test-design-structure.sh:1661-1678
- **Concern**: Step 5c publish fence remains a source-env fence without the canonical pause-check, and the current pause audit ignores indented fences. Scenario: A pause requested after Step 5b but before Step 5c publish would not be honored before design-publish.sh writes the plan, publishes logs, and may rename the issue
- **Proposed resolution**: Insert the design-pause-save.sh pause-check immediately after the source-env line in the indented Step 5c publish fence, before set +e; extend the new optional-whitespace fence extractor or pause audit to assert this fence is pause-bearing

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:598-604
- **Concern**: Step 1e is folded only into Step 2a even though post-plan Gate A can route directly to Step 3. Scenario: A pause requested after post-plan Gate A Ready for review reaches the Step 3 prelude with .completed/step-1e still absent, so design-pause-save records STEP=1e and resume replays Gate A instead of continuing to plan review
- **Proposed resolution**: Fold .completed/step-1e into the Step 3 entry fence as well, before its pause-check, or retain a boundary-local Step 1e write on the post-plan Ready for review path; add a pause/resume test for that route

### FINDING_5:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:562-572; skills/design/references/brainstorm.md:62-103
- **Concern**: Plan deletes the Step 1d.5 prelude while treating 1d.5 as pure discussion, but brainstorm can launch external Bash work and its reference fences do not carry the pause-save prelude.. Scenario: A pause requested before an enabled brainstorm run can be ignored while external brainstorm launches/collection proceed, widening pause latency beyond the stated discussion-only fold and weakening the pause/resume contract.
- **Proposed resolution**: Exclude Step 1d.5 from the deleted-prelude fold, or add an equivalent pause-save check before the first brainstorm launch/collection path; update the deleted-prelude test guard to allow the retained 1d.5 boundary.

### FINDING_6:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: .claude/rules/script-md-siblings.md:7-12
- **Concern**: Plan changes script behavior but omits required sibling contract docs for scripts/design-pause-load.sh, scripts/test-design-structure.sh, and skills/design/scripts/test-design-pause-resume.sh. Scenario: The repo rule requires updating each script sibling .md in the same PR as behavior changes; the proposed loader clear, folded-sentinel structure checks, and pause/resume regression would land with stale contracts
- **Proposed resolution**: Update the plan to include UPDATED entries for scripts/design-pause-load.md, scripts/test-design-structure.md, and skills/design/scripts/test-design-pause-resume.md documenting only the new folded discussion and pause-marker-clear contracts

### FINDING_7:
- **Reviewer(s)**: Cursor-dyn-test-assertion-mapping
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:55-65 (planned assert_folded_sentinel_writes)
- **Concern**: Folded-sentinel tests specify host mapping only, not before-pause line order. Scenario: Sentinel writes placed after design-pause-save.sh still pass mapping greps; resume replays completed discussion (failure mode 1)
- **Proposed resolution**: Require extracted host-fence bodies and awk line-order checks (pause line after each absorbed write) for every folded step except the documented step-6 exception pattern

### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-pause-load-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-pause-resume.sh:77-84
- **Concern**: Proposed regression can pass without exercising restored `.pause-requested`. Scenario: The plan only requires the marker be absent after `design-pause-load.sh`; a harness can seed a snapshot without `.pause-requested` (or omit a post-save snapshot assertion) and still pass, so the new `rm` in load never runs on the failure path
- **Proposed resolution**: Build the snapshot via `design-pause-save.sh` (stub publish copies the tmpdir while `.pause-requested` still exists: `scripts/design-log-publish.sh:294-302` excludes it only when `REASON != pause`; save removes it only after publish at `scripts/design-pause-save.sh:318`) and assert `[[ -f "$SNAPSHOT_ROOT/larch-logs/design/$RUN_ID/.pause-requested" ]]` before calling load

### OOS_1:
- **Description**: Plan changes design-pause-load.sh to rm restored .pause-requested but does not update the sibling contract doc. Scenario: Future readers of design-pause-load.md will miss the post-restore clear behavior and may reintroduce the immediate re-pause loop
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/design-pause-load.md:14-40
- **Phase**: design
