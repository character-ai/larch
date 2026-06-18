## Goal
Implement issue #4637: [IMPLEMENTING] sh-to-py G8: /implement finalize + preflight + Step-18 closeout bodies — port in-process.

## Implementation Plan
## Plan

Port `/implement` preflight and Step 16/17 closeout into Python, extract final-report code from `pr_body.py`, retire the listed Bash surfaces, and update callers, docs, lint reachability, and tests.

### Files to modify/create

**NEW:** `python/preflight.py` — `preflight_main(argv)` for `python3 python/cli.py implement preflight`. Ports all gates from `scripts/implement-preflight.sh`: positive-numeric `--issue`, required writable `--preflight-tmpdir`, optional `--repo` and `--emergency`, `admission gate` call, emergency bypass for `missing-designed-prefix` only, `gh issue view` retry-once, `plan-block read`, missing/malformed-plan emergency fallback, legacy lifecycle-prefix stripping, emergency-bypass.log, zero-review provenance refusal. Preserves exact success KV envelope (`ADMISSION_RESULT`, `RESUME`, `TITLE`, `BLOCK_PRESENT`, `PLAN_PATH`, `ISSUE_JSON_PATH`, `BYPASS_COUNT`). Stdlib-only.

**NEW:** `python/test_preflight.py` — pytest coverage for `python/preflight.py`. Stubs `admission gate`, `plan-block read`, `gh issue view`. Covers admission refusal, emergency bypass, `--repo` forwarding, missing/malformed plan paths, provenance refusal, KV envelope.

**NEW:** `python/final_report.py` — extracts `write_final_report`, `write_final_report_main`, `step18b_final_report`, `step18b_final_report_main`, and private helpers from `python/pr_body.py`. CLI output, return codes, and behavior unchanged.

**UPDATED:** `python/pr_body.py` — remove moved final-report implementations; keep compatibility wrappers or re-exports for any remaining internal callers.

**NEW:** `python/closeout.py` — `step_16_main`, `step_17_main`, `step_16_17_main`. Preserves: Step 16 run-id rehydration and best-effort rejected-findings write; Slack best-effort with redacted-Warnings on `STATUS=failed`; Step 17 `--no-print-stdout` backup/restore, Tool Failures on failure, direct-call marker printing; composed wrapper that always exits 0, gates markers on Step 17 success and non-empty `summary-final.md`, emits exact `---LARCH-SUMMARY-FINAL-BEGIN---`/`---LARCH-SUMMARY-FINAL-END---` markers, touches `.step17-printed` only after emission, never touches `.step17-emitted`.

**NEW:** `python/test_closeout.py` — pytest for `python/closeout.py`. Covers happy path, Step 16 failure, Slack skip/fail, stale-summary guard, upsert-fail with fresh summary, `.step17-printed` ownership, `.step17-emitted` absence.

**UPDATED:** `python/finalize.py` — close CLI parity gaps vs. `implement-finalize.sh`: reject unknown args, require phase-specific args, validate state-file under allowed roots, validate required keys and booleans. Keep postbump/postmerge/teardown behavior.

**UPDATED:** `python/test_finalize.py` — extend for former shell contract (usage errors, state-file validation, required-key checks, boolean checks, cache-root acceptance, cleanup-target checks, teardown tail KVs).

**UPDATED:** `python/test_finalize_bash_parity.py` — remove Bash parity dependence; delete or convert to direct Python CLI tests with no reference to `scripts/implement-finalize.sh`.

**UPDATED:** `python/cli.py` — register: `("implement", "preflight"): ("preflight", "preflight_main")`, `("implement", "step-16"): ("closeout", "step_16_main")`, `("implement", "step-17"): ("closeout", "step_17_main")`, `("implement", "step-16-17"): ("closeout", "step_16_17_main")`; reroute `("final-report", "write")` and `("final-report", "step18b")` to `final_report` module.

**UPDATED:** `skills/implement/SKILL.md` — replace `scripts/implement-preflight.sh` fence with `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" implement preflight ...`; replace `skills/implement/scripts/step-16-17.sh` fence with `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" implement step-16-17`; keep Step 18 as `step-18.sh`; update prose naming retired scripts.

**UPDATED:** `scripts/test-implement-fence-shape.sh` + `.md` — update fence expectations.

**UPDATED:** `scripts/test-implement-structure.sh`, `scripts/test-render-cost-line-callsites.sh`, `scripts/test-plan-adequacy-audit.sh` + `.md`, `scripts/test-cache-root-validation.sh` + `.md`, `scripts/test-implement-cleanup-roundtrip.sh` + `.md` — retarget retired paths to Python CLI surfaces.

**UPDATED:** `SECURITY.md`, `docs/linting.md`, `docs/vendor-agent-diagnostics-audit.md`, `scripts/flush-vendor-failure-diagnostics.md`, `scripts/git-force-push.md`, `scripts/rebase-push.md`, `skills/implement/scripts/flush-execution-issues.md`, `skills/implement/scripts/lib-implement-clone-tag.md`, `skills/implement/scripts/step-18.md`, `skills/implement/references/preflight-plan-audit.md` — update doc references from retired Bash surfaces to Python CLI equivalents.

**UPDATED:** `agent-lint.toml`, `python/checks.py`, `Makefile` — retire harness targets for deleted scripts; add targets for new Python test modules.

**NEW:** `python/test_final_report.py` — tests for `write_final_report`, `step18b_final_report`, manifest stamping, issue-count derivation, token-cost fallback.

**UPDATED:** `python/test_pr_body.py` — update imports/monkeypatches for moved final-report code.

**DELETED:** `skills/implement/scripts/step-16.sh` + `.md` + `step-17.sh` + `.md` + `step-16-17.sh` + `.md` + `test-step-16-17.sh` + `.md`, `scripts/implement-preflight.sh` + `.md` + `test-implement-preflight.sh` + `.md`, `scripts/implement-finalize.sh` + `.md` + `test-implement-finalize.sh` + `.md` + `test-finalize-sanity-check.sh` + `.md`.

**UPDATED:** `python/migrated-scripts.tsv` — add all deleted `.sh` and `.md` paths with `#3692`.

## Acceptance

- `python3 -m pytest python/test_preflight.py python/test_closeout.py python/test_final_report.py python/test_finalize.py -q` passes.
- `make lint-retired-scripts` passes with no stale retired-path references.
- `make py-lint py-test lint` passes.
- Makefile targets `test-implement-preflight`, `test-step-16-17`, `test-implement-finalize`, `test-implement-fence-shape`, `test-plan-adequacy-audit`, `test-implement-structure`, `test-render-cost-line-callsites`, `test-cache-root-validation` all pass.
- `skills/implement/SKILL.md` Preflight fence invokes `python/cli.py implement preflight`.
- `skills/implement/SKILL.md` Step 16-17 fence invokes `python/cli.py implement step-16-17`.
- None of the deleted Bash scripts remain in the repository.

diff_lines: 4250

## Test plan
(no test plan section in plan-file)
