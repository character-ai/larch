# Discussion Round 1 — Issue #6933

## Decision 1: Fix scope = full mutation-auth audit
- **Question**: Issue #6933 scopes to the shell helper being weaker than Python. The same #6896 `trusted_root` requirement also left two `design_terminal.py` callers fail-closed. How wide should the fix go?
- **Resolution**: **Full mutation-auth audit** (operator-selected). Fix the shell helper gap, fix the two fail-closed Python callers, and verify parity across every `check_live_mutation_auth` caller and every bash `gh`-mutation surface.
- **Source**: user

## Decision 2: Audit result — bounded surface set (codebase finding)
- **Question**: Which callers/surfaces are actually affected?
- **Resolution**: Only ONE bash `gh`-mutation surface exists (`scripts/file-failure-report-cross-repo.sh`). Python `check_live_mutation_auth` callers: `_report.py:472`, `_report.py:793`, `oos_filer.py:1115`, `issue_create.py:559` (callers pass authoritative `tmpdir`), and `audit_runs.py:1270` (operator-mode by design) are already authoritative — NO change. Two `design_terminal.py` callers (`:558` `_reconcile_post_recovery_comment`, `:926` tier-a dedup pre-check) omit `trusted_root` → fail-closed since #6896 — FIX. The shell helper's three Python invokers (`_report.py` ×2, `design_terminal.py:866`) must pass `--trusted-root`.
- **Source**: codebase

## Decision 3: Security bar = parity + non-circular trusted-root (hard constraint)
- **Question**: What is the correct security posture for the shell helper?
- **Resolution**: The shell helper must enforce the SAME rules as the Python checker with a NON-circular trusted-root pinned by the trusted Python caller (the authoritative session `tmpdir`). This eliminates the vacuous containment check (`trusted_root = dirname(context_file)` makes `ctx.parent == trusted_root` tautological) and hardens the confused-deputy case where `--mutation-context` is attacker-influenced: the caller-pinned root rejects a context file outside the real session. Resisting a fully-malicious direct caller who controls all argv+filesystem is beyond the call-chain trust model (the Python surface has the identical property) and is explicitly a NON-goal.
- **Source**: codebase

## Hard constraints (must not break)
- `session check-live-mutation-auth` CLI contract (`--context-file`, `--run-id`, `--trusted-root` all `required=True`) is unchanged.
- `check_live_mutation_auth(...)` signature unchanged; existing authoritative callers untouched.
- Bash 3.2 portability for the shell helper (no assoc arrays / namerefs / `&>>`).
- Fail-closed semantics preserved on refusal (status_refused / fallback reasons stay machine-parsed `KEY=value` grammar).
- `file-failure-report-cross-repo.sh` usage string and `*.md` contract stay in sync.

## Non-goals
- Redesigning the call-chain trust model or adding an unforgeable secret channel for run-id (out of scope; same residual as Python surface).
- Changing `audit_runs.close-priors` operator-mode gating.
- Broad refactor of stall-recovery tier filing beyond the auth pin.
