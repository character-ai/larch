## Goal
Delete 6 larch skills (skill-evolver, simplify-skill, show-skill, compress-skill, create-skill, umbrella) and all their tests, docs, and runtime references.

## Implementation Plan
## Plan

Delete 6 larch skills (skill-evolver, simplify-skill, show-skill, compress-skill, create-skill, umbrella) including their directories, tests, and documentation. Update runtime references so no live consumer of the deleted skills remains. Leave CHANGELOG.md entries and `larch-logs/` run records intact as historical artifacts. Replace `/review` description-mode auto-issue-filing (which went through `/umbrella`) with no-op + manual /issue follow-up.

Two scope decisions framing this plan:
- **Runtime refs only**: scrub references in runtime files; leave CHANGELOG.md and `larch-logs/` untouched.
- **Scrub umbrella broadly**: remove `/umbrella` prose from SECURITY.md and /issue scripts; keep /issue's `--blocked-by-issue` flag (caller-agnostic) but remove `/umbrella`-specific prose.

### Files to delete (entire trees)

```
skills/skill-evolver/      (SKILL.md + scripts/validate-args.{sh,md})
skills/simplify-skill/     (SKILL.md + scripts/build-feature-description.{sh,md})
skills/show-skill/         (SKILL.md + scripts/{show.{sh,md}, test-show-skill.{sh,md}})
skills/compress-skill/     (SKILL.md + scripts/{build-feature-description.{sh,md}, discover-md-set.{sh,py}})
skills/create-skill/       (SKILL.md + scripts/parse-args.{sh,md} + prepare-description.{sh,md} + post-scaffold-hints.{sh,md} + render-skill-md.{sh,md} + test-render-skill-md.{sh,md} + validate-args.sh)
skills/umbrella/           (SKILL.md + 24 scripts/* files: helpers.{sh,md}, parse-args.{sh,md}, render-batch-input.{sh,md}, render-umbrella-body.{sh,md}, validate-pieces-json.{sh,md}, test-helpers.{sh,md}, test-render-batch-input.{sh,md}, test-render-umbrella-body.{sh,md}, test-umbrella-blocked-by-issue.{sh,md}, test-umbrella-emit-output-contract.{sh,md}, test-umbrella-parse-args.{sh,md}, test-validate-pieces-json.{sh,md})
```

Top-level test harnesses (test deleted skills):
- `scripts/test-post-scaffold-hints.{sh,md}` (tests create-skill)
- `scripts/test-prepare-description.{sh,md}` (tests create-skill)
- `scripts/test-parse-args.{sh,md}` (tests create-skill)

### Files to modify

**Runtime configuration:**
- `.claude/settings.json` — remove permission entries for the 6 skills (14 lines: Bash entries 11–12, 17–19; Skill entries 160–161, 169–170, 179–182, 189–191, 194).
- `agent-lint.toml` — remove allowed-path entries (525, 1067, 1075, 1126); update comments at 79–90, 164 (trim "im, imaq, create-skill, simplify-skill, compress-skill" → "im, imaq"), 866, 873, 1068. KEEP GitHub-issue umbrella refs at lines 286, 896, 975.
- `Makefile` — remove targets `test-post-scaffold-hints`, `test-prepare-description`, `test-parse-args`, `test-render-skill` (TWO recipe lines: one create-skill, one show-skill), `test-show-skill`, `test-umbrella-helpers`, `test-umbrella-parse-args`, `test-umbrella-blocked-by-issue`, `test-umbrella-emit-output-contract`, `test-umbrella-render-batch-input`, `test-render-umbrella-body`, `test-validate-pieces-json`. Remove from `.PHONY` and shard prerequisite lists (test-harnesses-5/6/7/8/9/10/13/15/18). Run `make test-harness-shards-coverage` after edits.

