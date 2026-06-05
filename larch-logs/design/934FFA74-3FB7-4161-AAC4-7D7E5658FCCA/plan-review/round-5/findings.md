### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:584-604
- **Concern**: Plan item 11a clears only step-1e..step-2b on Gate B(c)/Gate C(b) discussion re-entry but deletes the Step 1e prelude fence; stale step-3..step-4b from a prior Gate C pass remain until Step 3 entry. Scenario: Pause during Step 1e after Gate C(b) Discuss further can leave step-4b set so design-pause-save.sh resolves STEP to 5b (scripts/design-pause-save.sh:170-188) while the operator is still in discussion
- **Proposed resolution**: Extend 11a rerun span through step-4b; add a concrete Gate B/C re-entry Bash fence at Step 1e (source-env → rm stale step-1e..step-4b → pause-check) and a pause-resume fixture that seeds step-4b then pauses at Step 1e before Step 3 entry

### FINDING_2:
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1262-1295
- **Concern**: Architectural Step 3b cleanup only clears architecture-diagram.skipped, not stale architecture-diagram.md on generation failure. Scenario: The plan says stale diagram artifacts are removed on each Gate C pass, but the detailed architectural-path edit leaves a prior architecture-diagram.md in place if the next architectural diagram generation fails or sanitizer rejects; design-publish.sh will then upsert the stale diagram
- **Proposed resolution**: Add branch-entry cleanup for architectural paths: rm -f "$DESIGN_TMPDIR/architecture-diagram.md" "$DESIGN_TMPDIR/architecture-diagram.candidate.md" "$DESIGN_TMPDIR/architecture-diagram.skipped" before fresh generation, or at minimum delete architecture-diagram.md on generation/sanitizer failure before Step 3b FINALIZE.

### FINDING_3:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:598-604,1014-1028
- **Concern**: Backward discussion re-entry clears step-2a through step-2b markers but direct Step 1e to Step 3 does not restore them. Scenario: Gate C Discuss further clears step-1e through step-2b, Gate A Ready for review jumps straight to Step 3, then a pause after review sees missing step-2a in registry order and resumes by replaying sketches/plan instead of Gate B or Step 3.5
- **Proposed resolution**: Narrow the backward re-entry clear to step-1e and post-review sentinels, or have the Step 3 direct-review entry restore step-2a step-2a.5 step-2b and step-2b.5 before pause-check

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1258-1295; skills/design/scripts/design-publish.sh:395-408
- **Concern**: Architectural reruns only clear architecture-diagram.skipped, leaving stale promoted diagrams on failure. Scenario: A prior Gate C pass writes architecture-diagram.md, a later architectural rerun fails generation or sanitizer, and design-publish.sh treats the stale non-empty file as current and republishes it
- **Proposed resolution**: At architectural Step 3b entry remove stale architecture-diagram.md and candidate as well as skipped; if failure should clear the tracking-issue Architecture section, also emit the clear sentinel or another explicit clear trigger on failure

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:584-604
- **Concern**: Plan deletes the Step 1e prelude fence (item 6) but item 11a requires stale-sentinel clears before a Step 1e entry pause-check on Gate B(c)/Gate C(b) re-entry; after the fold Step 1e has no Bash host until Gate A success prose. Scenario: Gate C Discuss further or Gate B switch to discussion re-enters Step 1e with step-3 through step-4b still set; a pause during discussion has no entry fence to clear them, so design-pause-save.sh registry walk can record STEP at 5b/5c instead of 1e and resume jumps past the discussion loop
- **Proposed resolution**: Add a minimal Gate B(c)/Gate C(b) re-entry Bash fence at Step 1e: source-env then rm stale step-1e through step-4b (not only through step-2b) then pause-check; keep the Phase 7 fold for first-time 1e skip paths

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md:123-124
- **Concern**: Backward discussion-loop cleanup is not anchored at the actual Gate B/C exit branches. Scenario: The plan deletes the Step 1e prelude but relies on stale-sentinel clears before a later pause-check; if Gate C Discuss further enters Gate A with stale step-3..step-4b markers and a pause fires during the discussion postplan fence, resume can jump to finalize and skip the required fresh review
- **Proposed resolution**: Add one small transition fence on Gate B Switch-to-discussion and Gate C Discuss further, or retain a Step 1e re-entry-only fence, that clears the rerun-span sentinels before its pause-check

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1262-1295
- **Concern**: Architectural retry path does not clear stale promoted diagrams before generation failure handling. Scenario: After a prior Step 3b pass generated architecture-diagram.md, a later Gate C loop can take the architectural path and fail generation or sanitizer; because the plan only clears architecture-diagram.skipped on architectural entry, the stale architecture-diagram.md can survive and be published as current
- **Proposed resolution**: At architectural path entry, remove stale architecture-diagram.md and architecture-diagram.candidate.md along with architecture-diagram.skipped before generating; keep the non-architectural skip cleanup as planned and add the structure assertion for this case

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:600
- **Concern**: Backward re-entry clears omit the Gate A plan-rewrite bash path. Scenario: Pause during Gate B(c)/Gate C(b) discussion that revises plan.txt runs gate-b-dedup / design-postplan-emit (SKILL.md:600) before Step 3 entry; stale step-3..step-4b from the prior review cycle remain, so design-pause-save.sh registry walk can set STEP to 5b/5c while the operator is still in Gate A rewrite
- **Proposed resolution**: Extend plan items 11/11a and SKILL.md Step 1e optional trailer guard: on the first rewrite bash fence (gate-b-dedup --snapshot-trailers), after source-env and before pause-check, rm -f stale $DESIGN_TMPDIR/.completed/step-3 through step-4b; add a pause-resume fixture that pauses mid-rewrite and asserts STEP is 3 (or 1e), not 5b+

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:35-40
- **Concern**: Step 2a entry SKILL edit omits SIMPLE marker ordering before pause-check. Scenario: Item 7 inserts discussion sentinel writes before pause-check but says only to preserve the SIMPLE guarded block in place; scripts/test-design-structure.sh:74-75 requires step-2a and step-2a.5 write lines before pause-check in that block
- **Proposed resolution**: A pause at Step 2a entry can exec design-pause-save.sh before SIMPLE markers are written, leaving an incomplete resume package Spell out in item 7 that the SIMPLE guarded block (artifacts plus step-2a and step-2a.5 writes) moves to after source-env and before pause-check, with timing mark after pause-check

### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:1129-1148,1353-1378,1548-1565
- **Concern**: Plan folds non-feature sentinel boundaries beyond the pure-LLM Phase 7 scope. Scenario: The feature acceptance targets pure-LLM steps 1c, 1d, 1d.5, 1d.7, 1e, and 2a.4, but the plan also moves Step 3, Step 3.5, Step 4b, Step 5d, and Step 6 markers and adds related stale-sentinel clearing and harness churn. That expands the pause/resume state-machine risk without being required to remove the named near-empty turns.
- **Proposed resolution**: Limit this PR to the named discussion/2a.4 folds plus required pause-load and Step 5c pause-check fixes; leave later sentinel hosts unchanged or split them into a separate follow-up.

### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-sentinel-state-machine
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-pause-save.sh:170-177
- **Concern**: Backward discussion re-entry to Step 1e has no Bash host for sentinel clears after folded preludes remove the Step 1e fence. Scenario: Plan item 11a requires clearing step-1e…step-2b before Step 1e pause-check, but items 6/33 delete the Step 1e standalone prelude. Gate B(c) / Gate C(b) exit to Step 1e is LLM-only while step-3 already exists from the Step 3.5 prelude fold (plan item 13). pause-save then emits STEP=3.5 (step-3 present, step-3.5 absent), so resume@3.5 replays Gate B instead of Gate A discussion
- **Proposed resolution**: Add a minimal re-entry-only Bash fence at Gate B(c)/Gate C(b)→Step 1e (and/or the first discussion-round2 postplan fence) that runs source-env → rm stale step-3…step-4b (and step-1e…step-2b.5) → pause-check before any Step 1e prose; do not rely on a deleted Step 1e prelude

