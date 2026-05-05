# scripts/session-entry-gate.sh — contract

`scripts/session-entry-gate.sh` is the pure Step 0 policy helper for `/implement` and `/design`. It turns branch facts from `scripts/create-branch.sh --check` plus the caller mode into a deterministic `ENTRY_GATE=strict|continue` and the caller-critical `SKIP_BRANCH_CHECK=true|false` flag. It has no side effects: no git reads, no preflight call, no temp-directory creation, and no `session-setup.sh` invocation.

## Inputs

- `--mode implement|design` is required.
- `--current-branch <string-or-empty>` is required. An explicit empty value is allowed for detached HEAD; omitting the flag is not allowed.
- `--is-main true|false` is required.
- `--is-user-branch true|false` is required.
- `--user-prefix <non-empty-string>` is required and must be non-empty.
- `--branch-info-supplied true|false` is design-only. Any occurrence with `--mode implement` is a contract violation, regardless of value.

The script validates required-flag presence before value content where possible, so a missing required flag produces `GATE_ERROR=missing required flag --flag` instead of a shell nounset trace.

## Outputs

On success, stdout is exactly two lines and stderr is empty:

```text
ENTRY_GATE=strict
SKIP_BRANCH_CHECK=false
```

```text
ENTRY_GATE=continue
SKIP_BRANCH_CHECK=true
```

On failure, stdout is empty and stderr contains one `GATE_ERROR=...` line:

```text
GATE_ERROR=missing required flag --current-branch
```

`SKIP_BRANCH_CHECK` is the authoritative caller-critical key for `session-setup.sh` argv assembly. `ENTRY_GATE` is diagnostic policy labeling. Today `SKIP_BRANCH_CHECK=true` iff `ENTRY_GATE=continue`; the harness asserts that equivalence on every success row, but callers should still branch on `SKIP_BRANCH_CHECK`.

## Exit Codes

- `0` — success; decision printed on stdout.
- `4` — invalid arguments or caller contract violation; `GATE_ERROR` printed on stderr.

## Decision Table

| Mode | `is_user_branch` | `branch_info_supplied` | Decision |
|------|------------------|------------------------|----------|
| `implement` | `true` | not accepted | `continue` |
| `implement` | `false` | not accepted | `strict` |
| `design` | `true` | `false` | `continue` |
| `design` | `false` | `false` | `strict` |
| `design` | `true` or `false` | `true` | `continue` |

## Invariants

`--issue <N>`, `SESSION_ENV_PATH`, and any sentinel file never waive the gate. The helper does not accept or read those inputs.

Detached HEAD reports `IS_MAIN=true` with empty `CURRENT_BRANCH`; continuation is never keyed on `IS_MAIN=false` or on a non-empty current branch. Only `IS_USER_BRANCH=true` or `/design`'s `branch_info_supplied=true` path opts into continuation, so detached HEAD falls through to `strict` and `preflight.sh` fails closed.

`--current-branch` and `--user-prefix` echo `create-branch.sh --check` output for audit context and forward compatibility. The decision policy does not consume them today; a future version may add a consistency check such as `is_user_branch=true` requiring `current_branch` to start with `user_prefix/`.

Caller parsing rule: parse this script's stdout in isolation; do not concatenate it with `create-branch.sh --check` output for a single `eval`.

## Callers

- `skills/implement/SKILL.md` Step 0
- `skills/design/SKILL.md` Step 0

## Test Harness

`scripts/test-session-entry-gate.sh` exercises the success and failure matrix offline. It invokes this helper directly via path at least once so the executable bit is part of the contract.

## Edit In Sync

When this script's CLI, outputs, policy, or error strings change, update:

- `skills/implement/SKILL.md` Step 0
- `skills/design/SKILL.md` Step 0
- `scripts/test-session-entry-gate.sh`
- `scripts/test-session-entry-gate.md`
- `scripts/test-implement-structure.sh`
- `scripts/test-design-structure.sh`
- `Makefile`
- `agent-lint.toml` excludes if reachability changes
