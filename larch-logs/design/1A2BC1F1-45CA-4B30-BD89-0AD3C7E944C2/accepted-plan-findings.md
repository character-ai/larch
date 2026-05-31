### FINDING_1: Stale plan-review-loop breadcrumb omits Override option
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Concern**: When `SOFT_ADVISORY=true` fires under a HARD trigger, the script still prints a two-option breadcrumb (“plan-body gate still requires Split/Cancel”) while the operator prompt will offer three options (Split / Override / Cancel). The plan updates SKILL.md and `test-design-structure.sh` for that phrase but does not include `plan-review-loop.sh` in its modified-files list, so user-visible guidance can contradict `AskUserQuestion`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Add `skills/design/scripts/plan-review-loop.sh` to the modified-files list and update line 575 from `plan-body gate still requires Split/Cancel` to `plan-body gate still requires the Split / Override / Cancel prompt` (or the exact phrase chosen for SKILL.md). Also update `plan-review-loop.md` sibling per `.claude/rules/script-md-siblings.md`.


### FINDING_2: Override audit omits full append-tool-failure.sh contract
- **Reviewer(s)**: unknown-slot, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Planned Override audit prose (hard trigger in SKILL.md and sprawl in `discussion-rounds.md`) cites only a subset of `append-tool-failure.sh` flags (`--category`, `--exit-code`, `--tool`, `--redact`, or “append a Warnings entry”). The helper requires `--log`, `--site`, and `--output-file` (file must exist). A minimal implementation can skip the write, call without a log path, or exit 2; with `|| true` the gate still proceeds but run logs often lack the promised override record.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Mirror the existing validate-plan-commands Override block (SKILL.md:1401): write a small capture file first, then append with --log, --site (design Step 2b.5 / Step 1c / Step 1d), --tool (e.g. operator-override-hard-trigger / operator-override-sprawl-heuristic), --exit-code 0, --output-file, --redact
  - From Cursor-Innovation: Mirror the existing plan-command Override pattern in skills/design/SKILL.md (~1401): write $DESIGN_TMPDIR/operator-override-sprawl.log first, then append with --site design Step 1c sprawl heuristic or design Step 1d sprawl heuristic, --tool operator-override-sprawl, --exit-code 0, --category Warnings, --redact
  - From Cursor-Pragmatic: Match the full invocation pattern at skills/design/SKILL.md:1401 (--log, --site design Step 2b.5, --output-file for the trigger-context log, then --redact)


### FINDING_3: Step 1c/1d sprawl Override widens scope beyond Step 2b.5 Hard branch
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Concern**: Feature scope targets Step 2b.5 Hard branch only, but the plan extends Override-and-proceed to Step 1c/1d semantic-sprawl heuristics in `discussion-rounds.md` (and related SKILL.md / `test-design-structure.sh` pins). That adds distinct semantics (pre-plan flow vs plan review), extra prose and test surface, and behavior not called out in scope—conflicting with minimum-change / SIMPLE-tier expectations unless explicitly justified in the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Remove the discussion-rounds.md sprawl-heuristic Override additions and confine the change to SKILL.md Step 2b.5, approval-gates.md, flags.md, README.md, and test-design-structure.sh; if the sprawl expansion is intentional, call it out explicitly in the plan's ## Scope section
  - From unknown-slot: Limit this PR to Step 2b.5 hard-trigger Override only. File a follow-up issue for sprawl-prompt Override if desired. Remove the discussion-rounds.md edits and the DISCUSSION_MD test pin from this change; the Step 1d "Split / Cancel only, no Continue" sentence and the Step 1c "exactly two options" prose stay as-is.


### FINDING_4: flags.md partition bullet still describes two-option hard prompt
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Concern**: The `--partition` bullet in `skills/design/references/flags.md` describes the hard-trigger-alongside-partition case as showing a “hard **Split/Cancel** prompt” (two options). After the change, that prompt is Split / Override / Cancel. The plan says not to touch the partition-only path clauses, but the bullet’s hard-trigger clause is stale and misleads operators.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Add a minimal update inside the `--partition` bullet to change "the hard **Split/Cancel** prompt" to "the hard **Split/Override/Cancel** prompt". The preceding "no Continue option, no threshold inspection" clause describes the partition-only (no hard trigger) path and is correct as-is; only the hard-trigger-alongside-partition description needs updating.

---

**Merge notes (diagnostic, not part of machine output):**
- Input FINDING_2–4 → aggregated **FINDING_2** (same audit-contract risk; distinct verbatim fixes preserved).
- Input FINDING_5–6 → aggregated **FINDING_3** (same scope-creep risk; severity **important** over **nit**).
- Input FINDING_1 and FINDING_7 kept separate (different files and fixes despite similar “two vs three options” theme).

