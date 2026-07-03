## Goal
Implement issue #6101: [IMPLEMENTING] Restore dyslexia-optimized readability style across all larch skills.

## Implementation Plan
## Plan

## Approach

- Treat the supplied `NO_SKETCHES` synthesis as a direct-inspection path. Do not invent planning-panel agreement.
- Move the readability authority from `/design` scope to shared skill scope.
- Repoint all live references from `skills/design/references/readability-style.md` to `skills/shared/readability-style.md`.
- Use `${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md` in public `skills/**` prose.
- Use `$PWD/skills/shared/readability-style.md` in dev-only `.claude/skills/**` prose.
- Add one readability directive to every `SKILL.md`.
- Add extra directives only at real prose-composition sites:
  - `/design` Step 2b plan drafting.
  - `/design` outline composition.
  - `/design` Step 5 final composition.
  - `/implement` execution issue, OOS, rejected finding, stall, bail, and final prose surfaces.
- Keep non-design external prompt token wiring out of scope.
- Keep machine grammars byte-stable. Only narrow the prose exemption.
- Extend the lint so future token-cost work cannot silently remove coverage.

## Files to modify/create

### NEW: skills/shared/readability-style.md

Move the current style guide here. Rewrite the Consumer and Contract lines for all larch skills. Restore the rule: when unsure how short to go, go shorter. Keep the existing style axes and precedence. Rewrite the Substitution Token section so the `<READABILITY_STYLE>` expansion contract applies only to prompt surfaces that already embed the token (currently `/design` brainstorm-prompts and plan-review). State that all other skills use direct readability directives; this issue adds no new token wiring.

### UPDATED: skills/design/references/readability-style.md

Remove this file after the move. Do not leave a shim.

### UPDATED: AGENTS.md

Point Output Style at `skills/shared/readability-style.md` as the source of truth. Keep the section within the current Tier-1a cap. Preserve chat-only rules such as confirm or correct up front and stop early. Narrow the machine-parsed exemption so prose inside templates still follows the style.

### UPDATED: skills/design/SKILL.md

Replace soft readability prose with root-path mandatory directives. Restore the Step 2b plan-drafting anchor. Keep step marker placement compatible with the lint.

### UPDATED: skills/design/references/design-outline.md

Replace the soft style load with a mandatory root-path directive before outline prose composition.

### UPDATED: skills/design/references/finalize-step5.md

Restore the mandatory root-path directive at Step 5 entry before diagram, final plan, summary, and Gate C prose composition.

### UPDATED: skills/design/references/brainstorm.md

Repoint every readability reference to the shared root-path form. Its counted MANDATORY anchor keeps the closing-backtick-then-`.**` suffix on `${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md`. Keep the existing external prompt substitution behavior unchanged.

### UPDATED: skills/design/references/approval-gates.md

Repoint its counted MANDATORY anchor line to `${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md`, keeping the counted suffix: closing backtick immediately followed by `.**`.

### UPDATED: skills/design/references/discussion-rounds.md

Repoint this reference's counted MANDATORY anchor the same way as approval-gates.md: shared root path inside backticks with the `.**` suffix intact.

### UPDATED: skills/design/references/settle-rc-dispatch.md

Keep expected count zero unless inspection finds user-facing prose composition. If it stays zero, do not add a directive.

### UPDATED: skills/design/references/brainstorm-prompts.md

Keep the existing `<READABILITY_STYLE>` prompt lines. Do not add new non-design token wiring.

### UPDATED: skills/design/references/plan-review.md

Keep the existing plan-review `<READABILITY_STYLE>` line. No topology change.

### UPDATED: skills/alias/SKILL.md

Add a public-skill readability directive near the entry prose.

### UPDATED: skills/block-issue/SKILL.md

Add a public-skill readability directive covering block and unblock status prose.

### UPDATED: skills/bug/SKILL.md

Add a public-skill readability directive before issue-body prose drafting.

### UPDATED: skills/cleanup/SKILL.md

Add a public-skill readability directive before user-facing cleanup reporting.

### UPDATED: skills/deps/SKILL.md

Add a public-skill readability directive before proposal and approval prose.

### UPDATED: skills/fluff-analysis/SKILL.md

Add a public-skill readability directive before report composition.

### UPDATED: skills/gc-run-logs/SKILL.md

Add a public-skill readability directive before report or PR prose.

### UPDATED: skills/im/SKILL.md

Add a public-skill readability directive despite being an alias-style skill, because the file has user-facing usage prose.

### UPDATED: skills/implement/SKILL.md

Add a skill-entry readability directive. Add or restore local directives at free-prose surfaces where entry load is too far away. Reword the rejected-finding template so detail means actionable content, not length.

