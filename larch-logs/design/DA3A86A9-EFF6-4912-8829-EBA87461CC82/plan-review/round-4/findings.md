### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/references/approval-gates.md:17-169
- **Concern**: Harness retargets approval-gates routing but file is not in the plan file list. Scenario: Negative line-scoped routing guard on surface (3) and updated contains pins at scripts/test-design-structure.sh:371-379,1568 will fail CI or leave normative Gate B/C prose telling orchestrators to skip the Step 3b completion boundary
- **Proposed resolution**: Add skills/design/references/approval-gates.md under Files to modify with the same boundary-qualified Step 3b→Step 4 wording used in SKILL.md

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:43-49 / skills/design/references/approval-gates.md:17-169
- **Concern**: Harness will scan approval-gates.md for bare Step 3b→Step 4 routing, but approval-gates.md is not listed under Files to modify/create. Scenario: Implementer updates SKILL.md and test pins only; line-scoped guard and updated contains() pins at scripts/test-design-structure.sh:371-379 and :1568 fail CI, or normative Gate B/C prose still tells the orchestrator to reach Step 4 after Step 3b without naming the completion boundary
- **Proposed resolution**: Add skills/design/references/approval-gates.md to Files to modify with the same boundary-qualified retarget applied to cap-breadcrumb, passive-summary auto-continue, zero-findings, Gate C When, and bypass routing lines (mirror the SKILL.md edits the plan already mandates)

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: plan.txt:38-39 / skills/design/scripts/run-step3-review.sh:167
- **Concern**: Plan adds a run-step3-review.sh routing assertion but omits that script from Files to modify. Scenario: New harness pin expecting boundary-qualified cap breadcrumb fails on the existing continuing to Step 3b, Step 4, then Gate C emit unless the script is updated or the assertion is dropped
- **Proposed resolution**: Add skills/design/scripts/run-step3-review.sh to Files to modify (retarget the cap breadcrumb) or state explicitly that script stdout is exempt from the routing guard

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/approval-gates.md:17,84,100,159,169
- **Concern**: Files-to-modify omits approval-gates.md even though the plan retargets Gate B/C routing there and the new line-scoped harness scans that file (plus positive contains pins at scripts/test-design-structure.sh:371-379,1568). Scenario: Implementer edits only SKILL.md and harness pins; approval-gates.md keeps bare Step 3b → Step 4 / Step 3b/4 chains, so Gate B/C auto-continue prose can still bypass the Step 3b completion boundary after Step 4 item 1 FINALIZE is removed; new routing guard and updated pins also fail CI until the reference is edited
- **Proposed resolution**: Add ### UPDATED: skills/design/references/approval-gates.md: retarget every Step 3b→Step 4 (and arrow/comma) routing line to name the Step 3b completion boundary before Step 4, matching the SKILL.md retarget pattern

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:1291-1295
- **Concern**: Plan inserts a new Step 3b completion bash fence instead of folding FINALIZE into the existing Step 3b entry timing fence that already runs on every 3b path. Scenario: Extra fence block, pause-check surface, and harness pinning for a region that already has an entry bash turn; FINALIZE only needs to run before Step 4 reads, not after diagram work
- **Proposed resolution**: Fold ACTION=FINALIZE (set +e + exit on failure) into the existing Step 3b entry fence; keep a single end-of-3b step-3b sentinel write (prose or minimal bash) and retarget exit paths to enter Step 3b (running FINALIZE at entry) before Step 4

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:9-65
- **Concern**: `skills/design/references/approval-gates.md` is absent from Files to modify despite mandatory retargeting and harness surface-3 routing scan. Scenario: The plan requires retargeting approval-gates Gate B/C routing prose (SKILL.md edit 3b) and adds a line-scoped guard over approval-gates as surface 3, but the file list omits `approval-gates.md`. Lines such as 84, 100, 159, and 169 still say Step 3b then Step 4 without the completion boundary; CI would fail the new guard and/or the orchestrator could follow stale normative Gate B/C prose and skip FINALIZE after Step 4 item 1 is removed
- **Proposed resolution**: Add `### UPDATED: skills/design/references/approval-gates.md` with the same boundary-qualified retarget applied to every Step 3b→Step 4 chain (cap breadcrumb, zero-findings, passive-summary, shared post-apply item 9, Gate C When); update harness positive pins at `scripts/test-design-structure.sh:371-379` and `:1568` to match

### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/approval-gates.md:17-169
- **Concern**: `approval-gates.md` is absent from **Files to modify/create** though Step 3 SKILL edit §3(b) and the new line-scoped routing guard both require boundary-qualified Step 3b→Step 4 prose there. Scenario: Implementer following only the file inventory updates `SKILL.md` and `test-design-structure.sh`; harness negative guard and pins at `scripts/test-design-structure.sh:371-379,1568` then fail on unchanged lines like `Step 3b → Step 4 → Step 4b` and `continuing to Step 3b, Step 4, then Gate C`
- **Proposed resolution**: Add `### UPDATED: skills/design/references/approval-gates.md` retargeting cap breadcrumb, passive-summary auto-continue, zero-findings chain, and Gate C When bypass lines to name the Step 3b completion boundary before Step 4

### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-routing-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/run-step3-review.sh:167
- **Concern**: Plan adds a harness routing assertion for this script but does not list retargeting its cap-reached emit string (Step 3b, Step 4, then Gate C).. Scenario: A new line-scoped guard will fail CI until the script is edited, or the emit stays as operator-facing text that implies a direct 3b→4 hop without the completion boundary.
- **Proposed resolution**: Add ### UPDATED: skills/design/scripts/run-step3-review.sh to retarget line 167 to name the Step 3b completion boundary before Step 4 (mirror approval-gates.md), or document an explicit harness exclusion if script text is intentionally out of band.

### FINDING_9:
- **Reviewer(s)**: Cursor-dyn-harness-sync
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh (planned §UPDATED)
- **Concern**: Entry-fence SIMPLE pins as described require unconditional sentinel/`step-2a`/`step-2a.5` substrings in the first Step 2a `bash` fence. Scenario: HARD runs keep that fence but must not write SIMPLE sentinels; naive `grep`/`awk` on the whole fence body fails CI or forces HARD to duplicate SIMPLE writes
- **Proposed resolution**: Scope the positive pin to a SIMPLE guard (e.g. `design_classification == SIMPLE` / `read-design-classification.sh` branch) or assert sentinels only in the `### SIMPLE branch` prose plus a negative `bash` check there, not bare literals in the shared entry fence

### FINDING_10:
- **Reviewer(s)**: Cursor-dyn-cross-doc-drift
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/references/approval-gates.md:17,100,169
- **Concern**: Plan item 3c and harness surface (3) retarget Gate B/C routing to require the Step 3b completion boundary, but approval-gates.md is not listed under Files to modify/create. Scenario: Multiple normative lines still say Step 3b then Step 4 (e.g. cap breadcrumb line 17, passive-summary line 100, Gate C When line 169) without naming the completion boundary; new line-scoped guards will fail or docs will contradict SKILL.md
- **Proposed resolution**: Add ### UPDATED: skills/design/references/approval-gates.md and rewrite those routing sequences to run the Step 3b completion boundary (FINALIZE + step-3b) before Step 4, matching SKILL.md

### OOS_1:
- **Description**: Plan conditionally adds a run-step3-review.sh routing assertion but does not list this script under Files to modify. Scenario: Cap breadcrumb emit still says continuing to Step 3b, Step 4, then Gate C without naming the completion boundary; a strict assertion would fail or force an out-of-scope script edit unrelated to orchestrator routing
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/run-step3-review.sh:167
- **Phase**: design
