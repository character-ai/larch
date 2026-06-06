Normalized findings below: merged duplicates that share the same behavioral risk, kept separate items that need different fixes or touch different paths, and preserved `[OUT_OF_SCOPE]` entries as `OOS_N` blocks.

### FINDING_1: Step 3 re-entry (`.step3-reentry`) documentation inconsistent across SKILL.md and approval-gates.md
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Audit table and Step 1e prose still imply an unconditional `step-1e` write on every Step 3 entry, but round-2 implementation gates Step 3 sentinel work behind `.step3-reentry`. `approval-gates.md` Gate A re-entry (“Ready for review”) omits `.step3-reentry` and Step 3 sentinel hygiene that `SKILL.md` requires. After a backward loop clears `step-1e` and Step 2 markers, an orchestrator following `approval-gates.md` alone can enter Step 3 without the re-entry block; pause during review can snapshot `STEP=1e` and resume replays Gate A instead of Step 3. Maintainers reading lines 92/644 may add an unconditional `step-1e` write or miss Gate A / Gate C marker requirements; first-time Step 3 incorrectly assumes Step 3 always repairs `step-1e`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Step 2a entry batch-writes discussion sentinels before pause-check
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Step 2a entry batch-writes discussion completion sentinels before the pause-check and before step-body success is proven. An orchestrator reaching Step 2a before `1d.7`/`outline` is truly done can freeze incomplete discussion as complete in pause snapshots. A `/pause` during folded pure-LLM discussion can snapshot markers for completed steps `1c`–`1e` while discussion is partial; resume skips replay and proceeds to sketches/planning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt: Address the concern above.

### FINDING_3: Zero-sketch degraded fence not branch-guarded in shell
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The zero-sketch degraded fence is HARD-guarded only in prose, not branch-guarded in shell. A misfired fence on normal HARD sketch runs can mark `step-2a`/`2a.5` complete before sketches/synthesis.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_4: Step 3 bypass-restore comment mislabels `.step3-reentry` scope
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: The Step 3 bypass-restore comment says backward-loop-only, but the code runs for all `.step3-reentry` paths. This misleads maintainers; no immediate runtime bug if `SKILL.md` is followed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_5: `jq` absence forces false `brainstorm_requested`, breaking `step-1d.5` repair
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `jq` absence makes `brainstorm_requested` false, forcing `step-1d.5` repair at Step 2a. On a `jq`-less host with `brainstorm_requested` true in `run-params.json`, `step-1d.5` can be marked complete without the brainstorm boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_6: `assert_bash_fences_have_pause_check` scan narrowed to Step 0c only
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `assert_bash_fences_have_pause_check` now scans only the Step 0c fence instead of all Bash fences from Step 1c onward. A later edit could drop pause-check from a non-folded fence (e.g. sketch collection or Step 3 preview) without failing Check 21.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_7: Step 1d short-circuit defers discussion sentinels to Step 2a entry
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Step 1d short-circuit can skip the Step 1d.5 section when brainstorm is off, deferring discussion sentinels to Step 2a entry. A `/pause` during Step 1d.7 or 1e leaves only `step-0c` in the snapshot; `design-pause-save.sh` resumes at `STEP=1c` and replays completed discussion/outline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: Tradeoff prose overclaims folded-sentinel pause replay prevention
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Tradeoff text at `skills/design/SKILL.md:82` implies folded sentinels always prevent discussion replay on pause. Mid-discussion pause before the next host fence can still resume at the first missing registry step and replay upstream LLM work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: Backward-loop pause-resume test omits `.step3-reentry` fixture semantics
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The direct-review backward-loop test replays Step 3 restore without `.step3-reentry`. Orchestrator regressions that omit the marker write from Gate A or Gate C would pass the harness while breaking first-time vs re-entry behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: `assert_backward_reentry_guards` does not pin sentinel writes inside `.step3-reentry` block
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `assert_backward_reentry_guards` checks that `.step3-reentry` exists but not that `step-1e` and bypass-package writes are inside that conditional. Moving those writes outside the `if` block would still pass Check 21 while changing first-time Step 3 sentinel behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_11: Phase 7 plan-to-commit checklist omits `design-pause-load.sh`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Phase 7 plan lists `scripts/design-pause-load.sh`; Phase 7 commit only updated `.md`; the `.sh` change is in #3529. Plan-to-commit file checklist for Phase 7 is incomplete even though branch behavior satisfies acceptance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### OOS_1: [OUT_OF_SCOPE] `design-pause-load.sh` listed in plan but unchanged on branch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Plan listed script change; branch only updates docs; clear behavior pre-existed. No runtime regression from this diff. None required if docs suffice.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Branch diff includes non–Phase-7 collateral changes
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Non–Phase-7 files changed on branch from review/merged PRs (`SECURITY.md`, `design-log-publish.*`, `larch-log.*`, etc.). Reviewers auditing Phase-7-only scope must filter unrelated diffs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
