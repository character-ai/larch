### FINDING_1: Tail wrapper missing `.pause-save-complete` early-exit
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The planned `design-step3b-tail.sh` copies the `.pause-save-complete` clear from `design-step4b.sh` but omits the early-exit guard after Gate C preview. If pause-save fires during preview, the tail wrapper can still read `SKIP_APPROVE_REQUESTED` and write `.completed/step-4` mid-pause, breaking pause/resume semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Mirror `design-step4b.sh` lines 21-24: after `emit-design-plan-preview.sh --variant gatec`, if `.pause-save-complete` exists exit 0 before skip-approve read and step-4 write; pin in `scripts/test-design-structure.sh`


### FINDING_2: Gate C full-plan display still normatively requires raw `cat` in `approval-gates.md`
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The plan updates `SKILL.md` to use `emit-design-plan-preview.sh --variant full` for Gate C "See full plan" / `Other`, but `approval-gates.md` remains the single normative Gate C source and still mandates raw `cat "$DESIGN_TMPDIR/plan.txt"` for those branches (lines ~187–204). An implementer following `approval-gates.md` can bypass the new `--variant full` helper, its allowlist checks, and its warning contract, failing the acceptance goal to retire Gate C raw-`cat` paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a narrow update for skills/design/references/approval-gates.md, or remove its authority for those branches, and replace the Gate C full-plan instructions with emit-design-plan-preview.sh --design-tmpdir "$DESIGN_TMPDIR" --variant full while preserving the re-prompt option shapes.
  - From Cursor-Innovation: Update approval-gates.md See full plan and Other branches to call emit-design-plan-preview.sh --variant full (or add a minimal references/ edit to the plan surfaces list); keep AskUserQuestion option semantics unchanged
  - From Codex-Innovation: Update only the Gate C full-plan display prose in approval-gates.md to call `emit-design-plan-preview.sh --variant full` for See full plan and Other while preserving the existing option-removal rules
  - From Cursor-Pragmatic: Extend the plan to update approval-gates.md Presentation/Prompt cat mandates to emit-design-plan-preview.sh --variant full (keep option-set logic unchanged)
  - From Codex-Pragmatic: Add approval-gates.md to the plan and replace only the Gate C full-plan display command wording with emit-design-plan-preview.sh --variant full, preserving the existing option-removal and re-prompt semantics.
  - From Cursor-Requirements: Add approval-gates.md to the plan: replace See full plan / Other full-plan cat instructions with emit-design-plan-preview.sh --variant full (keep option-removal and cap-aware re-prompt behavior unchanged)
  - From Codex-Requirements: Update the Gate C full-plan instructions in approval-gates.md, or change the SKILL.md delegation so the new emit-design-plan-preview.sh --variant full path is the sole normative full-plan display path.


### FINDING_3: Plan-heading classifier omits backticked path-token normalization
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: Production `/design` plans use backticked path tokens and whitespace-tolerant heading grammar (e.g. `### UPDATED: `docs/foo.md``). If `design-step3b-entry.sh` classifies the raw heading tail without stripping backticks, the extension becomes `md`` and docs-only plans are misrouted to `DIAGRAM_REQUIRED=true` instead of the required one-call skip path. Existing plan-scope extraction in `python/issue_wire.py` already handles backtick-wrapped paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Specify path-token normalization before classification: extract the backticked token when present, otherwise the first plain token, then strip only that token before extension and SKILL.md checks.
  - From Codex-Innovation: Match the existing heading grammar `^###[ \t]+(NEW|UPDATED|REWRITTEN)[ \t]*:` and strip one surrounding backtick pair before extension and SKILL.md checks
  - From Codex-Pragmatic: Strip surrounding markdown backticks before extension tests, or reuse the existing plan scope-path extraction behavior, while keeping missing or heading-free plans architectural.
  - From Codex-Requirements: Specify that the classifier trims whitespace and strips one surrounding backtick pair before extension and SKILL.md checks, or reuse the existing heading path extraction behavior.