### UPDATED: skills/implement/references/execution-issues-tracking.md

Add a readability directive before composing execution issue descriptions, OOS descriptions, and manual filing prose.

### UPDATED: skills/implement/references/stall-recovery.md

Add a readability directive before terminal stall report, fallback print, and root-cause prose composition.

### UPDATED: skills/implement/scripts/write-final-report.md

Add a readability directive for final report prose if this script reference is used to compose or review final report text.

### UPDATED: skills/issue/SKILL.md

Add a public-skill readability directive before issue title and body drafting.

### UPDATED: skills/pause/SKILL.md

Add a public-skill readability directive before pause or resume user-facing prose.

### UPDATED: skills/rejected-analysis/SKILL.md

Add a public-skill readability directive before report and issue prose.

### UPDATED: skills/report-tokens/SKILL.md

Add a public-skill readability directive before analysis report prose.

### UPDATED: skills/research/SKILL.md

Add a public-skill readability directive before synthesis and validation report prose. Do not add `<READABILITY_STYLE>` tokens to research external prompts in this issue.

### UPDATED: skills/review/SKILL.md

Add a public-skill readability directive before review summaries, OOS presentation, and description-mode prose.

### UPDATED: skills/review-and-fix/SKILL.md

Add a public-skill readability directive before status or remediation prose.

### UPDATED: skills/set-up-forked-open-source-repo/SKILL.md

Add a public-skill readability directive before setup status and operator guidance prose.

### UPDATED: skills/status/SKILL.md

Add a public-skill readability directive before rendering the health report.

### UPDATED: skills/upgrade-larch/SKILL.md

Add a public-skill readability directive before upgrade result prose.

### UPDATED: skills/voter-calibration/SKILL.md

Add a public-skill readability directive before diagnostic report prose.

### UPDATED: .claude/skills/agnix-fix/SKILL.md

Add a dev-only readability directive using `$PWD/skills/shared/readability-style.md`.

### UPDATED: .claude/skills/analyze-issues/SKILL.md

Add a dev-only readability directive before analysis report prose.

### UPDATED: .claude/skills/audit-runs/SKILL.md

Add a dev-only readability directive before audit report and follow-up prose.

### UPDATED: .claude/skills/combine-issues/SKILL.md

Add a dev-only readability directive before combination proposal prose.

### UPDATED: .claude/skills/larch-size/SKILL.md

Add a dev-only readability directive, or explicitly confirm output is pure pass-through and list it as an exemption only if no prose is composed.

### UPDATED: .claude/skills/rebalance-tests/SKILL.md

Add a dev-only readability directive before verification and PR prose.

### UPDATED: .claude/skills/release/SKILL.md

Add a dev-only readability directive before release preview and approval prose.

### UPDATED: python/larch/design/design_step2b.py

Read the shared style file when assembling Step 2b drafter prompts.

### UPDATED: python/larch/rendering/rendering.py

Change the default readability style path to `skills/shared/readability-style.md`.

### UPDATED: python/larch/lint/lint_readability_preamble.py

Extend the lint:
- Parse manifest metadata rows for the expected-count floor.
- Parse optional skill-exemption rows with reasons.
- Sum manifest expected counts and fail below the committed floor.
- Walk public and dev-only `SKILL.md` files.
- Require each skill to have the right path form or a manifest exemption.
- Fail if a new skill is neither wired nor explicitly exempt.
- Preserve existing exact-count and step-placement checks.

### UPDATED: python/tests/lint/test_lint_readability_preamble.py

Add tests for:
- floor pass and fail.
- public skill path form.
- dev-only skill path form.
- missing per-skill directive.
- explicit exemption behavior.
- restored Step 2b placement.
- invalid manifest metadata or exemption rows.
- Update ORCH-style fixtures that pin the old design-scoped path to the shared path.

### UPDATED: scripts/lint-readability-preamble.tsv

Repoint current rows to the shared path. Raise the restored `/design` composition-site rows explicitly: `skills/design/SKILL.md` from 0 to 1 (Step 2b anchor), `skills/design/references/design-outline.md` from 0 to 1, and `skills/design/references/finalize-step5.md` from 0 to 1. Set the finalize row to 2 only if the implementation restores two distinct anchors there. Add rows for `/implement` and all other public and dev-only skills. Add the committed floor metadata row. Add no exemption rows unless inspection proves a pure redirect with no user-facing prose.

### UPDATED: scripts/lint-readability-preamble.tsv.md

Document metadata rows, skill exemption rows, floor semantics, path-form checks, and dynamic skill coverage.

### UPDATED: scripts/test-design-structure.sh

