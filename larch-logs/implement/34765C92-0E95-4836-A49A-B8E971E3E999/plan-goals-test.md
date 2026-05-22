## Goal
Purge dead code left by the /design and /implement boundary rework: delete retired scripts, update callers to conventional paths, and fix CI harnesses.

## Implementation Plan
## Plan

### Files to delete

**Runtime scripts:**
- `scripts/persist-post-plan-keys.sh`
- `skills/implement/scripts/post-design-boundary.sh`
- `skills/implement/scripts/hook-post-design.sh`
- `skills/design/scripts/classify-issue.sh`
- `skills/design/scripts/write-design-manifest.sh`
- `skills/design/scripts/read-design-manifest.sh`
- `skills/design/references/heavy-worker.md`
- `skills/design/references/heavy-worker.digest.md`

**Contract docs:**
- `skills/implement/scripts/post-design-boundary.md`
- `skills/implement/scripts/hook-post-design.md`
- `skills/design/scripts/classify-issue.md`
- `skills/design/scripts/write-design-manifest.md`
- `skills/design/scripts/read-design-manifest.md`

**Test files:**
- `skills/design/scripts/test-classify-issue.sh` + `.md`
- `skills/design/scripts/test-design-manifest.sh` + `.md`
- `scripts/test-persist-post-plan-keys.sh`
- `scripts/test-implement-post-design-boundary.sh`
- `skills/implement/scripts/test-post-design-boundary.sh` + `.md`

### Files to modify

**Runtime scripts:**

`scripts/run-step5-review.sh`, `scripts/run-step1-plan-log.sh`, `skills/implement/scripts/run-step2-dispatch.sh`
- Replace `session_get PLAN_FILE` with `PLAN_FILE="$IMPLEMENT_TMPDIR/plan.txt"` in all three
- Replace `session_get POST_PLAN_WORKFLOW_PATH` with hardcoded `WORKFLOW_PATH="HARD"` in step5 and step2
- Update error messages to remove `persist-post-plan-keys.sh` references

`scripts/ship-pr.sh`
- Update `resolve_plan_file()` to prefer `$IMPLEMENT_TMPDIR/plan.txt` when PLAN_FILE absent from session-env
- Update CI-fix/rebase-rebump plan-context forwarding paths accordingly

`skills/design/scripts/design-driver.sh`
- Remove `CLASSIFY)` case from `run_action()` and `process_line()` dispatcher

`scripts/write-run-params.sh`
- Remove `router-pre-design` from `--source` enum; update usage string

`hooks/hooks.json`
- Remove PostToolUse Skill hook entry for `hook-post-design.sh` (keep bump-version hook)

**SKILL.md and docs:**

`skills/design/SKILL.md`
- Step 0b: `design_classification_source=caller-forwarded` (not tier-flag); remove ACTION=CLASSIFY sentence
- Step 2a: Remove entire Subagent heavy phase conditional block (non-inline dispatch, DESIGN_HEAVY gate, on-complete/failed branches)
- Step 2a.5: Replace `references/heavy-worker.digest.md` reference with inline dirty-tree probe description
- Step 5c: Remove STANDALONE_HEAVY_FAILED guard
- Plan helper contracts: Remove heavy-worker.md, heavy-worker.digest.md, manifest entries, classify-issue.sh, hook-post-design.md

`skills/design/references/flags.md`
- Rewrite non-inline dispatch paragraph to describe inline-only; remove heavy-worker.md and --subagent/--inline references

`skills/implement/SKILL.md`
- Anti-halt reminder: remove persist-post-plan-keys.sh reference
- NEVER #12: update archival note (deletion completed #2487)
- NEVER #14: remove persist-post-plan-keys.sh from sanctioned writers; update example error text
- Line ~97 legacy: remove post-design-boundary.md archival entry
- Exit code 2 table: remove persist-post-plan-keys reference
- Step 1 sub-step 4: remove persist-post-plan-keys.sh block; note conventional-path derivation

`AGENTS.md`
- Update `/design --subagent requires SendMessage` bullet: inline-only design, remove heavy-worker.md reference
- NEVER session-env rule: remove persist-post-plan-keys.sh from sanctioned writers

`SECURITY.md`
- Update PostToolUse paragraph: hook-post-design.sh retired in #2487