**Documentation:**
- `README.md` — remove 6 skill table rows; update `/review` row to drop `(--no-issues to suppress)` parenthetical.
- `docs/skills.md` — remove 6 TOC entries + 6 sections; update `/review` description-mode entry to drop `--no-issues` framing.
- `docs/installation-and-setup.md` line 200 — remove `/create-skill`, `/simplify-skill`, `/compress-skill` from skill list.
- `docs/configuration-and-permissions.md` — remove 10 permission-entry rows; update line 48 ordering note; delete "Implication for the umbrella stall (issue #566)" section (lines 85–87).
- `docs/linting.md` — update `test-analyze` description at line 190 (KEEP `Tracking/umbrella` label; drop /umbrella-as-creator framing); delete `test-umbrella-*` and `test-render-umbrella-body` target-description rows (273–278). KEEP Makefile umbrella refs at 39/136/139.
- `docs/workflow-lifecycle.md` — major rewrite: remove `/skill-evolver` orchestrator + edges (7/17/18/34); drop the 4 delegator description blocks (58/60/61/62) and parenthetical (64); delete `/show-skill` + `/skill-evolver` from Standalone Usage (114/116); drop `--no-issues` from `/review` Standalone Usage entry.

**Shared docs:**
- `skills/shared/voting-protocol.md` — remove `/umbrella` filer phrases at lines 241, 286 (replace with `/implement` Step 9a.1 only).
- `skills/shared/subskill-invocation.md` — drop /create-skill, /simplify-skill, /compress-skill examples + delegator-list entries (11, 21, 46, 55, 90, 139–141); update closing paragraph at line 243.
- `skills/shared/skill-design-principles.md` — drop /create-skill cited-by callouts (3, 37, 123).

**Other skills:**
- `skills/review/SKILL.md` line 55 — drop /umbrella invocation + pieces.json composition + `--no-issues` flag. Keep security-tagged findings holding-local behavior.
- `skills/issue/scripts/create-one.sh` line 189 — delete `# /umbrella forwards ...` comment.
- `skills/issue/scripts/create-one.md` line 5 — replace /umbrella sentence with neutral acknowledgment that caller-supplied labels may contain regex metacharacters.
- `skills/issue/scripts/parse-input.md` lines 15–27 — delete `## Reverse coupling: /umbrella's piece bodies (#831)` subsection.
- `skills/alias/scripts/resolve-target.sh` line 16 — drop create-skill cross-reference comment.
- `skills/alias/scripts/resolve-target.md` line 47 — inline the two-file rule description (was cross-reference to create-skill).

**SECURITY.md:**
- Line 152 — remove `skills/skill-evolver/SKILL.md` from `/research --no-issue` transitive callers.
- Lines 154–156 — delete `### /umbrella --blocked-by-issue` subsection.
- Line 166 — drop `/umbrella` sentence in create-one.sh:182 bullet.
- Lines 167–169 — delete 3 `skills/umbrella/scripts/helpers.sh` wire-dag bullets.

**Scripts:**
- `scripts/test-anti-halt-banners.sh` lines 48–50 — remove 3 entries from `DELEGATORS=()` array.
- `scripts/test-review-structure.sh` lines 370–385 — delete test case (18) (`--pieces-json` /umbrella assertion).
- `scripts/blocker-helpers.sh` line 5 — remove `skills/umbrella/scripts helpers, ` from caller list.
- `scripts/repro-claude-p-edit-permissions.sh` line 41 — change `EDIT_TARGET="skills/umbrella/SKILL.md"` → `"skills/issue/SKILL.md"`.
- `scripts/repro-claude-p-edit-permissions.md` lines 19/49/70/91/115 — same substitution.

### Files NOT to touch (historical / non-relevant)

- `CHANGELOG.md`, `larch-logs/**` (immutable history).
- `scripts/test-harness-shards-coverage.sh` (Makefile umbrella target, not /umbrella skill).
- `skills/research/scripts/test-validate-citations.md:60`, `skills/issue/scripts/test-{intra-batch-deps,body-file-title,blocked-by-issue}.md:5` (Makefile umbrella references).
- `skills/implement/SKILL.md:30`, `agent-lint.toml` lines 286/896/975 (GitHub-issue umbrella references).
- `.claude/skills/analyze-issues/scripts/{analyze.py:266, test-analyze.{sh,md}}` ("Tracking/umbrella" issue category for historical issues).

