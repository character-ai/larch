## Proposed Design Outline

### Goals
- Prevent the failure mode where Codex commits a test-pin literal that diverges from the implementation text it wrote in the same review-fix commit (root cause of CI stall on PR #3057).
- Catch literal/file divergence at commit time (relevant-checks lane) so review-and-fix re-loops locally instead of stalling CI mid-`/implement`.
- Reinforce the rule in the Codex implementer prompt so the model is biased to derive `contains` literals from the file it is editing rather than paraphrase.

### Non-goals
- Refactoring `test-design-structure.sh` internals.
- Changing how pre-commit hooks are configured.
- Wiring other pin-heavy harnesses (`test-anti-halt-banners.sh`, `test-prompt-template-invariants.sh`, `test-subskill-anchors.sh`, …) into `relevant-checks.sh` — explicitly deferred per Step 1c user decision.

### Approach sketch
- **Option A — relevant-checks routing**: extend the case statement in `scripts/relevant-checks.sh` so changes to `skills/design/SKILL.md` and `skills/design/references/*.md` route to `append_target_once test-design-structure`. Mirrors the existing `test-lint-foreground-markers` pattern at line ~52.
- **Option B — `scripts/check-contains-pins.sh`**: new Bash 3.2-compatible script that scans `contains` assertions in `test-*.sh`, resolves the target file via the variable assignment immediately above the assertion (e.g., `SKILL_MD="$REPO_ROOT/skills/design/SKILL.md"`), and verifies each literal exists verbatim in that file. Wired into `relevant-checks.sh` (post-review-fix lane) so it runs on the same commit-time path that already failed.
- **Option C — Codex prompt note**: append a short discipline rule to `agents/codex-implementer.md` directing Codex, when editing a file that has `contains`-style assertions referencing it, to quote the edited file verbatim instead of paraphrasing.
- Cover all three with offline harnesses (`test-check-contains-pins.sh` for B; smoke-test additions in `test-relevant-checks.sh` for A; static-grep coverage of the new Codex prompt prose).

### Surfaces in scope
- `scripts/relevant-checks.sh` (UPDATED, Option A wiring)
- `scripts/check-contains-pins.sh` (NEW, Option B)
- `scripts/check-contains-pins.md` (NEW, sibling spec per `.claude/rules/script-md-siblings.md`)
- `scripts/test-check-contains-pins.sh` + `scripts/test-check-contains-pins.md` (NEW, offline harness)
- `Makefile` (UPDATED, register `test-check-contains-pins` make target + add to a `test-harnesses-N` shard)
- `agents/codex-implementer.md` (UPDATED, Option C prompt-discipline rule)
- `scripts/test-relevant-checks.sh` (UPDATED, fixture covering the new design-md → test-design-structure route)
- Possibly `scripts/test-codex-implementer.sh` (UPDATED, literal pin for the new Codex prompt rule)

### Open questions
- Should `check-contains-pins.sh` scan ALL `test-*.sh` files or only the ones changed in the current commit set? Recommended: scan all `test-*.sh` for assertions whose target file is in `$MODIFIED_FILES`, so a `references/*.md` edit triggers verification of every pin against it (regardless of which test script holds the pin).
- Where in `relevant-checks.sh` should `check-contains-pins.sh` run — inside `run_direct_relevant_targets` as a new make target, or as a standalone post-`pre-commit` hook? Recommended: standalone post-`pre-commit` invocation parallel to `agent-lint` so it runs even when no make target was triggered.
