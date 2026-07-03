## Goal
Implement issue #6152: [IMPLEMENTING] perf(/implement): CI-first — slim local checks to ruff+pyright; raise CI-fix cap to 30.

## Implementation Plan
> **Bundled issue.** This tracks two related changes toward a CI-first `/implement` loop: **Part 1** slims the local pre-PR check gate and defers the heavy suites to CI; **Part 2** (merged from #6167) raises the main-agent CI-fix loop cap so the run can actually iterate through the CI failures Part 1 defers. Land them together or in sequence (Part 1 first).

# Part 1 — Slim local relevant-checks to ruff-autofix + pyright; defer pylint/pytest/harnesses to CI

## Problem

Running `/implement` (and `/review`) **inside the larch repo itself** (dogfooding) is slow because the pre-PR local check gate re-runs larch's full, unscoped Python test and lint suites — repeatedly — before the PR is ever pushed. CI is the faster, massively-parallel path (~1 min), and `/implement` already has a CI-fix loop, so the heavy suites should run there, not locally.

## Root cause

`/implement` gates on `python3 python/cli.py checks run-relevant --site <site>` (impl: `python/larch/implement/checks_run_relevant.py`, driven via `skills/implement/scripts/run-step-checks.sh` + the `checks-commit-route` composites). It runs at **multiple sites per run** — Step 3 (`step3`), Step 5 self-review + review-fix (`step5-self-review`, `step5-mav`/`step5-review-fixes`), Step 6 (`step6`), and again in the CI-fix path (`step8-main-agent-fix`).

Each invocation (`_run_relevant_checks_inner`) runs, for larch's own file paths, a hardcoded `make`-target fan-out (`_DIRECT_TARGET_RULES`) that includes:

- `make py-test` → `cd python && pytest --durations=0` — the **entire suite, serial, unscoped** (~5,542 test functions across 165 files). Fires for essentially any Python source change.
- `make py-lint` → `ruff check .` + AST ratchets + **`pylint -j N .`** (pylint is ~90% of lint wall-time) + **`pyright`** — **whole-tree, not changed-file-scoped**. Fires for top-level `python/*.py`, config/toml edits, and a set of specific modules.
- A subset of the 287 bash `test-*` harness targets.

Because `py-test`/`py-lint` are unscoped and rerun at every checks site, a one-line Python change re-runs the whole ~5,500-test suite plus whole-tree pylint/pyright **3–4 times** in a single `/implement`. That is the multi-minute drag. `pre-commit run --files` (also part of relevant-checks) is scoped and cheap by comparison, and notably **does not include ruff/pylint/pyright** today.

## Not in scope: `/design`

Contrary to the initial framing, `/design` does **not** run relevant-checks, linters, or the test suite at runtime (no `run-relevant` / `make py-*` / `pytest` under `skills/design/`). It runs only plan-grammar validators. Any `/design` slowness comes from the plan-review panel (reviewer-agent dispatch) + clarify loop — a separate subsystem. Track that separately if it's a concern.

## Proposal

Slim the pre-PR local gate to **ruff (autofix) + pyright**, and defer pylint, the full pytest suite, and the bash `test-*` harnesses to CI + the existing CI-fix loop.

1. **Add ruff and pyright as changed-file-scoped pre-commit hooks** in `.pre-commit-config.yaml`, so they run at commit time and via `pre-commit run --files <changed>` inside relevant-checks:
   - `ruff` with autofix (`ruff check --fix`; consider `ruff format` too). Autofix is new — nothing wires `ruff --fix`/`ruff format` today.
   - `pyright` (resolve whole-tree vs scoped — see design details).
2. **Remove `py-test`, `py-lint` (pylint), and the `test-*` harness fan-out from the local path** — i.e. drop those entries / triggers from `_DIRECT_TARGET_RULES` in `python/larch/implement/checks_run_relevant.py` so they no longer run during `/implement`/`/review`.
3. **Keep `contains-pins` and `agent-lint` on the local path, and guarantee both also run in CI.** `contains-pins` is a linting-type validation (it statically checks that committed `test-*` script `contains "$VAR" "literal"` pins still exist in their target files) and is currently **local-only with no CI job** — this change must add a dedicated `contains-pins` CI job so the CI-superset invariant below holds. `agent-lint` already has a dedicated CI job.
4. **Lean on the CI-fix loop that already exists** (ship PR → CI monitor → `NEXT_ACTION=ci-fix` → autonomous fix). CI already shards pytest 20 ways, pylint by basename, and runs harnesses in a 6-cell matrix.

## Invariant: CI is a strict superset of local

**CI must run a strict superset of all linting and tests run locally — no check may be local-only.** This is a hard requirement, not a nicety: the local gate exists only as a fast, optional early-catch; CI is the authoritative gate, so anything worth running locally must also run in CI (CI may — and does — run *more*).

Coverage audit today (local relevant-checks phase → CI job):

| Local phase | CI coverage |
|---|---|
| `pre-commit run --files` | ✅ `lint` job (`pre-commit run --all-files`) |
| ruff | ✅ `python-lint` shard |
| pyright | ✅ `python-pyright` |
| pylint | ✅ `python-lint` shards |
| py-test | ✅ `python-tests` matrix |
| test-harnesses | ✅ `test-harnesses` matrix |
| agent-lint | ✅ dedicated `agent-lint` job |
| **contains-pins** | ❌ **none — local-only; must add a CI job** |

So deferring pylint / pytest / harnesses loses **no** coverage — all are already in CI. The one invariant violation to fix is `contains-pins`: add a CI job for it as part of this change. Also add a guard (a lint or test) that asserts every check in the local relevant-checks path has a CI counterpart, so the strict-superset invariant cannot silently regress.

## Tradeoff (stated for the record)

Deferring converts a locally-caught failure into a push → CI → autonomous-fix round-trip (minutes + fixer tokens). Accepted because CI is ~1 min and parallel, and keeping **ruff + pyright local (seconds)** still catches the highest-frequency Python errors cheaply pre-PR. pylint (slow) and the full serial pytest (slow) are exactly the right things to defer.

## Design details to resolve during implementation

- **ruff `--fix` mutates the working tree.** The autofixed changes must be staged/committed by the subsequent `commit-route`, not dropped. As a standard pre-commit fixing hook it modifies files and fails the hook so the change is re-staged; the autonomous `/implement` flow must capture those edits into the commit. Also reconcile autofix with the existing lint-fix coder-dispatch loop (autofix should resolve many failures mechanically, avoiding a Codex/Cursor dispatch).
- **pyright as a pre-commit hook** needs Node + pyright available in the hook env; decide whole-tree vs `pyright <changed-files>` (pyright resolves project-wide types regardless, so scoped invocation still typechecks dependents). Mirror the CI `python-pyright` setup.
- **`no-validation-phases` guard**: relevant-checks exits 2 if no phase runs. Ensure `pre-commit` (now carrying ruff/pyright) counts as a phase so stripping the direct make targets doesn't trip the guard on Python-only changes.
- **`_DIRECT_TARGET_RULES` scope**: these rules only match larch's own paths and are filtered against the client Makefile, so this change affects **larch dogfooding only** — generic consumer repos already run just pre-commit + contains-pins + agent-lint.

## Acceptance criteria

- Editing a `python/` file and running `/implement` no longer triggers a full local `pytest` run or whole-tree `pylint` at any checks site.
- `ruff` (autofix) + `pyright` run changed-file-scoped at commit time via pre-commit; ruff autofixes are committed, not lost.
- **CI is a strict superset of local**: every check in the local relevant-checks path also runs in CI. Specifically, a dedicated `contains-pins` CI job is added (it has none today), and a guard asserts the superset invariant so it can't regress.
- CI continues to gate pylint / pytest / pyright / harnesses; the CI-fix loop handles any deferred failure.
- relevant-checks does not trip the `no-validation-phases` guard on Python-only changes.
- Regression coverage updated (`python/tests/implement/test_checks.py`, `_DIRECT_TARGET_RULES` expectations, and `.pre-commit-config.yaml` hook wiring).

---

# Part 2 — Raise the main-agent CI-fix loop cap 3 → 30 (merged from #6167)

## Problem

The `/implement` main-agent CI-fix loop stalls after only **3** attempts. When the workflow relies on CI to catch errors (the direction of Part 1 above — slim local checks, push PR, fix CI, repeat), 3 autonomous fix cycles is too few: a PR that surfaces several independent CI failures in sequence exhausts the cap and hands off to the operator (`operator-bail`/`stall`) before the run can drive CI green on its own. Raise the cap to **30** ship-pr fix cycles.

## Where the cap lives

`skills/implement/references/ship-pr-ci-fix.md`, step 3:

> Use sentinel `$IMPLEMENT_TMPDIR/main-agent-ci-fix-$FAILED_RUN_ID.attempted` and counter `$IMPLEMENT_TMPDIR/main-agent-ci-fix.count`. **Attempts 1-3 may run; the next arrival falls through.**

Mechanics:
- **Global counter** `main-agent-ci-fix.count` — total main-agent CI-fix attempts across the whole `/implement` run. This is the cap being raised (3 → 30).
- **Per-run-id sentinel** `main-agent-ci-fix-$FAILED_RUN_ID.attempted` — idempotency guard so the *same* failed CI run is not re-fixed twice. Unchanged.

Each attempt is one full ship-pr fix cycle: read CI failure → capture redacted `gh run-logs` → minimal repo edit → `checks run-relevant --site step8-main-agent-fix` → commit → refresh run logs → push → re-invoke `step-8-ship.sh`. So the cap counts ship-pr re-invocations directly.

## Change surface (Part 2)

- The literal cap lives **only** in the prompt line above. It is **prompt-enforced**: the main agent reads/increments `main-agent-ci-fix.count` and falls through past the limit. There is no Python constant to change for this path.
- `scripts/test-implement-structure.sh` and `scripts/test-implement-step8-exit3-first-fixer.sh` pin the counter **filename** (`main-agent-ci-fix.count`), not the numeric limit — so they should not break, but re-run `make test-implement-structure` and `make test-implement-step8-exit3-first-fixer` to confirm.
- Per the drift-prone-prose rule, grep `skills/implement/SKILL.md`, `skills/implement/references/*.md`, `docs/`, and `README.md` for any prose referencing the "3 attempts" / "1-3" cap and update in lockstep.

## Related knob (decide scope)

`CI_AGENTIC_FIX_MAX_CYCLES = 20` (`python/larch/core/config.py`) caps the **autonomous coder** CI-fix loop (`python/larch/implement/ci_agentic_fix.py`), used by `/implement --merge` where a coder fixes CI without the main agent looping. That is a *different* flow from the main-agent path Part 2 targets. If "≤30 CI fixes before stall" should hold universally, bump this to 30 as well for consistency; otherwise leave it. Other loops (`CI_MONITOR_MAX_ITERATIONS=50`, `SHIP_MERGE_LOOP_MAX_ITERATIONS=50`, `CI_MONITOR_MAX_FIX_ATTEMPTS=10`) are monitor/poll caps, not "CI failures fixed" counts — leave them.

## Consideration

At 30, a non-converging fix can loop up to 30 autonomous edit → push → CI cycles before `operator-bail` — each cycle spends CI minutes + main-agent tokens + wall-clock. The per-run-id sentinel prevents duplicate attempts on the *same* CI run, but every re-ship creates a *new* run-id, so only the global counter bounds a recurring failure. This is the intended trade for a hands-off "drive CI green" loop; noting it so the raise is a deliberate autonomy/cost choice, not an oversight.

## Acceptance criteria (Part 2)

- The main-agent CI-fix loop runs up to **30** attempts before falling through to `operator-bail`/`stall` (was 3).
- Prose references to the old 3-attempt cap are updated in lockstep; no stale "1-3" wording remains.
- `make test-implement-structure` and `make test-implement-step8-exit3-first-fixer` pass.
- Scope decision on `CI_AGENTIC_FIX_MAX_CYCLES` (20 → 30 or leave) recorded in the PR.

This cap raise pairs with Part 1 above — it makes the CI-first loop actually able to iterate through the CI failures that Part 1 defers, without a premature operator bail.

## Test plan
(no test plan section in plan-file)
