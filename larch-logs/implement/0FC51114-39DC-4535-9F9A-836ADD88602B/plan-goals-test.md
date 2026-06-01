## Goal
Implement issue #3338: [IMPLEMENTING] make lint hangs on test-plan-review-loop when Codex is unavailable\n\n`make lint` hangs indefinitely on developer machines when Codex is unavailable (unhealthy, quota exhausted, or not authenticated)..

## Implementation Plan
## Plan

Fix is **test-only**: `make lint` hangs when Codex (or Cursor) is installed but unavailable (auth/quota/network). `test-plan-review-loop.sh` stubs the loop's orchestration scripts via `LARCH_PLAN_REVIEW_*_SH`, but `run_loop` defaults `LARCH_PLAN_REVIEW_REVISE_SH` to the **real** `revise-plan-with-waterfall.sh` (lines 818 and 2715), which calls the real `launch-review.sh` → real `codex`/`cursor`. The launcher libs have no `command -v codex` availability guard, so an installed-but-unhealthy binary launches and blocks on the production reviewer timeout (~30 min), which reads as a hang. Prepend a `STUB_BIN` of minimal `codex`/`cursor`/`claude` stubs to `PATH` so no real binary can ever launch, regardless of which internal path reaches it (issue Option 1).

### UPDATED: `skills/design/scripts/test-plan-review-loop.sh`
- After the existing `TMP`/`STUB` setup (around line 44, before the first launch-capable section), add a dedicated `STUB_BIN="$TMP/bin"` directory containing executable `codex`, `cursor`, and `claude` stubs, then `export PATH="$STUB_BIN:$PATH"`.
- Each stub is `#!/usr/bin/env bash` with `set -euo pipefail`, parse-tolerant, and exits `0` immediately:
  - `codex`: scan argv for `--output-last-message <path>`; when present, write one minimal line to that path. Print one minimal line to stdout. Never read stdin. Exit 0.
  - `cursor`: print one minimal line to stdout. Exit 0.
  - `claude`: print one minimal line to stdout. Exit 0.
- Mirror the PATH-prepended `STUB_BIN` pattern at `skills/implement/scripts/test-codex-implementer.sh:218-287`, dropping manifest fields this harness does not need.
- Do not remove or alter the existing `LARCH_PLAN_REVIEW_*_SH` script-level stubs. The binary stub is a hermetic backstop layered beneath them; script-stubbed paths call their stub scripts by absolute path and never reach a binary.
- Keep the existing `trap 'rm -rf "$TMP"' EXIT` as the stub cleanup (the stub dir lives under `$TMP`).
- Keep stubs Bash 3.2-compatible (`[[ ]]`, `for arg in "$@"`, `printf`; no `mapfile`/namerefs/`${var^^}`).

### UPDATED: `skills/design/scripts/test-plan-review-loop.md`
- Document the new PATH `STUB_BIN` backstop: why it exists (#3338), which binaries it stubs, and that it guarantees the harness never launches a real external binary even when a script-level stub is missing on some path.

### Approach notes
- Hermetic process boundary: a PATH stub neutralizes every real-binary launch site (the revise-tier waterfall today, plus any path added later) without enumerating each one.
- The binary stub only intercepts paths that currently reach a real binary (paths that hang today, so have no passing assertion to break). Deterministic script-stubbed paths (`LARCH_PLAN_REVIEW_*_SH`) are unaffected because they invoke their stub scripts directly.
- **Sweep scope**: re-run the audit grep over make-lint harnesses that pass `--codex-present`/`--cursor-present true` or reach a real launcher. The audit during design found only `test-plan-review-loop.sh` at-risk; the rest already isolate externals via `*_WATERFALL_SH` / `LARCH_DISPATCH_*` / stub manifests, or pass harmless `bash -c` commands. If the re-audit surfaces a second at-risk harness, apply the same inline `STUB_BIN` pattern there; extract a shared helper only if 2+ harnesses need identical stubs (otherwise keep it inline per KISS).
- **No production-code change**: the launcher timeout/health gap (`run-external-agent.sh`, `plan-review-loop.sh`) is intentionally out of scope.

### Failure modes
1. Stub output breaks a previously-green assertion — mitigation: for any such section, add the minimal `LARCH_PLAN_REVIEW_REVISE_SH` script-stub (the existing per-section pattern) so its revise stays deterministic.
2. Stub still blocks — mitigation: stubs `exit 0` immediately and never read stdin; verify with a `timeout`-wrapped run.
3. PATH stub shadows a tool the harness genuinely needs — mitigation: the stub dir is scoped to `$TMP/bin` for this harness only (cleaned by the existing `trap`) and shadows only `codex`/`cursor`/`claude`.

### Testing strategy
- Run `bash skills/design/scripts/test-plan-review-loop.sh`; all assertions pass and it completes in seconds.
- Run `make test-plan-review-loop` (shard `test-harnesses-1`); time permitting, run full `make lint`.
- Run `bash scripts/relevant-checks.sh` (covers `make lint-bash32`, shellcheck, `test-design-structure`).

## Acceptance

- [ ] `make lint` completes without hanging on a machine where Codex is unavailable.
- [ ] `test-plan-review-loop` invokes no real `codex` or `cursor` binary (PATH `STUB_BIN` intercepts every launch).
- [ ] The stubs exercise the loop's control flow faithfully (complete / bailed / needs-qa paths); all existing `test-plan-review-loop.sh` assertions still pass.
- [ ] No production-code change (`run-external-agent.sh`, `plan-review-loop.sh`, launcher libs untouched).
- [ ] Re-audit confirms no other make-lint harness reaches a real external launch; any that does gets the same stub.
- [ ] `skills/design/scripts/test-plan-review-loop.md` documents the `STUB_BIN` backstop.
- [ ] Stubs are Bash 3.2-compatible and shellcheck-clean; `scripts/relevant-checks.sh` passes.

diff_lines: 72

## Test plan
(no test plan section in plan-file)
