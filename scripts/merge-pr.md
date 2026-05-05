# merge-pr.sh

Squash-merges a PR via `gh pr merge`, with a re-verified `--admin`-first path and plain-merge fallback when the privileged attempt is rejected. The canonical `--admin` implementation in this repo — see `skills/implement/SKILL.md` Step 12b for the orchestrator-side contract.

## Usage

```
scripts/merge-pr.sh --pr NUMBER --repo OWNER/REPO [--no-admin-fallback]
```

Emits `MERGE_RESULT=...` and `ERROR=...` on stdout via an EXIT trap. Exits 0 unconditionally on usage success (the outcome is in `MERGE_RESULT`); exits 1 only on argument-validation errors.

## MERGE_RESULT enum

| Value | Meaning |
|-------|---------|
| `merged` | Plain squash merge succeeded. In default mode this means the prior `--admin` attempt failed and the plain fallback succeeded; with `--no-admin-fallback`, this means the only merge attempt succeeded. |
| `admin_merged` | CI re-verified green + branch fresh; `--admin` merge succeeded. **Only emitted when `--no-admin-fallback` is NOT set.** |
| `main_advanced` | Pre-merge gate found that the branch is behind main, or found a non-admin-eligible merge state. Caller should rebase and retry. |
| `ci_not_ready` | Pre-merge gate did not find all checks passing. Caller should poll CI. |
| `admin_failed` | Default-mode `--admin` attempt failed and the plain fallback also failed. Hard error. |
| `policy_denied` | CI re-verified green + branch fresh (admin-eligible); `--no-admin-fallback` is set, so `--admin` was NOT invoked, and the plain merge attempt failed. Caller should bail to manual reviewer-approval flow. |
| `error` | Catch-all unexpected failure. Also covers the case where `gh pr view --json mergeStateStatus` returns empty (API/network/`gh` failure) or `UNKNOWN` — the script cannot determine merge state, so it short-circuits with `error` rather than mis-routing to `main_advanced`. |

## --no-admin-fallback

When set, the script reaches the same admin-eligible gate (CI good + branch fresh) but invokes only `gh pr merge --squash`; if that plain merge fails, it emits `MERGE_RESULT=policy_denied` instead of invoking `gh pr merge --squash --admin`. This is opt-out: the default behavior (no flag) is to try `--admin` first, then retry without `--admin` if the privileged attempt is rejected.

The flag applies to **all admin-eligible mergeStateStatus values** — `CLEAN`, `UNSTABLE`, `HAS_HOOKS`, and `BLOCKED`. Any state where default mode would have tried `--admin` first becomes a plain-only merge path when the flag is set; this is broader than just review-required denials. Document this in caller-side flag specs so operators understand the scope.

`ERROR` on the `policy_denied` path is a fixed string: `"branch protection denied merge; --no-admin-fallback set"`. The orchestrator surfaces this verbatim as `FINAL_BAIL_REASON` when bailing to Step 12d.

## Safety invariant

`--admin` overrides ALL branch protection rules, including review-required policies. The script enforces a re-verification gate before the privileged path:

1. All CI checks must have `bucket == "pass"` (verified via `gh pr checks --json`).
2. `mergeStateStatus` must be `CLEAN`, `UNSTABLE`, `BLOCKED`, or `HAS_HOOKS` (NOT `BEHIND`, `DIRTY`, `DRAFT`, or `UNKNOWN`).

Both gates are checked **before** any merge attempt: default-mode `--admin`, default-mode plain fallback, or the `--no-admin-fallback` plain-only attempt. The `--no-admin-fallback` opt-out is not a way to skip the safety invariant — it is a way to decline the override that the safety invariant has already approved.

## Non-responsibilities

This script does NOT post audit comments, Slack messages, or any human-facing observability about the bypass. The orchestrator (`skills/implement/SKILL.md` Step 12b's `admin_merged` branch) is responsible for posting a best-effort PR comment recording the bypass when `--admin` actually succeeds. Keeping audit side effects out of this script preserves the narrow `MERGE_RESULT`/`ERROR` stdout contract that callers parse.

## Edit-in-sync rules

- When the `MERGE_RESULT` enum changes, update both this file's enum table and `skills/implement/SKILL.md` Step 12b's parse table in the same PR.
- When `--no-admin-fallback` semantics change (e.g., the gate set, the `ERROR` text), update `skills/implement/SKILL.md` flag spec, `skills/fix-issue/SKILL.md` flag forwarding, and `docs/configuration-and-permissions.md`.
- When default `--admin` ordering changes, update `skills/implement/SKILL.md` Step 12b, `docs/configuration-and-permissions.md`, and `docs/skills.md`.
- The script's header comment also documents the enum and flag — keep it byte-aligned with this file's "MERGE_RESULT enum" table.

## Test harness

Validation is via:
- `bash scripts/test-merge-pr.sh` for offline merge-order and gate regressions.
- `make lint` (shellcheck plus the Makefile-wired harness).
- Manual integration testing on a real PR for new GitHub CLI behavior changes.
