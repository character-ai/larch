### FINDING_1: Define plan-summary freshness before previewing it
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan requires Step 3/Gate C to prefer a fresh `plan-summary.md`, but does not mechanically define freshness. If `plan.txt` is rewritten after summary generation, previews can show stale large-plan content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify and implement one rule in emit-design-plan-preview.sh and its .md sibling (e.g. use plan-summary.md only when mtime is >= plan.txt mtime, or record a PLAN_SUMMARY_GENERATED_AT KV at drafter write); add harness cases for stale vs fresh
  - From Cursor-Edge: Define freshness mechanically in plan + emit-design-plan-preview.md (e.g. use plan-summary.md only when mtime is >= plan.txt mtime; otherwise synthetic outline) and add harness cases for stale-summary-after-rewrite
  - From Cursor-Requirements: Define and document freshness in the `emit-design-plan-preview.sh` update (e.g. use summary only when `plan-summary.md` is non-empty and `plan-summary.md` mtime ≥ `plan.txt` mtime, or delete `plan-summary.md` on any inline fallback that rewrites `plan.txt`); add harness cases for stale/missing summary after fallback


### FINDING_2: Retarget preview updates to the live skills/design script path
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Codex-dyn-voter-caller-surface
- **Severity**: important
- **Concern**: Multiple plan entries target root-level `scripts/emit-design-plan-preview.*`, but the live Step 3/Gate C preview renderer and harness are under `skills/design/scripts`. Implementing the plan literally could leave the real preview flow unchanged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Retarget the plan entries and harness/docs to skills/design/scripts/emit-design-plan-preview.sh, skills/design/scripts/emit-design-plan-preview.md, and skills/design/scripts/test-emit-design-plan-preview.sh
  - From Codex-Edge: Change the plan targets to skills/design/scripts/emit-design-plan-preview.sh, skills/design/scripts/emit-design-plan-preview.md, and skills/design/scripts/test-emit-design-plan-preview.sh.
  - From Cursor-Innovation: Retarget all preview/harness bullets to skills/design/scripts/emit-design-plan-preview.{sh,md} and skills/design/scripts/test-emit-design-plan-preview.{sh,md}
  - From Codex-Innovation: Retarget those UPDATED sections and harness/docs references to skills/design/scripts/emit-design-plan-preview.sh, skills/design/scripts/emit-design-plan-preview.md, and skills/design/scripts/test-emit-design-plan-preview.sh; avoid creating root-level preview files
  - From Cursor-Pragmatic: Retarget all emit-design-plan-preview and preview-harness bullets to skills/design/scripts/emit-design-plan-preview.sh, skills/design/scripts/emit-design-plan-preview.md, and skills/design/scripts/test-emit-design-plan-preview.sh
  - From Codex-Pragmatic: Retarget these plan entries and harness updates to skills/design/scripts/emit-design-plan-preview.sh, skills/design/scripts/emit-design-plan-preview.md, and skills/design/scripts/test-emit-design-plan-preview.sh/.md.
  - From Codex-dyn-voter-caller-surface: Retarget the plan entries at lines 283-300 to skills/design/scripts/emit-design-plan-preview.sh, skills/design/scripts/emit-design-plan-preview.md, and skills/design/scripts/test-emit-design-plan-preview.sh, and keep the Makefile target wired to that harness.


### FINDING_6: Add a mechanical once-only guard for postplan inline fallback
- **Reviewer(s)**: Cursor-dyn-fallback-reentry-invariant, Codex-dyn-fallback-reentry-invariant
- **Severity**: important
- **Concern**: The postplan fallback path says inline fallback may rerun the terminal postplan fence once, but lacks a concrete sentinel or guard. Repeated validation failures could re-enter fallback indefinitely or ambiguously instead of taking a terminal failure branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-fallback-reentry-invariant: Add a mechanical once constraint in the Step 2b SKILL fence e.g. touch/check $DESIGN_TMPDIR/.step2b-postplan-inline-retry-done before inline fallback from postplan failure and refuse a second retry routing to existing rc=10 Gate A or abort
  - From Codex-dyn-fallback-reentry-invariant: Add a minimal shell guard such as _drafter_postplan_fallback_used=false before the first fence, set it true and set plan source to inline before invoking inline fallback, and only permit the drafter-postplan fallback branch when the guard is still false.


### FINDING_7:
- **Reviewer(s)**: Cursor-dyn-voter-caller-surface
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:283-300; staged-context/scope-files.txt:10-12
- **Concern**: [SCOPE-REDUCTION] Plan and scope-files target scripts/emit-design-plan-preview.sh and bare emit-design-plan-preview.sh but the canonical script is skills/design/scripts/emit-design-plan-preview.sh. Scenario: Implementer edits or creates wrong paths; preview changes for fresh plan-summary.md never land on the script SKILL.md and run-step3-review.sh already call
- **Proposed resolution**: Rename plan entries and scope-files lines to skills/design/scripts/emit-design-plan-preview.sh .md and skills/design/scripts/test-emit-design-plan-preview.sh; remove stale scripts/ and bare duplicates