**Contract doc siblings:**
- `scripts/run-step5-review.md`, `scripts/run-step1-plan-log.md`, `skills/design/scripts/design-driver.md`, `scripts/write-run-params.md`, `scripts/ship-pr.md`
- Update each to match their corresponding .sh changes (conventional paths, removed actions, updated enum)

**CI harnesses:**

`scripts/test-implement-structure.sh`
- Remove persist-post-plan-keys.sh assertions (lines 184-191)
- Add absence pins: persist-post-plan-keys and post-design-boundary.sh must not appear in implement SKILL.md

`scripts/test-design-structure.sh`
- Remove checks 4c, 12, 12b, 12c (heavy-worker.md assertions)
- Remove from check 8 only lines 223-224 and 234-235 (heavy-worker.md pins); retain lines 225-232 (plan-block-write.sh assertions)
- Remove checks 14b, 14c (ACTION=CLASSIFY and heavy-worker content pins)
- Remove check 10 (--subagent/subagent_mode=true mandates)
- Add absence pins: heavy-worker.md, DESIGN_HEAVY=, write-design-manifest, classify-issue, ACTION=CLASSIFY, --subagent, subagent_mode=true must not appear in skills/design/SKILL.md; heavy-worker.md must not appear in flags.md

`scripts/test-write-run-params.sh`
- Update 4 test cases (lines 27, 47, 69, 91) from `--source router-pre-design` to `--source caller-forwarded`
- Add rejection test: passing `--source router-pre-design` must exit non-zero

`scripts/test-run-step5-review.sh`, `scripts/test-run-step1-plan-log.sh`, `scripts/test-run-step2-dispatch.sh`
- Update fixtures: write plan.txt to $IMPLEMENT_TMPDIR/plan.txt; remove PLAN_FILE and POST_PLAN_WORKFLOW_PATH session-env writes

`scripts/test-anti-improvised-wakeup.sh` and `scripts/test-implement-anti-halt.sh`
- Audit for references to hook-post-design, post-design-boundary, persist-post-plan-keys; update any pins to surviving post-cutover literals

`Makefile`
- Remove test-design-manifest, test-classify-issue, test-post-design-boundary, test-implement-post-design-boundary, test-persist-post-plan-keys from .PHONY, shards (6/9/11/13/18), and target definitions

`docs/linting.md`
- Remove table rows for `make test-classify-issue` and `make test-design-manifest`

`agent-lint.toml`
- Remove manifest entries for all deleted scripts (hook-post-design.sh/.md, test-persist-post-plan-keys, test-implement-post-design-boundary, test-classify-issue, test-design-manifest) and their comment blocks

### Approach

Treat the deletion + caller update + CI update as a single atomic commit so no intermediate state has SKILL.md calling a deleted script. Prefer: remove Makefile targets and SKILL.md call sites in the same change as deleting the scripts. `persist-implement-run-flags.sh` is preserved. `write-session-env.sh` already has no PLAN_FILE writers (verified, no change needed).

### Testing strategy

- `make test-design-structure` — verify old checks removed, new absence pins pass
- `make test-implement-structure` — verify old persist-post-plan-keys checks removed, new absence pins pass
- `make test-write-run-params` — verify router-pre-design rejected as invalid source
- `make test-run-step5-review`, `test-run-step1-plan-log`, `test-run-step2-dispatch` — verify conventional-path derivation
- `make test-design-driver` — verify CLASSIFY removed from dispatcher
- `make test-anti-improvised-wakeup test-implement-anti-halt` — verify no stale pins
- `make lint` — full lint pass (shellcheck, markdownlint, agent-lint)
- `/relevant-checks` — pre-commit validation
- **Smoke-test**: Complete issue-anchored `/implement` session to verify PLAN_FILE flows through Step 1 → Step 2 → Step 5 → ship-pr.sh without PLAN_FILE missing errors

## Acceptance

- No broken references remain (grep clean across docs/, skills/, scripts/, AGENTS.md, README.md)
- `make lint` and `agent-lint` pass
- The smoke-test flow from the cutover issue still completes end-to-end

## Out-of-scope issues accepted for filing:
- OOS_1: `skills/shared/subskill-invocation.md` still references manifest/persist-post-plan-keys surfaces
- OOS_2: `docs/review-agents.md` still describes POST_PLAN_WORKFLOW_PATH as Step 5 source

diff_lines: 2800

## Test plan
(no test plan section in plan-file)
