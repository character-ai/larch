## Goal
Reduce multi-flag SKILL.md Bash blocks to ≤2-flag launcher calls

## Implementation Plan
Encapsulate the top-3 highest-blast-radius SKILL.md Bash blocks behind one-arg launcher scripts that derive flags from on-disk artifacts.


### Target 1: `scripts/run-step5-review.sh` (wraps 11-flag review-and-fix.sh in SKILL.md Step 5)

Create launcher that takes only `--implement-tmpdir PATH` and `--round-num N`.

Derives from `$IMPLEMENT_TMPDIR/session-env.sh`:
- `POST_PLAN_WORKFLOW_PATH` → `PANEL` (SIMPLE→simple, HARD→hard) and `ROUND_CAP` (SIMPLE→5, HARD→7)
- `CODEX_PRESENT` → `--codex-available`
- `CURSOR_PRESENT` → `--cursor-available`
- `PLAN_FILE` → `--plan-file`

Derives from tmpdir:
- `session-id` → `RUN_ID`
- `feature-description.txt` path (conventional)
- `session-env.sh` path (conventional)

Hardcodes: `--mode diff`

### Target 2: `scripts/run-step1-plan-log.sh` (wraps compose-plan-goals-test.sh + larch-log.sh write in SKILL.md Step 1)

Create launcher that takes only `--implement-tmpdir PATH` and `--goal-text TEXT`.

Derives from `$IMPLEMENT_TMPDIR/session-env.sh`:
- `PLAN_FILE` → compose-plan-goals-test.sh `--plan-file`
- `LARCH_CLAUDE_PLUGIN_ROOT` → script paths

Derives from tmpdir:
- `session-id` → `RUN_ID` (for larch-log.sh write `--run-id`)

Hardcodes: `--skill implement`, `--batch plan-goals-test`, output path `$IMPLEMENT_TMPDIR/plan-goals-test.md`

### Target 3: `skills/implement/scripts/run-step2-dispatch.sh` (wraps 7-flag step2-implement.sh in SKILL.md Step 2)

First: Add `LARCH_AUTO_MODE=$auto_mode` append to session-env.sh in SKILL.md Step 0 (after write-session-env.sh call), using the established atomic append pattern.

Create launcher that takes only `--implement-tmpdir PATH` and `--coder CODER`.

Derives from `$IMPLEMENT_TMPDIR/session-env.sh`:
- `PLAN_FILE` → `--plan-file`
- `CURSOR_PRESENT` → `--cursor-present`
- `POST_PLAN_WORKFLOW_PATH` → `--workflow` (SIMPLE or HARD)
- `LARCH_AUTO_MODE` → `--auto-mode`

Derives from tmpdir:
- `feature-description.txt` path (conventional)

### SKILL.md changes (4 sites)

1. Step 0 (after write-session-env.sh): add 4-line LARCH_AUTO_MODE atomic append
2. Step 1 plan-goals-test block (2 commands): replace with run-step1-plan-log.sh (2 flags)
3. Step 2 step2-implement.sh invocation (7 flags): replace with run-step2-dispatch.sh (2 flags)
4. Step 5 review-and-fix.sh invocation (11 flags): replace with run-step5-review.sh (2 flags)

### Sibling .md contracts

Each new script gets a sibling .md documenting: purpose, caller, argv, derived sources, exceptions, harness path.

### Test harnesses

For each launcher, a test harness that:
1. Verifies required flags (exit 2 when missing)
2. Verifies correct flag derivation from mock session-env / tmpdir artifacts
3. Verifies the downstream script is invoked with the expected argv (via spy wrapper)

### Makefile

Add three new test targets and add them to an existing shard.


## Test plan

Run:
- `bash scripts/test-run-step5-review.sh`
- `bash scripts/test-run-step1-plan-log.sh`
- `bash skills/implement/scripts/test-run-step2-dispatch.sh`
- `make test-implement-structure` (checks SKILL.md structural assertions)
- `make lint` (markdownlint, agent-lint, pre-commit on modified files)
