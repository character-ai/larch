## Plan

## Goal

Rename `/release`'s auto-confirm flag from `--approve`/`-a` to `--skip-approve`/`-s`.

Preserve behavior:

- Skip Step 4 `AskUserQuestion` only when `PR_COUNT>0`.
- Keep `PR_COUNT=0` default-to-Cancel prompt.
- Do not keep old `--approve`/`-a` as aliases.

## Approach

- Treat the approved outline as binding scope.
- Make the smallest prompt and docs change.
- Keep all release logic in `.claude/skills/release/SKILL.md`.
- Do not add Python parsing or release CLI changes.
- Rename the internal shell variable from `approve` to `skip_approve` to match the new public flag.
- Add explicit rejection for old `--approve` and `-a` tokens so they are not silently ignored or treated as compatibility aliases.

## Files to modify/create

### UPDATED: .claude/skills/release/SKILL.md

- Update frontmatter `argument-hint`:
  - From `[--approve|-a]`
  - To `[--skip-approve|-s]`
- Update the Flags table row:
  - From `` `--approve`, `-a` ``
  - To `` `--skip-approve`, `-s` ``
- In Step 1's Bash parser:
  - Rename `approve=false` to `skip_approve=false`.
  - Parse `--skip-approve|-s` to set `skip_approve=true`.
  - Add a fail-closed branch for retired `--approve|-a`.
  - Print a clear error telling the operator to use `--skip-approve` or `-s`.
  - Stop before release prepare when retired tokens appear.
- In Step 4 prose:
  - Replace `approve=true` with `skip_approve=true`.
  - Replace user-facing `--approve` mentions with `--skip-approve`.
  - Spell the ordered branch clearly:
    1. `--dry-run`: preview and exit.
    2. `skip_approve=true` and `PR_COUNT>0`: skip the prompt and proceed as Confirm.
    3. Otherwise fire `AskUserQuestion`, including `PR_COUNT=0` with `--skip-approve`.
- Keep the empty-window safety text explicit:
  - `PR_COUNT=0` must still show the prompt.
  - Default remains Cancel unless the operator explicitly chooses Confirm.

### UPDATED: docs/skills.md

- Update `/release` Arguments:
  - From `[--dry-run] [--approve|-a] [--bump major|minor|patch] [--repo OWNER/REPO]`
  - To `[--dry-run] [--skip-approve|-s] [--bump major|minor|patch] [--repo OWNER/REPO]`
- Update the `/release` description sentence:
  - Replace `--approve` with `--skip-approve`.
  - Preserve the non-empty release-window qualifier.

### UPDATED: README.md

- Update the `/release` feature-matrix Arguments cell:
  - From `[--dry-run] [--approve|-a] [--bump major|minor|patch] [--repo OWNER/REPO]`
  - To `[--dry-run] [--skip-approve|-s] [--bump major|minor|patch] [--repo OWNER/REPO]`

## Edge cases

- **`PR_COUNT=0` with `--skip-approve`**: must still prompt. Default stays Cancel.
- **`--dry-run --skip-approve`**: dry-run still previews and exits. No writes.
- **Old `--approve` or `-a`**: fail closed with a clear retired-flag error. Do not silently ignore.
- **Docs drift**: all public mentions in `README.md` and `docs/skills.md` must match the skill frontmatter.
- **Internal variable drift**: after renaming, no live `approve=true`, `approve=false`, or `approve` Step 4 condition should remain in `.claude/skills/release/SKILL.md`.

## Failure modes when non-trivial

- A silent old-flag ignore can confuse operators and make a release unexpectedly prompt.
- Keeping `approve=true` in Step 4 after renaming the parser variable can disable the skip path.
- Treating `--skip-approve` as unconditional can bypass the empty-window safety net.
- Updating docs but not frontmatter can make Claude Code's argument hint stale.

## Testing strategy

- Run targeted greps:
  - `grep -RIn -- "--approve\\|-a\\|skip-approve\\|-s" .claude/skills/release/SKILL.md docs/skills.md README.md`
  - Confirm only intentional retired-flag rejection text remains for `--approve` and `-a`.
- Run markdown and relevant checks for changed docs where available:
  - `python3 python/cli.py checks run-relevant`
- If relevant checks do not cover the private skill, also run:
  - `make lint-skill-md-flag-signature`
- Manually inspect `.claude/skills/release/SKILL.md` Step 1 and Step 4 to verify the ordered branch and zero-PR safety text.

## Acceptance

- Run targeted greps:
  - `grep -RIn -- "--approve\\|-a\\|skip-approve\\|-s" .claude/skills/release/SKILL.md docs/skills.md README.md`
  - Confirm only intentional retired-flag rejection text remains for `--approve` and `-a`.
- Run markdown and relevant checks for changed docs where available:
  - `python3 python/cli.py checks run-relevant`
- If relevant checks do not cover the private skill, also run:
  - `make lint-skill-md-flag-signature`
- Manually inspect `.claude/skills/release/SKILL.md` Step 1 and Step 4 to verify the ordered branch and zero-PR safety text.

review_status: ok
rounds_completed: 1
difficulty: MODERATE
diff_lines: 24
