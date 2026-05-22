### FINDING_1: Wrapper `[[ ! -x "$CHECK_SCRIPT" ]]` conflates absent vs present-non-executable

- **Reviewers**: Cursor-Arch, Cursor-Edge, Cursor-Innovation, Codex-Arch, Codex-Edge, Codex-Pragmatic, Codex-Requirements (7/10)
- **Concern**: The planned skip branch at `scripts/run-relevant-checks-captured.sh:133-137` uses `[[ ! -x "$CHECK_SCRIPT" ]]`, which fires for both (a) the file is missing AND (b) the file is present but not executable (e.g., a consumer forgot `chmod +x`, or a partial checkout, or a non-regular file like a directory). Both states emit the same skip envelope and exit 0, so a broken migration is silently treated as "no checks configured."
- **Proposed resolution**: Split the branch. Skip ONLY when the file is absent (`[[ ! -e "$CHECK_SCRIPT" ]]`). When the file exists but is not executable / not a regular file, emit a structured failure envelope: `STATUS=fail EXIT_CODE=126 FAILURE_REASON=check-script-not-executable` and exit 126. Add a harness case for each branch.


### FINDING_10: skills/shared/subskill-invocation.md:98-99 generic clause still references slash-skill

- **Reviewers**: Cursor-Requirements (1/10)
- **Concern**: The generic anti-halt clause at lines 98-99 still requires anti-halt coverage for "every direct `/relevant-checks` Skill invocation," which becomes invalid when the Skill is deleted.
- **Proposed resolution**: Add this file to the doc sweep with concrete replacement wording tied to `run-relevant-checks-captured.sh` (the helper-based invocation) and optionally direct `bash scripts/relevant-checks.sh`.


### FINDING_12: scripts/run-relevant-checks-captured.md stale callers list + missing SKIPPED in grammar

- **Reviewers**: Cursor-Edge (1/10)
- **Concern**: The .md callers list references Steps 10 / 12c, which are stale versus the current `/implement` (Steps 3, 5, 6). Success grammar omits the new third terminal state.
- **Proposed resolution**: Sync the .md: accurate caller enumeration (Steps 3, 5, 6 in `/implement`; Step 3e in `/review`); document `RELEVANT_CHECKS_SKIPPED=true SITE=<site>` alongside the green-line grammar.


### FINDING_13: Plan claims removing `missing-check-script` assertion from a harness that does not have one

- **Reviewers**: Cursor-Pragmatic (1/10)
- **Concern**: The plan's "Migrate test harnesses" section says `scripts/test-relevant-checks-helper-failure.sh` will have its `missing-check-script` assertion removed, but inspection shows the harness does not actually pin that envelope today.
- **Proposed resolution**: Drop the "remove" language in the plan; describe only the addition of a new skip-path assertion. (Verify by grepping the harness for `missing-check-script`.)


### FINDING_15: CHANGELOG bullet wording "silent skip" understates observability

- **Reviewers**: Cursor-Edge (1/10)
- **Concern**: The plan's CHANGELOG bullet describes the new behavior as "silent skip," but the wrapper emits a stderr breadcrumb via `larch_err` plus a machine-readable stdout line. Operators reading the CHANGELOG may underestimate observability.
- **Proposed resolution**: Tighten the wording to "non-blocking skip with stderr breadcrumb + `RELEVANT_CHECKS_SKIPPED=true` stdout signal."


### FINDING_16: skills/review/SKILL.md:46-50 Step 3e prose order makes the third terminal state easy to miss

- **Reviewers**: Cursor-Innovation (1/10)
- **Concern**: Step 3e quotes `RELEVANT_CHECKS_OK=true` and `STATUS=fail` semantics BEFORE the fenced helper invocation. When adding a third terminal state (`RELEVANT_CHECKS_SKIPPED=true`), the prose ordering makes it easy to misread which child the branch refers to (the `/review-and-fix` return vs. the relevant-checks helper).
- **Proposed resolution**: Reorder Step 3e: put the helper invocation block first, then list OK / SKIPPED / STATUS=fail parsing branches in order.


### FINDING_2: AGENTS.md:18 standing rule "After any change, run `/relevant-checks`" not in doc-sweep checklist

- **Reviewers**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements (5/10)
- **Concern**: AGENTS.md line 18 (the operational editing rule "After any change, run `/relevant-checks`") references a Skill that no longer exists post-cutover. The plan's AGENTS.md bullet only mentions canonical-sources updates and does not explicitly schedule this line. The final grep gate will catch the surviving `/relevant-checks` literal but implementers may miss the exact line.
- **Proposed resolution**: Add an explicit AGENTS.md:18 work item to the doc-sweep section: rewrite line 18 to `bash scripts/relevant-checks.sh` (or `make test-relevant-checks` / the captured helper) and drop the slash-skill wording.


### FINDING_20: skills/implement/SKILL.md has more `/relevant-checks` references than just Steps 3/5/6

- **Reviewers**: Cursor-Arch, Cursor-Requirements (2/10)
- **Concern**: Specific lines outside the three "Continue after child returns" blocks: 14-16 (anti-halt reminder), 988 (permissions / always-permitted writes), 1059 (Step 2 guidance), 1576 (Step 6 stall narrative). The plan's SKILL.md edit list does not explicitly enumerate these.
- **Proposed resolution**: Expand the SKILL.md edit scope to enumerate these line ranges, with consistent wording: `relevant-checks helper` (referencing the wrapper) or `scripts/relevant-checks.sh` (referencing the new convention).

---

## OOS Items


### FINDING_3: `.claude/settings.json` `Skill(relevant-checks)` entry not removed

