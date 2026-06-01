## Decision 1: Fix approach — test-harness only
- **Question**: Test-only stub (issue Option 1) vs. also hardening production so real `/design` runs don't hang when a tool is unavailable?
- **Resolution**: Test-harness only. No production-code changes to `run-external-agent.sh`, `plan-review-loop.sh`, or the launcher libs. Stub the external binaries in the affected test harnesses.
- **Source**: user

## Decision 2: Breadth — sweep all make-lint harnesses
- **Question**: Fix only `test-plan-review-loop` (the named offender) vs. audit every make-lint harness that can reach a real external launch?
- **Resolution**: Sweep. Audit every make-lint harness that passes `--codex-present`/`--cursor-present true` (or otherwise reaches a real `codex`/`cursor`/`claude` launch); apply the stub pattern to any that are at-risk; verify the whole suite is hang-free.
- **Source**: user

## Decision 3: Stub mechanism — PATH-prepended STUB_BIN (process boundary)
- **Question**: Which stubbing mechanism for the at-risk harness(es)?
- **Resolution**: Prepend a `STUB_BIN` dir holding minimal `codex`/`cursor`/`claude` stubs to `PATH` at the top of each at-risk harness (the `skills/implement/scripts/test-codex-implementer.sh` pattern). This is path-agnostic: it neutralizes every real-binary launch regardless of which internal code path (revise, scout, dispatch) reaches it, so we do not have to enumerate every launch site. Script-level `LARCH_*_SH` stubs already present in a harness still win for the deterministic paths; the binary stub only catches paths that would otherwise reach a real binary (which currently hang, so have no passing assertions to break).
- **Source**: codebase (canonical pattern at test-codex-implementer.sh:218-287) + user (endorsed Option 1)

## Decision 4: At-risk set (audit result)
- **Question**: Which make-lint harnesses actually reach a real external launch?
- **Resolution**: `skills/design/scripts/test-plan-review-loop.sh` is confirmed at-risk: `run_loop` defaults `LARCH_PLAN_REVIEW_REVISE_SH` to the real `revise-plan-with-waterfall.sh` (line 818; mirrored at 2715), which calls the real `launch-review.sh` → real `codex`/`cursor`. Audited and found already-isolated (no real launch): `test-dispatch-plan-review-panel.sh`, `test-dispatch-plan-assessors.sh`, `test-assess-plan-round.sh`, `test-scout-plan-archetypes-wrapper.sh`, `test-decompose-panel-dispatch.sh`, `test-decompose-aggregator.sh` (all stub via `*_WATERFALL_SH` / `LARCH_DISPATCH_*` / stub manifests), `test-run-external-agent.sh` (passes harmless `bash -c` commands), `test-launch-review.sh` / `test-launch-claude-review.sh` / `test-dispatch-with-waterfall.sh` / `test-step2-dispatch.sh` / `test-revise-plan-with-waterfall.sh` (PATH stubs / `LARCH_TEST_LAUNCH_*`), `test-design-multi-round-integration.sh` (exports a `revise-plan-with-waterfall.sh` stub before `run_loop`). The implementation step re-runs the audit grep to catch any harness missed here before concluding the sweep.
- **Source**: codebase

## Decision 5: Hard constraints
- **Question**: What must not break?
- **Resolution**: (a) No production behavior change. (b) Bash 3.2 portability (BASH_AUTHORING.md §3). (c) Do not break existing passing assertions / faithful control-flow coverage (complete / bailed / needs-qa paths — acceptance #3). (d) Stubs must satisfy `set -euo pipefail` and the script-md sibling rule does not require new siblings for edited-in-place test files. (e) Stub binaries must honor the launcher's output contract (e.g. `codex`'s `--output-last-message <path>`) so `run-external-agent.sh` sees a completed launch instead of an empty/again-blocking one.
- **Source**: codebase / AGENTS.md / BASH_AUTHORING.md

## Decision 6: Out of scope
- **Question**: What is explicitly excluded?
- **Resolution**: Production timeout/health-gate in `run-external-agent.sh` or `plan-review-loop.sh`; building a `check-codex-health.sh` (none exists today); any degrade-to-Claude production logic. These are the deferred "Option 2" robustness items.
- **Source**: user

## Decision 7: Verification
- **Question**: What defines done?
- **Resolution**: `make lint` (at minimum the affected shard `test-harnesses-1` plus any harness touched) completes without hanging on a machine where Codex is unavailable; the at-risk harness(es) invoke no real `codex`/`cursor` binary. Verification approach: run the harness with a PATH stub-bin and confirm completion + the loop's control-flow assertions still pass.
- **Source**: acceptance criteria
