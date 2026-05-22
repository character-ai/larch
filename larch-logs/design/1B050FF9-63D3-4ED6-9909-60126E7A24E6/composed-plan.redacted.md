## Plan

Replace `/relevant-checks` skill invocation in `/implement` (and peer skills/scripts) with a direct invocation of `scripts/relevant-checks.sh` (consumer-repo top-level). Hard cutover in one PR.

### Approach

The wrapper helper `scripts/run-relevant-checks-captured.sh` stays as the orchestration boundary; only its hardcoded `CHECK_SCRIPT` target moves. The check script itself migrates out of the skill directory to `scripts/relevant-checks.sh`, the skill is deleted, and every caller's stdout-parser site learns about a new `RELEVANT_CHECKS_SKIPPED=true SITE=<site>` terminal state that replaces the current `STATUS=fail FAILURE_REASON=missing-check-script` envelope.

The wrapper distinguishes three cases for `CHECK_SCRIPT`:

- Absent file → skip with exit 0 + structured `RELEVANT_CHECKS_SKIPPED=true SITE=<site>` line + stderr breadcrumb.
- Present file that is not executable OR not a regular file → structured failure envelope `STATUS=fail EXIT_CODE=126 FAILURE_REASON=check-script-not-executable`.
- Present executable file → invoke under `cd "$REPO_ROOT"` so `git rev-parse --show-toplevel` inside the check script resolves under the intended tree.

### Order of edits

1. Create `scripts/relevant-checks.sh` + `scripts/relevant-checks.md` (sibling per `.claude/rules/script-md-siblings.md`).
2. Update `scripts/run-relevant-checks-captured.sh` + `.md` (repoint target; split missing-script branch; `cd "$REPO_ROOT"` before invoke).
3. Update every wrapper-stdout parser site in lockstep:
   - `scripts/ship-pr.sh`: add `is_relevant_checks_clean()` helper that matches both `RELEVANT_CHECKS_OK=true` and `RELEVANT_CHECKS_SKIPPED=true`; replace 4 grep sites (lines 686 / 709 / 763 / 789) with calls to the helper.
   - `skills/implement/SKILL.md` Step 3 / Step 5 / Step 6 "Continue after child returns" blocks add a `RELEVANT_CHECKS_SKIPPED=true` branch and update the `FAILURE_REASON` enum (drop `missing-check-script`, add `check-script-not-executable`). Also update line ranges 14-16, 988, 1059, 1576 for surviving `/relevant-checks` literals.
   - `skills/review/SKILL.md` Step 3e: reorder so the fenced helper invocation precedes the stdout-contract branches; add the SKIPPED branch.
   - `skills/review-and-fix/SKILL.md` line 28: align contract reference.
4. Migrate test harnesses to the new contract.
5. Delete `.claude/skills/relevant-checks/` directory entirely.
6. Delete the vestigial hook (`scripts/hook-block-skill-relevant-checks.{sh,md}` + test + `hooks/hooks.json` Skill-matcher entry + `.claude/settings.json` line 6 Bash row + line ~184 `Skill(relevant-checks)` row), plus `scripts/lib-resolve-active-larch-session.{sh,md}` after verifying it is orphan after the hook deletion.
7. Lockstep CI/lint registrations: `Makefile` (.PHONY entries, shard memberships `test-harnesses-11` / `test-harnesses-18`, target rename `test-run-checks` → `test-relevant-checks`), `agent-lint.toml` (rows ~514-523 and ~762-763), `docs/linting.md` (table rows).
8. Doc sweep across the runtime + reference surface.
9. `CHANGELOG.md` entry: migration step for downstream consumers with explicit observability wording.

### Files to create / modify / delete

**NEW**: `scripts/relevant-checks.sh`, `scripts/relevant-checks.md`, `scripts/test-relevant-checks.sh`, `scripts/test-relevant-checks.md`.

**MODIFIED (runtime + parsers)**: `scripts/run-relevant-checks-captured.sh` (+ `.md`), `scripts/ship-pr.sh` (+ `.md`), `skills/implement/SKILL.md` (Step 3 line 1107, Step 5 line 1210, Step 6 line 1306, plus lines 14-16, 988, 1059, 1576), `skills/review/SKILL.md` (Step 3e lines 46-50), `skills/review-and-fix/SKILL.md` (line 28 if it documents the contract).

**MODIFIED (tests)**: `scripts/test-relevant-checks-byte-budget.sh` (+ `.md`), `scripts/test-relevant-checks-helper-failure.sh` (+ `.md`), `scripts/test-relevant-checks-validation.sh` (+ `.md`), `scripts/test-review-relevant-checks-helper.sh` (+ `.md`), `skills/implement/scripts/test-implement-relevant-checks-anti-halt.sh` (+ `.md`), `scripts/test-ship-pr.sh`.

**DELETIONS**: entire `.claude/skills/relevant-checks/` directory; `scripts/hook-block-skill-relevant-checks.{sh,md}`; `scripts/test-hook-block-skill-relevant-checks.{sh,md}`; `hooks/hooks.json` PreToolUse → Skill matcher block; `.claude/settings.json` line 6 + line ~184; `scripts/lib-resolve-active-larch-session.{sh,md}` if orphan; `Makefile` `test-run-checks` target (renamed) + `test-hook-block-skill-relevant-checks` target.

