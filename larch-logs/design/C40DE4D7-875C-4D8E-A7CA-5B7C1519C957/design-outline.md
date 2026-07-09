## Proposed Design Outline

### Goals
- Give `scripts/test-bgjob.sh` real-process coverage for all six work-item-A scenarios (STARTED line, owner death, budget expiry, external kill, reap of a recycled-PID stale row, slug rejection), fast, with production timing defaults unchanged.
- Add pytest coverage for `reap_main`: stale dead row removed, recycled-PID row left unsignaled, live identity-valid row preserved.
- Durably record the #6516 Section E sentinel KEEP/DELETE decision table in a committed doc, and drop the stale `_bg_wait_marker_context` env-via-config-constant baseline entry.

### Non-goals
- No changes to bgjob daemon lifecycle, wait, registry, or result-env semantics beyond a test-only timing override.
- No editing of already-merged PR #6706; the table ships in this issue's new PR instead.
- No new shared Bash libraries; do not drop or duplicate the existing `python/tests/bgjob` pytest suite.

### Approach sketch
- Add a test-only env override for `BGJOB_OWNER_GRACE_S` (and `BGJOB_DAEMON_POLL_INTERVAL_S` only if grace-only is too slow), read through a new config `ENV_*` `Final` name constant, production default (120 / 1.0) unchanged (G-Cfg-1).
- Rewrite `scripts/test-bgjob.sh` as one Bash 3.2 real-process harness driving `python3 python/cli.py bgjob start|wait|reap`; skip loudly when the sandbox blocks `ps` identity probes (G-Py-4).
- Add `reap_main` cases under `python/tests/bgjob/`; the recycled-PID case asserts no signal to the new owner (G-Sec-5).
- Record the Section E table in a committed markdown doc; regenerate `python/env-via-config-constant-baseline.json` via `make regen-env-via-config-constant-baseline` (never hand-edited).

### Surfaces in scope
- `scripts/test-bgjob.sh` (rewrite)
- `python/larch/core/config.py` (new `ENV_*` constant; env-overridable grace/poll read site here or in `python/larch/bgjob/daemon.py`)
- `python/tests/bgjob/` (reap tests)
- `python/env-via-config-constant-baseline.json` (regenerated, drop stale entry)
- A committed doc hosting the Section E decision table (exact file chosen in drafting)

### Open questions
- Exact committed home for the Section E table (deferred to Step 2b / plan review).
- Whether the poll-interval override is needed in addition to the grace override.