### FINDING_12:
- **Reviewer(s)**: Codex-dyn-sentinel-state-machine
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:600-604,1014-1018
- **Concern**: Gate A discussion re-entry clears too far upstream. Scenario: The plan says Gate B/C discussion re-entry should clear step-1e through step-2b before pause-check, but the Ready for review route proceeds directly from Gate A to Step 3 and the proposed Step 3 repair only re-writes step-1e. A pause at Step 3 would see missing step-2b and resume at Step 2b instead of reviewing the revised current plan.
- **Proposed resolution**: Do not clear step-2a/step-2a.5/step-2b on Gate A discussion re-entry. Clear only step-1e before Gate A and let Step 3 clear downstream review/Gate-C markers, or ensure the Gate A post-rewrite fence re-writes step-2b before any Step 3 pause-check.

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-sentinel-state-machine
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:439,528-532; scripts/design-pause-save.sh:167-186
- **Concern**: Already-planned Q&A-only branch writes a non-contiguous sentinel. Scenario: The proposed terminal write of only .completed/step-1d.5 cannot make pause-save resume past brainstorm on the already-planned Q&A-only branch, because that branch exits before Step 0c and the registry picks the first missing step in order. With step-0c or step-1c still absent, a saved pause resumes before 1d.5 and can replay the brainstorm path.
- **Proposed resolution**: Either drop the new Q&A-only step-1d.5 terminal write as unnecessary, or make the branch write a contiguous registry prefix through step-1d.5 before any pause-save-capable terminal boundary.

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-sentinel-state-machine
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1260-1295; skills/design/scripts/design-publish.sh:395-408
- **Concern**: Architectural retry does not clear a stale prior diagram. Scenario: The plan removes stale diagram files only on the non-architectural skip branch and clears only architecture-diagram.skipped on architectural entry. If a prior Gate C pass produced architecture-diagram.md and a later architectural retry fails generation or sanitizer, design-publish.sh will still upsert the old non-empty architecture-diagram.md.
- **Proposed resolution**: On architectural Step 3b entry, remove stale architecture-diagram.md and architecture-diagram.candidate.md before generation, then promote only the current candidate on success.

### FINDING_15:
- **Reviewer(s)**: Cursor-dyn-harness-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md (proposed §6 + §11a)
- **Concern**: Gate B(c)/Gate C(b) re-entry to Step 1e requires stale step-1e…step-2b clears before a pause-check, but Step 1e loses its standalone prelude fence. Scenario: After Discuss-further → Step 1e, stale step-2a/2b/3 markers from the prior pass can remain while Step 1e is pure LLM; pause-save resumes at a later registry step instead of Gate A discussion
- **Proposed resolution**: Add a concrete bash host on the Step 1e re-entry path (minimal source-env → rm stale step-1e…step-2b → pause-check) or route Gate B(c)/Gate C(b) through an existing prelude that performs the clears before any Step 1e work; pin that host in assert_folded_sentinel_writes / backward re-entry guards

### FINDING_16:
- **Reviewer(s)**: Cursor-dyn-harness-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh (proposed §3)
- **Concern**: assert_folded_sentinel_writes host map lists conditional/branched writes but not how to prove the branch in extracted shell. Scenario: Unconditional : > step-1d.5 in Step 2a entry, unconditional step-2a in Step 2a.5 prelude on SIMPLE runs, or step-5c before PLAN_WRITE_OK parse would still satisfy literal-line grep and weaken the folded contract
- **Proposed resolution**: Extend assert_folded_sentinel_writes to require branch guards (brainstorm_requested false via run-params.json/jq, HARD-only classification guard on 2a.5 prelude, [[ PLAN_WRITE_OK=true ]] block with step-5c write after the parse loop) using line-order checks inside the extracted fence body

### FINDING_17:
- **Reviewer(s)**: Cursor-dyn-harness-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh (proposed §2–3; skills/design/SKILL.md proposed §8)
- **Concern**: Zero-sketch degraded branch fence has no named extraction anchor beyond “first fence after <!-- step:2a”. Scenario: extract_first_bash_fence_after only returns the Step 2a entry fence, so step-2a/step-2a.5 writes in the degraded branch fence and their source-env→writes→pause-check ordering would not be asserted
- **Proposed resolution**: Add extract_bash_fence_after with a dedicated marker (e.g. proximity to “ran 0 sketches (degraded)” / zero-sketch jump prose) and register that fence separately in assert_folded_sentinel_writes

### FINDING_18:
- **Reviewer(s)**: Cursor-dyn-harness-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:961-962
- **Concern**: Existing Check 15b section grep for architecture-diagram.skipped is not retired when branch-local assertions are added. Scenario: Prose at skills/design/SKILL.md:1260 can satisfy line 961 without a branch-local bash fence that rm -f stale diagram files before writing the skip sentinel, so the planned Step 3b branch contract can ship untested
- **Proposed resolution**: Replace lines 961–962 with branch-scoped fence extraction: skip-path fence must contain rm -f architecture-diagram.md and .candidate.md before : > architecture-diagram.skipped; architectural entry must rm -f .skipped before generation; FINALIZE boundary must not write .skipped