**MODIFIED (CI/lint registrations)**: `Makefile`, `agent-lint.toml`, `docs/linting.md`.

**MODIFIED (docs)**: `README.md`, `AGENTS.md` (line 18 standing rule rewrite + canonical-sources), `SECURITY.md` (mandatory skip-semantics section), `CHANGELOG.md` (new migration entry), `docs/installation-and-setup.md` (lines 202-217 full section rewrite), `docs/skills.md`, `agent-lint.toml`, `.pre-commit-config.yaml`, `agents/{_implementer-base,codex-implementer,cursor-implementer}.md`, `skills/shared/subskill-invocation.md` (lines 98-99), `skills/design/references/plan-review-quick.md`, `skills/review/references/domain-rules.md`, `skills/alias/SKILL.md`, `skills/{compress-skill,simplify-skill}/SKILL.md` + scripts, `skills/create-skill/scripts/post-scaffold-hints.sh`, `.claude/skills/release/scripts/promote-latest-release.md`, `scripts/external-tool-registry.md`, `scripts/pre-commit-shellcheck.md`.

### Edge cases

- **Larch self-dogfooding** works because the new script is created in this PR.
- **Present but non-executable** is distinct from "missing": emits `STATUS=fail FAILURE_REASON=check-script-not-executable EXIT_CODE=126`.
- **PWD != CLAUDE_PROJECT_DIR**: wrapper `cd`s to `REPO_ROOT` before invoking the check script.
- **Mid-PR state**: wrapper looks at the new path only; old skill files are harmless until step 5 deletes them.
- **Skip-path on green-line callers**: all 4 ship-pr.sh + 3 /implement + 1 /review parser sites update in lockstep with the wrapper emission.
- **Banner literals preservation**: byte-identical preservation in the script rewrite avoids classifier drift; if changed, wrapper classifier + test fixtures update in lockstep.
- **Orphan helper verification**: grep `scripts/lib-resolve-active-larch-session.sh` callers across `skills/`, `hooks/`, `scripts/`, `.claude/settings.json`, `.github/workflows/` before deletion.

### Failure modes

1. **False-stall in ship-pr.sh on skip path** — mitigated by adding `is_relevant_checks_clean()` helper + 4 grep-site replacements + new test fixtures in the same commit as the wrapper change. Earliest warning: `test-ship-pr.sh` new SKIPPED fixture fails.
2. **Banner-string regression silently flips coverage classification** — mitigated by preserving the three banner strings byte-identical. Earliest warning: `test-relevant-checks-validation.sh` coverage assertions fail.
3. **Downstream-consumer breakage post-merge** — mitigated by explicit CHANGELOG.md migration note + SECURITY.md trust-implication paragraph + observable skip line and stderr breadcrumb. Earliest warning: post-merge operator feedback. OOS_1 tracks the broader downstream communication follow-up.

## Acceptance

- `make lint` passes.
- `make test-harnesses` (or `make test`) is green, including all migrated harnesses: `test-relevant-checks` (new), `test-relevant-checks-byte-budget`, `test-relevant-checks-helper-failure`, `test-relevant-checks-validation`, `test-review-relevant-checks-helper`, `test-implement-relevant-checks-anti-halt`, `test-ship-pr` with new SKIPPED fixtures.
- Halt-rate regression harness per `docs/linting.md` does not regress.
- Refined verification gate at PR-finalize time:
  - `grep -rn '\.claude/skills/relevant-checks' --include='*.md' --include='*.sh' --include='*.json' --include='*.toml' --include='*.yaml' --include='*.yml' --exclude-dir=larch-logs --exclude=CHANGELOG.md` returns zero hits.
  - `grep -rnE '(^|[^[:alnum:]_./-])/relevant-checks\b' --include='*.md' --include='*.sh' --include='*.json' --include='*.toml' --include='*.yaml' --include='*.yml' --exclude-dir=larch-logs --exclude=CHANGELOG.md` returns zero hits.
  - The current release section of `CHANGELOG.md` contains the migration sentinel string `RELEVANT_CHECKS_SKIPPED`.
- Local `/implement` self-run on larch succeeds at Step 3 / Step 5 / Step 6 (each `run-relevant-checks-captured.sh` invocation returns `RELEVANT_CHECKS_OK=true` since the new `scripts/relevant-checks.sh` is in tree).
- Stdout byte budget preserved: green-line + skip-line both ≤ 120 bytes.
- `RELEVANT_CHECKS_SKIPPED=true` is treated as a non-failing terminal state by all 4 `scripts/ship-pr.sh` grep sites (via `is_relevant_checks_clean()` helper), 3 `skills/implement/SKILL.md` parser blocks, and `skills/review/SKILL.md` Step 3e parser block.
- Anti-halt invariants preserved by `skills/implement/scripts/test-implement-relevant-checks-anti-halt.sh` for both green and skip continuation paths.
- `scripts/lib-resolve-active-larch-session.{sh,md}` deleted if and only if its only caller was the now-deleted hook (verified by pre-deletion grep).

diff_lines: 1100