- **Reviewers**: Cursor-Arch, Cursor-Edge, Cursor-Innovation, Codex-Requirements (4/10)
- **Concern**: The plan removes the Bash permission row at `.claude/settings.json` line 6 but does not call out removing the `Skill(relevant-checks)` allow entry (around line 184). Stale strict-permissions surface contradicts deleting the skill.
- **Proposed resolution**: Extend the `.claude/settings.json` cleanup to include the `Skill(relevant-checks)` entry (and any namespaced variants like `Skill(larch:relevant-checks)`). Add a validation grep for these forms in the verification step.


### FINDING_4: Final grep gate is broken — matches `scripts/relevant-checks.sh` (new path) AND historical CHANGELOG entries

- **Reviewers**: Codex-Arch, Codex-Pragmatic (grep matches new path), Cursor-Requirements, Codex-Edge, Codex-Innovation, Codex-Requirements (CHANGELOG historical entries) (6/10)
- **Concern**: Two related problems with the gate `grep -rnE '\.claude/skills/relevant-checks|\b/relevant-checks\b' …`:
  1. `\b/relevant-checks\b` matches the new convention `scripts/relevant-checks.sh`, so even a correct migration cannot pass the gate.
  2. `CHANGELOG.md` retains historical entries with the alternation pattern. The plan excludes `larch-logs/` but not the historical CHANGELOG sections.
- **Proposed resolution**: Refine the gate. Use a stricter pattern that catches only `.claude/skills/relevant-checks` and slash-command `/relevant-checks` NOT followed by a path character like `.` or `/`. Example: `(^|[^[:alnum:]_./-])/relevant-checks\b` for the slash-command form. Exclude `CHANGELOG.md` from the alternation gate; separately assert that the current release section contains the migration note.


### FINDING_5: Makefile + agent-lint.toml + docs/linting.md cleanup for renamed/deleted harnesses

- **Reviewers**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Edge, Codex-Requirements (5/10)
- **Concern**: The plan deletes `scripts/test-hook-block-skill-relevant-checks.{sh,md}` and renames `test-run-checks` → `test-relevant-checks`, but does not explicitly enumerate the dependent Make / agent-lint / linting.md updates:
  - `Makefile` `.PHONY` entries for the deleted/renamed targets.
  - `Makefile` `test-harnesses-11` / `test-harnesses-18` shard membership.
  - `agent-lint.toml` reachability allowlist rows at lines ~514-523 (deleted hook test) and ~762-763 (skill/hook paths).
  - `docs/linting.md` table row for the deleted hook harness.
- **Proposed resolution**: Add an explicit "Lockstep CI/lint registrations" sub-section to the deletion checklist enumerating each of these files and the specific edits.


### FINDING_6: docs/installation-and-setup.md is a full consumer-dependency section, not a setup-step tweak

- **Reviewers**: Cursor-Edge, Cursor-Requirements, Codex-Innovation (3/10)
- **Concern**: `docs/installation-and-setup.md` lines 202-217 currently scaffold an entire consumer workflow that creates `.claude/skills/relevant-checks/`, a SKILL.md, and references the blocking hook. The plan's doc-sweep entry just says "update setup steps" — that underspecifies the change.
- **Proposed resolution**: Name a full section rewrite for the `scripts/relevant-checks.sh` model: drop the skill-scaffold steps, document the new contract, update the hooks-narrative subsection after `hook-block-skill-relevant-checks.sh` removal.


### FINDING_7: SECURITY.md must include skip semantics (mandatory, not conditional)

- **Reviewers**: Cursor-Pragmatic, Cursor-Requirements (3/10 across two related findings)
- **Concern**: The skip path is a fail-open shift in the trust boundary (exit 0 + stderr breadcrumb replacing exit 127 + STATUS=fail). The plan's SECURITY.md entry is currently framed as a light "if cited" touch.
- **Proposed resolution**: Elevate `SECURITY.md` to a required update documenting `RELEVANT_CHECKS_SKIPPED=true`, exit 0, and the stderr breadcrumb meaning. State explicitly that an unobserved skip line means "no local checks ran" with the operator-trust implication.


### FINDING_8: Orphan helper `scripts/lib-resolve-active-larch-session.{sh,md}` after hook deletion

- **Reviewers**: Codex-Arch (1/10)
- **Concern**: Per Codex's repo inspection, `scripts/lib-resolve-active-larch-session.sh` is referenced only by `scripts/hook-block-skill-relevant-checks.sh`. Deleting the hook without deleting its sole consumer leaves dead runtime surface.
- **Proposed resolution**: Verify the caller surface (grep for callers across `skills/`, `hooks/`, `scripts/`, `.claude/settings.json`, `.github/workflows/`). If truly orphan after the hook deletion, add `scripts/lib-resolve-active-larch-session.{sh,md}` to the deletion list. Otherwise, document the retained caller.


### FINDING_9: Wrapper invokes CHECK_SCRIPT from CLAUDE_PROJECT_DIR but the new script uses cwd's git tree

- **Reviewers**: Codex-Edge (1/10)
- **Concern**: `scripts/run-relevant-checks-captured.sh` resolves `REPO_ROOT` from `CLAUDE_PROJECT_DIR`, but the migrated `scripts/relevant-checks.sh` runs `git rev-parse --show-toplevel` from the current `PWD`. If `PWD` is a different git repo than `CLAUDE_PROJECT_DIR`, the script validates the wrong tree (or fails with "not in a git repository").
- **Proposed resolution**: Either have the wrapper `cd "$REPO_ROOT"` before invoking `CHECK_SCRIPT`, or have `scripts/relevant-checks.sh` derive its own repo root from `BASH_SOURCE[0]` and use `git -C` for all git calls. Add a regression test where `PWD` differs from `CLAUDE_PROJECT_DIR`.