### FINDING_19:
- **Reviewer(s)**: Cursor-dyn-harness-fidelity
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/test-design-pause-resume.sh (proposed §9)
- **Concern**: Backward-loop fixtures only assert resumed STEP routing, not that stale .completed markers were removed before the re-entry pause-check. Scenario: Structure grep could pass with rm prose in the wrong fence while runtime pause still saves stale step-3…step-4b (or step-1e…step-2b) and resumes at Gate C or Step 2b
- **Proposed resolution**: Seed stale markers, execute the documented re-entry prelude shell (or a copied excerpt) before pause-save, assert the stale files are absent on disk, then assert LOAD STEP; mirror Gate B(c)→Step 1e if a clear host is added

### FINDING_20:
- **Reviewer(s)**: Codex-dyn-harness-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:609-640; scripts/test-design-structure.sh:99-143
- **Concern**: Plan makes the harness assert SIMPLE step-2a and step-2a.5 writes before pause-check, but the SKILL.md edit instructions only insert folded discussion writes before pause-check and say to preserve the existing SIMPLE guarded block, which is currently after pause-check. Scenario: The implementer can follow the SKILL.md plan literally and leave SIMPLE marker writes after pause-check, while the new ordering assertion expects the opposite; or they can satisfy the test by moving code in a way the plan never explicitly specifies
- **Proposed resolution**: Make the Step 2a entry ordering explicit: source env, folded discussion writes, read classification plus SIMPLE guarded artifact and step-2a/step-2a.5 writes if intended, then pause-check; or relax the planned assertion if SIMPLE markers need not precede pause-check

### FINDING_21:
- **Reviewer(s)**: Cursor-dyn-contract-drift
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:32-34,45-46
- **Concern**: Step 11a requires clearing stale step-1e…step-2b sentinels before Step 1e pause-check, but Step 6 deletes the Step 1e prelude fence. Scenario: Gate B(c)/Gate C(b) → Step 1e can run design-postplan-emit.sh (SKILL.md Step 1e optional trailer guard) before Step 3 entry; stale step-3…step-4b markers remain, so design-pause-save.sh registry scan can emit STEP≥5 while the operator is still in discussion (scripts/design-pause-save.sh:170-188)
- **Proposed resolution**: Add a re-entry-only Bash host (clears step-1e…step-4b, then pause-check) at Gate B(c)/Gate C(b) → Step 1e and/or prepend the same clears to the Gate A postplan-emit fence before its pause-check; do not rely on Step 3 entry alone

### FINDING_22:
- **Reviewer(s)**: Codex-dyn-contract-drift
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1270-1295; skills/design/scripts/design-publish.sh:395-408
- **Concern**: Proposed architectural-path cleanup clears architecture-diagram.skipped but not stale architecture-diagram.md. Scenario: After a prior architectural Gate C pass writes architecture-diagram.md, a later architectural pass can fail generation or sanitizer validation; design-publish.sh treats the stale non-empty architecture-diagram.md as authoritative and republishes it
- **Proposed resolution**: Add branch-local cleanup for architectural paths: remove stale architecture-diagram.md and architecture-diagram.candidate.md before generation, or remove them on rejection/failure before FINALIZE; extend the Step 3b structure assertion to cover this

### FINDING_23:
- **Reviewer(s)**: Codex-dyn-contract-drift
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/design-pause-load.md:5-6,39-45,58-59; scripts/design-pause-load.sh:292-306; skills/design/scripts/test-design-pause-resume.sh:186-193
- **Concern**: Plan adds restored .pause-requested clearing but leaves the sibling contract saying the issue pause marker is deleted on load. Scenario: The script restores files and emits LOAD_OK without deleting the issue marker, and the harness expects the marker to remain; the updated docs would still describe a conflicting load contract
- **Proposed resolution**: Update design-pause-load.md to say load removes only the restored live $DESIGN_TMPDIR/.pause-requested marker; the issue-body larch:design-pause marker remains until existing terminal cleanup/marker handling

### FINDING_24:
- **Reviewer(s)**: Codex-dyn-contract-drift
- **Severity**: latent
- **Focus area**: correctness
- **Location**: docs/configuration-and-permissions.md:268-270; skills/design/SKILL.md:1022-1027
- **Concern**: The plan says to leave the Step 3 chat-order clause unchanged, but that clause names an obsolete preview helper. Scenario: SKILL.md Step 3 invokes emit-design-plan-preview.sh --variant step3, while the config note still says run-step3-review.sh --preview-only; updating the same chat-order sentence for Gate C would preserve a false contract
- **Proposed resolution**: While editing the note, change the Step 3 helper name to emit-design-plan-preview.sh --variant step3; keep the rest of the Step 3 ordering unchanged
