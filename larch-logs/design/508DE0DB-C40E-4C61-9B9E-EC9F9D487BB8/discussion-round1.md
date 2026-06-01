## Decision 1: Verification / test scope
- **Question**: How should the fix be verified, given there is no offline harness for `upgrade-larch.sh` and the script is not source-safe (harnesses were intentionally removed in #3231)?
- **Resolution**: Static + manual only. Run `make lint` (incl. `lint-bash32`, `shellcheck`) plus a by-hand retention check with a throwaway cache dir. Do NOT add a committed offline harness and do NOT refactor the script to be source-safe in this issue.
- **Source**: user

## Decision 2: Defect scope (which defects to fix)
- **Question**: Should the issue's explicit "Out of scope" boundary (fix Defect A + B only, leave Defect C) be binding?
- **Resolution**: Expand scope. Fix Defect A (protect the running version dir) + Defect B (stamp every successful install) **and additionally** harden Defect C (the `has_stamp` ranking). This diverges from the issue's "Out of scope" list by operator choice.
- **Source**: user

## Decision 3: Defect C hardening form (hard constraint on ranking)
- **Question**: Must the design preserve #3174's ranking invariant — install stamps trusted over filesystem mtime, stamped dirs ranked above unstamped ones?
- **Resolution**: Preserve #3174. Harden Defect C additively via stamp-on-discovery backfill: when listing cached versions, write a persistent `.larch-installed-at` for any unstamped version dir derived from its filesystem mtime, so every dir becomes stamped and is ranked by real age. The `has_stamp`-first ranking is NOT reworked. Tradeoff accepted: backfill freezes a possibly-unreliable mtime for legacy dirs, which is strictly better than the status-quo "unstamped sorts dead-last".
- **Source**: user

## Decision 4: Keep-cap unchanged (hard constraint)
- **Question**: Does the fix change `keep_versions` (the retention cap)?
- **Resolution**: No. `keep_versions=8` stays. Retained-set size remains capped at 8 even with up to 2 pre-seeded protected versions (target + running).
- **Source**: codebase / issue (not overridden by operator)

## Decision 5: Untouched surfaces (hard constraints)
- **Question**: What must not be touched?
- **Resolution**: Do not touch the #3231 in-place marketplace refresh / install-resolution logic; do not add `claude plugin update` usage (doc forbids it). Only `skills/upgrade-larch/scripts/upgrade-larch.sh` and its sibling `skills/upgrade-larch/scripts/upgrade-larch.md` change. Shell stays Bash 3.2-compatible. No new external deps.
- **Source**: codebase / issue (not overridden by operator)
