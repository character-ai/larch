## Proposed Design Outline

### Goals
- Collapse Step 5c's validate -> redact -> publish from 3 mechanical Bash turns into one `design-publish.sh` call (core of #3418).
- Eliminate the vestigial `review_budget` knob and `--force-validate`; plan-command validation runs unconditionally.
- Make validator failures self-healing: the agent auto-repairs the plan and escalates to the user (root cause + options) only when warranted.

### Non-goals
- Do not remove `design_classification` (SIMPLE vs HARD) — it stays as the real tier signal.
- Do not change what the validator checks (Tier 2 / Tier 3 semantics; Tier 3 stays disabled for `composed-plan.md`).
- Do not touch `/implement` (already has no SIMPLE/HARD split and never read `review_budget`).

### Approach sketch
- `design-publish.sh` absorbs validate + redact: take `composed-plan.md`, validate (Tier 2), redact to `composed-plan.redacted.md`, publish — one foreground call; return `VALIDATE_STATUS=defects-found` to hand back on defects; add `--skip-validate` for the operator accept/proceed path.
- Drop `review_budget` from `design-init-runparams.sh` + `write-run-params.sh` (schema), and remove the `quick`-skip + `--force-validate` from `design-postplan-emit.sh`.
- Rewrite the shared `### Plan command validator failure` handler (Step 2b, Gate B, discussion-round2, Step 5c): diagnose root cause -> auto-fix + re-validate (cap 2) -> AskUserQuestion with root cause + options only when warranted.
- Thin SKILL.md Step 5c items 2-4 to the thin-fence `design-publish.sh` call; preserve the foreground-required invariant.

### Surfaces in scope
- `skills/design/scripts/design-publish.{sh,md}`, `design-postplan-emit.{sh,md}`, `design-init-runparams.sh`
- `scripts/write-run-params.{sh,md}`
- `skills/design/SKILL.md` (Step 5c, Step 2a, shared validator-failure handler, helper list)
- `skills/design/references/flags.md`, `approval-gates.md`, `discussion-rounds.md`
- Harnesses: `test-design-publish.sh`, `test-design-structure.sh`, `test-design-postplan-emit.sh`, `test-write-run-params.sh`

### Open questions
- None.
