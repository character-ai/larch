## Goal
Implement issue #4542: [IMPLEMENTING] Add a rule that every larch script from now on should be in Python, except for thin wrappers.

## Implementation Plan
## Plan

Add a docs-only policy with three linked surfaces. Reconcile the standing **No shims** migration rule with the new forward-looking thin-wrapper allowance so migration cutover and new glue wrappers are not read as contradictory.

- Keep the rule **forward-looking**.
- Allow Bash only for:
  - thin wrappers that set up environment and delegate to `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py"`.
  - Claude Code hooks.
  - pre-commit and CI glue (documented in policy text; not a path-trigger surface).
- Do not add mechanical lint.
- Do not migrate existing Bash scripts.

## Files to modify/create

### UPDATED: AGENTS.md

Add one bullet under `## Conventions`.

Content intent:

- New larch scripts should be Python by default.
- All new logic belongs in `python/` behind `python3 python/cli.py`.
- Bash is allowed only for thin delegation wrappers (environment setup plus delegate to `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" <domain> <verb> [args...]`), Claude Code hooks, and pre-commit or CI glue.
- State explicitly that permitted thin wrappers are **forward-looking glue only**; they are **not** migration cutover shims. Migration/voluntary ports must repoint consumers to direct `cli.py` calls per `docs/python-migration.md` (see **No shims** there).
- Point to `docs/python-migration.md` and `.claude/rules/python-first-scripts.md`.

### NEW: .claude/rules/python-first-scripts.md

Add a path-triggered Claude Code rule modeled on `.claude/rules/shell-strict-mode.md`.

Use frontmatter paths (match `shell-strict-mode.md`; **do not** include workflow YAML):

- `scripts/**/*.sh`
- `skills/**/scripts/**/*.sh`
- `.claude/skills/**/scripts/**/*.sh`
- `hooks/**/*.sh`

Rule content:

- State that new larch script logic should be Python.
- Permit Bash thin wrappers only when they set up environment and delegate to `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" <domain> <verb> [args...]` (no direct `python/<module>.py` invocation from wrappers).
- Preserve exceptions for Claude Code hooks and pre-commit or CI glue (describe in rule body; no `.github/workflows` path trigger).
- State that existing Bash is not automatically in scope.
- Distinguish permitted forward-looking glue wrappers from migration cutover shims: during sh-to-py migration, consumers must call `cli.py` directly; do not add forwarding `.sh` stubs (cross-link `docs/python-migration.md` **No shims** and recipe step 4).
- Link to `docs/python-migration.md` and `AGENTS.md`.

### UPDATED: docs/python-migration.md

Two edits in `## Decision log`:

1. **Amend the existing `No shims` bullet** (do not leave the standing "ever" wording unreconciled). Scope it to **migration/voluntary-port cutover only**:
   - When retiring a bash domain, repoint all consumers to `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" <domain> <verb> [args...]` directly.
   - Do not add intermediate `.sh` forwarding stubs as migration cutover aids; delete retired bash per recipe steps 4–6.
   - State that this prohibition does **not** forbid forward-looking thin glue wrappers governed by the new Python-first policy (thin env-plus-`cli.py` delegation wrappers, hooks, pre-commit/CI glue only).

2. **Add a new decision-log bullet** (after the amended **No shims** line or adjacent to it):
   - Forward-looking Python-first policy for new larch scripts.
   - Restate allowed Bash exceptions using the same three categories on all surfaces: thin env-plus-`cli.py` delegation wrappers, hooks, pre-commit/CI glue.
   - Cross-link `AGENTS.md`, `.claude/rules/python-first-scripts.md`, and recipe **step 4** ("Cut ALL consumers to direct `cli.py` calls") so readers see cutover semantics and glue-wrapper permissions as complementary, not conflicting.
   - Preserve existing migration recipe semantics for voluntary ports.

## Edge cases

- Do not phrase the rule as a ban on editing existing Bash.
- Do not conflict with `Hooks stay bash`.
- Do not weaken migration discipline: **No shims** remains absolute for cutover stubs; thin wrappers are only for new forward-looking glue that delegates through `cli.py`, not as migration forwarding files.
- Do not bless a second entrypoint: wrappers must not call `python/<module>.py` directly.
- Do not add `.github/workflows/**/*` to the rule `paths:` frontmatter; CI glue exception belongs in policy prose only (AGENTS.md, rule body, decision log).

## Failure modes

- Overbroad wording could make existing Bash look non-compliant.
- Leaving **No shims** unamended while adding wrapper permissions recreates contradictory guidance and encourages cutover shims.
- Naming extra Bash categories on one surface but not the others (for example orchestration launchers in the decision log but not in AGENTS or the rule) ships conflicting guidance.
- A lint rule would violate the documentation-only scope.
- A new rule that omits `hooks/**/*.sh` may hide the hook exception at the edit point.
- Broadening rule paths to workflow YAML adds noise on non-script edits.

## Testing strategy

- Run `make lint`.
- Do not run `make py-lint` or `make py-test`; no Python files change.

## Acceptance

- `AGENTS.md` "Conventions" section gains one bullet: new larch scripts are Python by default; new logic lives in `python/` behind `python3 python/cli.py`; Bash is allowed only for thin delegation wrappers, Claude Code hooks, and pre-commit or CI glue. The bullet states the wrappers are forward-looking glue, not migration cutover shims, and links `docs/python-migration.md` and `.claude/rules/python-first-scripts.md`.
- `.claude/rules/python-first-scripts.md` exists with `paths:` frontmatter matching `.claude/rules/shell-strict-mode.md` (`scripts/**/*.sh`, `skills/**/scripts/**/*.sh`, `.claude/skills/**/scripts/**/*.sh`, `hooks/**/*.sh`; no workflow YAML). Its body states the Python-first policy, permits Bash thin wrappers that delegate to `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py"` only, preserves the hooks and pre-commit/CI-glue exceptions in prose, notes existing Bash is not auto-in-scope, distinguishes glue wrappers from migration cutover shims, and links `docs/python-migration.md` and `AGENTS.md`.
- `docs/python-migration.md` "Decision log": the `No shims` bullet is amended to scope the prohibition to migration/voluntary-port cutover and to state it does not forbid forward-looking thin glue wrappers; a new bullet states the forward-looking Python-first policy, restates the three Bash exceptions, and cross-links `AGENTS.md`, `.claude/rules/python-first-scripts.md`, and recipe step 4.
- The three surfaces use the same three Bash-exception categories and do not contradict each other or the existing `Hooks stay bash` decision.
- No new lint, runtime, or skill behavior is added; no existing Bash script is migrated.
- `make lint` passes.

diff_lines: 54

## Test plan
(no test plan section in plan-file)