Update the harness in the same edit that rewrites the /design files, so a correct shared-path MANDATORY update cannot fail tests:
- Replace the finalize-step5 `contains` needle (old soft-read wording) with the new shared-path MANDATORY directive text, or with a lint-aligned counted-suffix substring check.
- Align the finalize-step5 once-count grep with the new wording and the restored anchor count.
- Drop the `not_contains` prohibition that forbids readability anchors in `skills/design/SKILL.md`.
- Add a positive assertion for the restored Step 2b anchor where useful.

### UPDATED: skills/design/scripts/test-brainstorm-prompts.sh

Repoint the path pin to the shared readability file.

### UPDATED: skills/design/scripts/test-brainstorm-prompts.md

Update the harness description for the shared path.

### UPDATED: python/larch/implement/checks_run_relevant.py

Add direct relevant-check routing so changes to the readability lint, manifest, or shared style file run `test-lint-readability-preamble` and relevant structural tests.

### UPDATED: python/tests/rendering/test_rendering.py

Update any default-path expectations or fixtures that mention the old readability location.

### UPDATED: python/test_fixtures/plan-fidelity-calibration/diffs/3ED15A95-C722-4ABE-904C-729E1A730C5D_FINDING_10.diff

Repoint stored readability path references if this fixture is still compared byte-for-byte.

### UPDATED: python/test_fixtures/plan-fidelity-calibration/diffs/66A96EAD-3088-4750-AE3A-64A0E11EABBD_FINDING_10.diff

Apply the same conditional repoint to this second calibration fixture only if it is treated as a live referrer.

### UPDATED: python/skill-closure-baseline.json

Refresh only if skill-closure lint grows from the intentional directives in `design`, `implement`, or `review`.

### MAY_UPDATE: Makefile

Keep existing lint target names if possible. Update only if the lint or test target wiring changes.

## Edge cases

- New skills must fail lint until they add a directive or an exemption row.
- Every manifest `orchestrator-inline` site with `expected_count` above zero must use the counted MANDATORY anchor form: the directive line contains the backticked readability path whose closing backtick is immediately followed by `.**`. The path inside the backticks may be `${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md` (public) or `$PWD/skills/shared/readability-style.md` (dev-only). Soft `Read ...` prose lines and backtick-only paths do not satisfy the counter.
- Dev-only skills must not use `${CLAUDE_PLUGIN_ROOT}` in their readability directive.
- Public skills and public references must not use bare repo-relative readability paths.
- Machine output such as KVs, plan grammar, vote tables, and sentinels must stay byte-stable.
- Historical fixture diffs may be intentionally historical. Update only if tests or grep-clean requirements treat them as live referrers.
- `settle-rc-dispatch.md` should stay unwired if it does not compose user-facing prose.

## Failure modes

- Exact-count lint can fail if a file gains both entry and local anchors without a manifest count update.
- Tier-1a lint can fail if `AGENTS.md` grows past 89 lines. Prefer replacement over added lines.
- Skill-closure growth can fail after adding directives to ratcheted skills. Refresh the baseline only for intentional growth.
- Consumer installs can fail to resolve bare paths. All public directives must use `${CLAUDE_PLUGIN_ROOT}`.
- Over-wiring external prompts can violate the non-goal. Do not add `<READABILITY_STYLE>` outside current `/design` prompt surfaces.

## Testing strategy

- Run `python3 python/cli.py lint readability-preamble`.
- Run `make test-lint-readability-preamble`.
- Run `make test-design-structure`.
- Run `make test-brainstorm-prompts`.
- Run `make lint-tier1a-size`.
- Run `python3 python/cli.py lint skill-closure-growth`.
- Run `python3 python/cli.py checks run-relevant --site readability-style --tmpdir <tmpdir>` if available in the implementation environment.
- Run targeted Python tests touched by rendering or relevant-check routing:
  - `python3 -m pytest python/tests/rendering/test_rendering.py -q`
  - `python3 -m pytest python/tests/lint/test_lint_readability_preamble.py -q`

## Acceptance

- Readability-preamble lint passes with restored `/design` counts, catalog coverage rows, the exempt list, and the floor assertion.
- Every `skills/*/SKILL.md` and `.claude/skills/*/SKILL.md` carries a readability directive or an explicit exemption.
- Public-skill directives use `${CLAUDE_PLUGIN_ROOT}` paths; dev-only directives use `$PWD` paths.
- AGENTS.md Output Style points at the shared file; the tier1a-size lint passes.
- `scripts/test-design-structure.sh` and the other touched structural harnesses are updated and green.

mechanical_churn: true
diff_lines: 520

## Test plan
(no test plan section in plan-file)