### Approach

6 phases: (1) bulk deletes; (2) runtime configs (.claude/settings.json, agent-lint.toml, Makefile); (3) docs (README, docs/*); (4) shared + cross-skill refs (skills/shared/*, /review, /issue, /alias, SECURITY.md); (5) test harnesses + reproducer; (6) verify via make lint + make test-harness-shards-coverage + targeted manual smoke-tests.

### Edge cases

- Makefile shard rebalancing is optional (coverage harness checks single-shard membership, not balance).
- `/review` description-mode auto-issue-filing is removed (direct consequence of "scrub umbrella broadly").
- `/issue --blocked-by-issue` flag kept (caller-agnostic).
- Plugin permission caching: `.claude/settings.json` changes apply on next session.
- `/im` and `/alias` skills survive; their create-skill cross-references are updated inline.

### Failure modes

1. Missed reference → broken cross-link or stale agent-lint allow-list path. Mitigated by Phase 6 invariant grep + `make lint`.
2. Makefile shard imbalance breaks `test-harness-shards-coverage`. Mitigated by per-edit coverage check.
3. `/review` description-mode runtime failure if SKILL.md half-updated. Mitigated by same-commit update + `make test-review-structure`.

### Testing strategy

- After each phase: `make lint` (shellcheck/markdownlint/jsonlint/actionlint/agent-lint/agnix/gitleaks/trufflehog).
- `make test-harness-shards-coverage` post-Makefile edit.
- `make test-review-structure` + `make test-anti-halt` post-Phase 5.
- Manual smoke tests of `/issue` (label probe path) and `/alias` (two-file rule).
- Final invariant grep: `git grep -E 'skill-evolver|simplify-skill|show-skill|compress-skill|create-skill|/umbrella|skill:umbrella|larch:umbrella'` (excluding CHANGELOG.md and larch-logs/) returns zero matches.

## Acceptance

- All 6 skill directories (`skills/{skill-evolver, simplify-skill, show-skill, compress-skill, create-skill, umbrella}/`) are removed.
- The 3 top-level test harnesses (`scripts/test-{post-scaffold-hints, prepare-description, parse-args}.{sh, md}`) are removed.
- `.claude/settings.json`, `agent-lint.toml`, `Makefile` no longer contain any permission entries, allowed-paths, targets, .PHONY entries, or shard prerequisites referencing the 6 skills.
- `README.md`, `docs/skills.md`, `docs/installation-and-setup.md`, `docs/configuration-and-permissions.md`, `docs/linting.md`, `docs/workflow-lifecycle.md` no longer reference the 6 skills (table rows, TOC entries, sections, permission examples, target-description rows deleted; `/review --no-issues` flag prose cleaned up).
- `skills/shared/{voting-protocol, subskill-invocation, skill-design-principles}.md`, `skills/review/SKILL.md`, `skills/issue/scripts/{create-one.{sh,md}, parse-input.md}`, `skills/alias/scripts/resolve-target.{sh,md}`, `SECURITY.md` no longer reference the 6 skills.
- `scripts/{test-anti-halt-banners.sh, test-review-structure.sh, blocker-helpers.sh, repro-claude-p-edit-permissions.{sh,md}}` no longer reference the 6 skills.
- `make lint` passes cleanly (shellcheck, markdownlint, jsonlint, actionlint, agent-lint, agnix, gitleaks, trufflehog).
- `make test-harness-shards-coverage` passes.
- `make test-review-structure` and `make test-anti-halt` pass.
- `git grep -E 'skill-evolver|simplify-skill|show-skill|compress-skill|create-skill|/umbrella|skill:umbrella|larch:umbrella'` (excluding `CHANGELOG.md` and `larch-logs/`) returns zero matches.
- `CHANGELOG.md` and `larch-logs/` are unmodified (historical preservation invariant).
- Manual smoke tests of `/issue` single-mode and `/alias` succeed without runtime errors.

diff_lines: 1050

## Test plan
(no test plan section in plan-file)
