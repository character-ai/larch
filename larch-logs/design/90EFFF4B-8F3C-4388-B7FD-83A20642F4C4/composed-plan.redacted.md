## Plan


## Files to modify/create

### UPDATED: `skills/design/scripts/test-read-design-review-budget-invoke.sh`

Extend the offline harness with the missing-coverage cases identified in the OOS observation. Reuse existing fixtures — no new fixture files are introduced. Maintain the existing structure (single `bash` script, `fail()` helper, `trap` cleanup).

Add seven new assertion groups (each one-liner-ish — total roughly 80 added lines including helper setup), organized by target script:

1. **`read-design-review-budget.sh` — file unreadable** — call with a path that does not exist (`/tmp/larch-rdb-missing.<rand>`); expect `full`. Exercises the `[[ ! -r "$f" ]]` early-return branch (lines 9-12 of the target script).
2. **`read-design-review-budget.sh` — `sketch_budget` heuristic via python3** — JSON `{"sketch_budget": 2}` and `{"sketch_budget": 4}` each yield `full`. Exercises the python3 fallback's `print("quick" if sb == 0 else "full")` branch when no `review_budget` key is present and `sketch_budget` is non-zero.
3. **`read-design-review-budget.sh` — jq path** — fake-bin overrides only `python3` (real `jq` left on `PATH`). JSON `{"review_budget":"quick"}` yields `quick`. Exercises the jq branch (lines 32-35) reached when python3 fails. Skips with a clear message if `command -v jq` finds no real `jq` (CI safety; should not happen on the dev image).
4. **`read-design-review-budget.sh` — grep fallback for `review_budget=full`** — fake-bin overrides both `python3` and `jq`. JSON `{"review_budget":"full"}` yields `full`. Exercises the grep literal branch at lines 41-44 (current harness only covers the `quick` literal at lines 37-40).
5. **`read-design-review-budget.sh` — all fallbacks exhausted** — fake-bin overrides both `python3` and `jq`. JSON `{}` (no `review_budget`, no `sketch_budget`) yields `full`. Exercises the terminal default `printf full` at line 51.
6. **`invoke-plan-validator-if-not-quick.sh` — argv / env guards** — three sub-cases with `set +e` capture of `$?`:
   - Missing `PLAN_FILE` (`"$INVOKE"` with no args) → exit non-zero.
   - `DESIGN_TMPDIR=` empty with a valid plan file → exit non-zero (target script's `: "${DESIGN_TMPDIR:?...}"`).
   - `CLAUDE_PLUGIN_ROOT=` empty with valid `DESIGN_TMPDIR` and plan file → exit non-zero (target's `: "${CLAUDE_PLUGIN_ROOT:?...}"`).
7. **`invoke-plan-validator-if-not-quick.sh` — `run-params.json` missing, full-tier defects-found** — two sub-cases:
   - `$dt_norp` directory with no `run-params.json` and a real plan file → exits 0 with empty stdout (default-to-quick branch in target script lines 13-17 when `[[ -r "$rp" ]]` is false).
   - Full-tier invocation against `fixtures/validate-plan-commands/demo-plan.md` (an existing fixture that references `--unknown-flag` on `demo-stdout-help.sh`) → stdout contains `VALIDATE_STATUS=defects-found`, `VALIDATE_DEFECT_COUNT=1`, and `STEP_COMPLETED=VALIDATE_PLAN_COMMANDS`. Confirms end-to-end driver path emits a non-ok validator status.

The new cases follow the existing harness's idiom: temp `run-params.json` under `mktemp -d` tmpdirs, fake-bin PATH overrides for grep-fallback coverage, and `fail "<reason>"` on assertion miss. Update the cumulative `trap '...' EXIT` line as additional temp paths are introduced so cleanup still works on failure.

### UPDATED: `skills/design/scripts/test-read-design-review-budget-invoke.md`

Refresh the sibling contract description to enumerate the added coverage: argv/env guards on `invoke-plan-validator-if-not-quick.sh`, the `run-params.json` missing → skip-quick path, the `VALIDATE_STATUS=defects-found` reuse of `fixtures/validate-plan-commands/demo-plan.md`, and the python3-only fakebin used for the jq-path branch. Keep the running-instructions section unchanged (`make test-read-design-review-budget-invoke`).

## Approach

The OOS observation is concrete: the existing harness covers the happy `VALIDATE_STATUS=ok` path and the python3 / grep paths of `read-design-review-budget.sh`, but leaves the jq fallback, the full-grep branch, the `sketch_budget` non-zero heuristic, the file-unreadable default, the argv/env guards of the invoke wrapper, the `run-params.json` missing path, and the `VALIDATE_STATUS=defects-found` outcome uncovered. The fix is a pure harness expansion — no production-code changes.

All five validator outcomes / target-script branches are reachable with **existing fixtures**, per the Step 1c "Reuse existing fixtures" decision:
- `fixtures/parse-plan-commands/basic-plan.md` for the existing `VALIDATE_STATUS=ok` case (untouched).
- `fixtures/validate-plan-commands/demo-plan.md` for the new `VALIDATE_STATUS=defects-found` case — `demo-stdout-help.sh` documents only `--known-flag`, and the plan invokes it with `--unknown-flag value`, so Tier 2 emits a single defect.

The fake-bin pattern already used by the harness (lines 29-33) is extended with a **python3-only** fakebin so the jq branch is exercisable without mocking jq. Real `jq` availability is checked with `command -v jq`; the jq-path case is conditional on jq being present (no hard fail if missing — matches the production script's own jq-optional design).

## Edge cases

- **CI without `jq` installed**: the jq-path test guards on `command -v jq`. If missing, print `SKIP: jq not on PATH; skipping jq-path branch` and proceed (mirrors the production script's optional-jq invariant).
- **`set -e` interaction**: the argv / env guard tests must wrap each invocation in `set +e ... set -e` to capture the non-zero exit code without aborting the harness.
- **`trap` accumulation**: the harness currently re-`trap`s on each new tmpdir. Extend that pattern so every new mktemp path is included in the final cleanup trap; preserve the existing `rm -rf "$fakebin" "$dt" "$full_dt"; rm -f "$tmp"` cleanup.
- **Fakebin shadowing of system tools**: keep `PATH="$fakebin:/usr/bin:/bin:/usr/sbin:/sbin"` so `chmod`, `printf`, `grep` resolve to system tools and only `python3` / `jq` are stubbed. For the python3-only fakebin variant, prepend the real `jq` directory (resolved via `command -v jq` then `dirname`) so real `jq` is reachable while python3 is shadowed.
- **`{}` empty-object JSON**: the final-fallback test uses `{}` rather than malformed JSON so the python3 / jq stubs still get a syntactically valid input — keeps the cause of the fall-through to grep unambiguous (no JSON parse interference, just absence of the keys).
- **macOS `mktemp` template requirement**: continue using `${TMPDIR:-/tmp}/larch-<short>.XXXXXX` so Linux and macOS `mktemp` both accept the template (the existing harness already uses this pattern).

## Testing strategy

Manual: `bash skills/design/scripts/test-read-design-review-budget-invoke.sh` runs the harness directly and prints `PASS: test-read-design-review-budget-invoke.sh` on success.

CI: the `make test-read-design-review-budget-invoke` target (already wired) executes the harness via `scripts/harness-timer.sh`. The post-change run must keep that target green and increase the assertion count by at least 7 (the new groups above), which can be verified by running the harness before and after the change.

No production-code touch is required, so no behavioral regression risk exists outside the harness itself. Pre-commit lint (`make lint`) is expected to remain green because the only changes are `.sh` and `.md` content under `skills/design/scripts/` — no new bash-3.2 constructs, no new external-tool invocations, no new foreground-marker blocks.


## Acceptance

- `bash skills/design/scripts/test-read-design-review-budget-invoke.sh` exits 0 with `PASS: test-read-design-review-budget-invoke.sh` on stdout.
- `make test-read-design-review-budget-invoke` exits 0.
- Pre-commit `make lint` remains green (no new bash-3.2 violations, no new external-tool invocations needing the foreground-marker contract).
- No production-source files outside the two harness/doc files above are modified.
- New harness assertions exercise: (1) `read-design-review-budget.sh` file-unreadable default; (2) sketch_budget non-zero heuristic via python3; (3) jq path (conditional on `command -v jq`); (4) grep fallback for `review_budget=full`; (5) all-fallbacks-exhausted default; (6) three argv/env guard exits on `invoke-plan-validator-if-not-quick.sh`; (7) `run-params.json` missing → silent quick-skip; (8) full-tier `VALIDATE_STATUS=defects-found` via `fixtures/validate-plan-commands/demo-plan.md`.

diff_lines: 95
