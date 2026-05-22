# Design Discussion — Round 1 (Step 1c + 1d)

8 decisions resolved.

## Decision 1: Wrapper layer
- **Question**: Should `scripts/run-relevant-checks-captured.sh` be kept (repointed at `scripts/relevant-checks.sh`), dropped (direct invoke), or replaced by a thin shim?
- **Resolution**: Keep the wrapper; repoint its target from `.claude/skills/relevant-checks/scripts/run-checks.sh` to `scripts/relevant-checks.sh`. The wrapper retains its current responsibilities (path validation, logging under `$IMPLEMENT_TMPDIR/relevant-checks/`, redaction via `redact-tmpdir-paths.sh | redact-secrets.sh`, structured KV stdout, byte-budget contract, token/timing ledger marks per site).
- **Source**: user

## Decision 2: Migration scope
- **Question**: Should this migration cover only `/implement`, or all callers of the relevant-checks helper (e.g., `/review`, `scripts/ship-pr.sh`, `scripts/lint-fix-loop.sh`)?
- **Resolution**: All callers, one cutover. Every direct or indirect call site shifts to the new contract in a single PR — no two-convention period.
- **Source**: user

## Decision 3: Missing-script behavior
- **Question**: When `scripts/relevant-checks.sh` is absent from the consumer repo, should the helper hard-fail (current behavior), silently skip with a breadcrumb, or skip with a structured machine line?
- **Resolution**: Silent skip with a breadcrumb on stderr and (per Decision 5) a structured machine line on stdout. Exit 0. Replaces current `STATUS=fail FAILURE_REASON=missing-check-script EXIT_CODE=127` semantics.
- **Source**: user

## Decision 4: Larch-repo migration
- **Question**: Does the larch repo need a `scripts/relevant-checks.sh` in this PR, and what happens to the existing `.claude/skills/relevant-checks/` directory?
- **Resolution**:
  - (a) Migrate `.claude/skills/relevant-checks/scripts/run-checks.sh` into `scripts/relevant-checks.sh`.
  - (b) Delete `.claude/skills/relevant-checks/` entirely (SKILL.md + scripts + tests).
  - (c) Clean up all references to `/relevant-checks` skill across the repo so the only remaining reference is the new `scripts/relevant-checks.sh` invocation path inside `/implement` (and its peers per Decision 2).
- **Source**: user

## Decision 5: Skip stdout shape
- **Question**: What should `scripts/run-relevant-checks-captured.sh` emit on stdout when the consumer script is missing?
- **Resolution**: A structured machine line: `RELEVANT_CHECKS_SKIPPED=true SITE=<site>` on stdout (≤120-byte budget), plus a stderr breadcrumb. Parsers in `/implement`, `/review`, `ship-pr.sh`, `lint-fix-loop.sh` learn to recognize this as a success-equivalent terminal state. NOT conflated with `RELEVANT_CHECKS_OK=true` (which still means "actually ran and passed").
- **Source**: user

## Decision 6: Script content
- **Question**: Should `scripts/relevant-checks.sh` be a verbatim move, a minimal-cleanup move, or a rewrite?
- **Resolution**: Rewrite is permitted, with the binding constraint that any internal reference to the about-to-be-deleted `.claude/skills/relevant-checks/` path (in comments, banners, log markers, sibling `.md`) must be reconciled. The rewrite must keep the externally-observed log banner shape that the wrapper's coverage classifier greps for (`=== Running pre-commit`, `=== Running agent-lint ===`, `WARNING: agent-lint not found on PATH`) unless the wrapper's classifier is updated in lockstep.
- **Source**: user

## Decision 7: Test-harness handling
- **Question**: What happens to the existing test harnesses (`scripts/test-relevant-checks-byte-budget.sh`, `test-relevant-checks-helper-failure.sh`, `test-relevant-checks-validation.sh`, `test-review-relevant-checks-helper.sh`, `skills/implement/scripts/test-implement-relevant-checks-anti-halt.sh`)?
- **Resolution**: Migrate + retarget. Keep the test files (renamed as appropriate), retarget assertions to the new contract: new helper target path, new skip stdout shape (`RELEVANT_CHECKS_SKIPPED=true`), preserved redaction / byte-budget / anti-halt invariants. Existing CI coverage is preserved.
- **Source**: user

## Decision 8: Hook cleanup
- **Question**: What happens to `scripts/hook-block-skill-relevant-checks.sh` and its registration in `hooks/hooks.json` once the skill is deleted?
- **Resolution**: Delete the hook (`scripts/hook-block-skill-relevant-checks.sh` + `.md`), its test (`scripts/test-hook-block-skill-relevant-checks.sh` + `.md`), and the corresponding entry in `hooks/hooks.json` (PreToolUse / Skill matcher). The hook becomes vestigial once the skill it guards no longer exists.
- **Source**: user

---

## Scope summary

**In scope (one PR)**:
- Move check logic from `.claude/skills/relevant-checks/scripts/run-checks.sh` → `scripts/relevant-checks.sh`; reconcile internal path references during the rewrite (Decision 6).
- Delete `.claude/skills/relevant-checks/` directory entirely (Decision 4).
- Repoint `scripts/run-relevant-checks-captured.sh` from old to new target (Decision 1); add skip semantics on missing target (Decisions 3, 5).
- Update every caller of relevant-checks across the runtime surface (Decision 2): `skills/implement/SKILL.md`, `skills/review/SKILL.md`, `skills/review-and-fix/SKILL.md`, `scripts/ship-pr.sh`, `scripts/lint-fix-loop.sh`, and any sibling `.md` files.
- Delete the vestigial hook (Decision 8): `scripts/hook-block-skill-relevant-checks.{sh,md}`, `scripts/test-hook-block-skill-relevant-checks.{sh,md}`, and the matching entry in `hooks/hooks.json`.
- Migrate test harnesses to new contract (Decision 7): byte budget, helper failure, validation, review-helper, anti-halt.
- Doc sweep: README.md, AGENTS.md, SECURITY.md, CHANGELOG.md, docs/*.md, agent-lint.toml, .pre-commit-config.yaml, agents/*.md, skills/*/SKILL.md (compress-skill, simplify-skill, alias, create-skill scaffold hints, design plan-review-quick, review domain-rules, shared subskill-invocation), `.claude/skills/release/scripts/promote-latest-release.md`, `.claude/settings.json` (if it references the hook).

**Hard constraints**:
- Halt-rate regression harness (per `docs/linting.md`) must not regress.
- `make lint` must pass post-change.
- Byte-budget assertion (≤120 bytes on green/skip-path stdout) must be preserved.
- Log banner strings (`=== Running pre-commit`, `=== Running agent-lint ===`, `WARNING: agent-lint not found on PATH`) must keep matching the wrapper's coverage classifier OR the classifier must be updated in lockstep.
- Running `/implement` on larch itself must continue to perform relevant-checks (via the new `scripts/relevant-checks.sh` introduced in this PR).
- Anti-halt invariants for relevant-checks call sites must be preserved (the existing `skills/implement/scripts/test-implement-relevant-checks-anti-halt.sh` assertion target).

**Non-goals / out of scope**:
- No backward-compatibility shim for consumer repos that still rely on `.claude/skills/relevant-checks/`. The cutover is hard. Documentation in CHANGELOG.md should note the migration step for downstream consumers (add `scripts/relevant-checks.sh`).
- No new check categories introduced; only the dispatch path changes.
- No change to the wrapper's redaction pipeline (`redact-tmpdir-paths.sh | redact-secrets.sh`) or its log-dir tmpdir validation logic.
