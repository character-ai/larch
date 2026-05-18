# scripts/persist-post-plan-keys.sh — contract

Persists the post-plan router keys `PLAN_FILE`, `FEATURE_FILE`, and `POST_PLAN_WORKFLOW_PATH` into `$IMPLEMENT_TMPDIR/session-env.sh` atomically, then verifies the write before returning. Replaces the inline `grep -v` / append / `mv` shell snippets that the `/implement` orchestrator previously emitted at the Step 1 post-plan router (see issue #2326).

## Primary caller

`skills/implement/SKILL.md` § "Post-plan router" invokes this script exactly once per run, after `post-design-boundary.sh` has loaded `PLAN_FILE` (or after the manifest-reuse branch has bound it) and after the orchestrator has chosen the `SIMPLE` or `HARD` workflow path.

## Arguments

- `--implement-tmpdir PATH` — required, must be an existing directory containing `session-env.sh`.
- `--plan-file PATH` — required, must point to an existing non-empty file.
- `--feature-file PATH` — required, must point to an existing file.
- `--workflow-path SIMPLE|HARD` — required.

## Invariants

- Atomic temp+mv write: a tmp file is created next to `session-env.sh`, populated, then `mv`-renamed in place. Concurrent readers never observe a half-written file.
- The grep filter is anchored: `^PLAN_FILE=`, `^FEATURE_FILE=`, `^POST_PLAN_WORKFLOW_PATH=`. A looser pattern would strip unrelated keys (e.g., `LARCH_PLAN_FILE_HISTORY`).
- Newline / CR characters in argument values are rejected before write — those would corrupt the `KEY=VALUE` shape that `read-session-env-key.sh` and `session-setup.sh --caller-env` rely on.
- Post-condition: each of the three keys is read back via `read-session-env-key.sh` and asserted to equal the input. Mismatch is a fatal exit-2 with an actionable error naming the bad key. Without this assertion, a partial-write bug (the exact failure mode that motivated this script) would still slip past Step 1 and surface minutes later as "PLAN_FILE missing from session-env" at Step 5.

## Exit codes

- `0` — all three keys persisted and verified.
- `2` — usage error, validation failure, write failure, or post-condition failure.

## Stdout

On success:
```
POST_PLAN_KEYS_PERSISTED=true
PLAN_FILE=<path>
FEATURE_FILE=<path>
POST_PLAN_WORKFLOW_PATH=<SIMPLE|HARD>
```

## Harness

`scripts/test-persist-post-plan-keys.sh` (regression harness).

## Edit-in-sync

When changing argv validation, output grammar, or post-condition messages:

- `scripts/test-persist-post-plan-keys.sh` (regression harness).
- `skills/implement/SKILL.md` § "Post-plan router" (orchestrator caller).
- `AGENTS.md` and `skills/implement/SKILL.md` NEVER list — the contract that the orchestrator MUST NOT improvise prompt-side writes to `session-env.sh` remains paired with this script being the sanctioned writer for the three post-plan keys.
