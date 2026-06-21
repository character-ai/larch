## Goal
Implement issue #4946: [IMPLEMENTING] [OOS] ci-wait empty-checks timeout + /design concern-overlap + pre-rebase flush commit-failed (3 items).

## Implementation Plan
## Out-of-Scope Observation (combined)

Combined from #4924, #4920, and #4930 via `/combine-issues --oos`. Three OOS findings packed to reduce issue count. They touch different subsystems (`python/ci.py`, `/design` plan-review, `python/ship.py` / `python/config.py`); treat as three independent tasks within one issue.

**Phase**: design / implement

### Item 1 — manual `ci wait` default leaves an empty-checks full-timeout path

**Location**: `python/ci.py` (`--empty-checks-grace`, default `0`)
**Surfaced by**: Codex-Generic

`python3 python/cli.py ci wait` with the default `--empty-checks-grace 0` can poll a zero-check head until the poll budget is exhausted (full timeout). The ship-driver minimum change left `python/ci.py` unchanged, so this path persists; it matches the issue's synthetic reproduction path.

Actuality (verified 2026-06-20): `--empty-checks-grace` default `0` is declared at `python/ci.py:64` (`ci status`) and `python/ci.py:179` (`ci wait`), and flows unchanged into `ci_monitor.poll_ci` at `python/ci.py:264`. Concern intact.

### Item 2 — `/design` plan-review re-lists concerns already satisfied (concern-level overlap)

**Surfaced by**: Cursor-Innovation
**Vote tally**: accepted by `/design` plan-review panel

Follow-on to #4884 (closed 2026-06-20). The #4884 fix relabeled the "Unimplemented Plan Review Suggestions" section and hardened the prompt, but dedups only by finding-identity, so rejected blocks whose Concern text still misstates the current plan remain in the operator list. The fix reframes the report rather than suppressing concerns at the concern level. Real run #4773: five already-satisfied concerns still appear under softer framing; only the section title changed, not the per-finding false claims.

Actuality (verified 2026-06-20): #4884 is closed/fixed; this residual concern-level-overlap claim is not disprovable from files alone, so it is kept. Folds in #4930 ("Branch fixes #4884 via report reframing, not concern-level suppression"), a duplicate of this concern.

### Item 3 — pre-rebase merge-loop flushes still treat `commit-failed` as warn-only via `REFRESH_SKIP_MERGE_OK`

**Location**: `python/ship.py` (pre-rebase refresh gates) and `python/config.py` (`REFRESH_SKIP_MERGE_OK`)
**Surfaced by**: Cursor-Innovation
**Vote tally**: accepted (design plan review for #4900)

Post-ensure flush+push is hardened, but later pre-rebase refreshes on CI-fix/rebase paths still allow squash-merge without a newer log commit if that flush fails to commit. Straight-merge happy path is covered; rebase-heavy paths retain a narrower stale-snapshot window.

Actuality (verified 2026-06-20): `REFRESH_SKIP_COMMIT_FAILED = "commit-failed"` is a member of `REFRESH_SKIP_MERGE_OK` (`python/config.py:297,307`), and the pre-rebase gates at `python/ship.py:1783` and `python/ship.py:1885` test `pre_rebase.reason not in config.REFRESH_SKIP_MERGE_OK`. The hardened `REFRESH_SKIP_POST_ENSURE_PR_OK` set (`python/config.py:310-318`) excludes `commit-failed`, confirming the asymmetry. Concern intact.

---
*Combined by `/combine-issues --oos` from #4924, #4920, #4930. Original line numbers in the source issues were stale; verified locations are updated above.*

## Test plan
(no test plan section in plan-file)
