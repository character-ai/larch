## Decision 1: Classification ownership (poll/status/decide)
- **Question**: ci-wait.sh delegates status+decision to ci-status.sh + ci-decide.sh (not in the named port list). Is reimplementing that poll/status/decide stack in-scope for Phase 6, or owned by another phase?
- **Resolution**: In-scope for Phase 6. The #3132 `python/` module inventory has no `ci_status.py`/`ci_decide.py`; Phase 3=rebase, Phase 4=local checks, Phase 5=PR/merge, Phase 7=driver. `ci_monitor.py` owns the full poll→status→decide reimplementation (gh pr checks bucket + behind-count + the ACTION matrix) to deliver "parity vs ci-wait.sh action classification".
- **Source**: user + codebase (#3132 phase map; sibling issue bodies)

## Decision 2: Fix model — fix all jobs, verify locally, push
- **Question**: On a real (non-transient) CI failure, what does the fix loop do before returning to the driver?
- **Resolution**: Collect ALL failed jobs + redacted logs; drive the CI vendor waterfall (`agents.run_waterfall`, cursor→codex→claude via `launch-*-ci.sh --role fix`) to fix; verify EACH fixable job locally via its `make` target; stage+commit+push once; return a "fixing was done → GOTO Rebase" signal. Not one-job-at-a-time; not internal re-poll-to-green.
- **Source**: user

## Decision 3: Per-job local fixer when local re-verify still fails (Phase-1-only)
- **Question**: Phase 6 is blocked by Phase 1 only (not Phase 4's checks.py). When a fixable job's local `make` re-verify still fails after the vendor waterfall, how should ci_monitor.py handle the per-job fix?
- **Resolution**: Re-drive the CI vendor waterfall, capped (internal cap = parity with `run_evaluate_failure` `_max_fix=3`, jittered backoff). Unfixable / no-local-equivalent jobs (gitleaks, trufflehog) bail. Stays Phase-1-only — does NOT import Phase 4's `checks.py` and does NOT duplicate `run_captured_cmd_then_fix_loop` / `run-external-agent.sh`. Any targeted per-job local fixer is deferred to the Phase-7 driver.
- **Source**: user

## Decision 4: Rebase is decoupled (signal, not inline)
- **Question**: bash `_stage_and_push_ci_fixes` inlines `run_rebase_rebump`. Does ci_monitor.py call rebase.py?
- **Resolution**: No. Per #3132 ("this module owns monitor + fix + signal; the GOTO Rebase loop and its iteration cap are wired by the Phase 7 driver"), ci_monitor.py returns a GOTO-Rebase signal after any fixing work and does NOT import `rebase.py`. ci_monitor's push is a normal push; the driver owns rebase + force-push-with-lease.
- **Source**: codebase (#3132 master flow + blocking DAG `#3239 ← #3234` only)

## Decision 5: Caps, HEAD-changed, transient-retry (parity)
- **Question**: Where do the caps live and what are the parity semantics?
- **Resolution**: Add CI-monitor caps to `config.py` (iteration≥50, rebase≥20, fix-attempts≥10 from ci-decide.sh; internal `_max_fix`=3; transient-retry cap). HEAD-changed during stage/verify → parity with bash `exit_stall` (STALLED outcome / abandon this fix). First failure (TRANSIENT_RETRIES < cap) → rerun failed jobs only (`gh run rerun --failed`), no fix. First-fixer-non-health short-circuit is already in `agents.run_waterfall`.
- **Source**: codebase (ci-decide.sh, run_evaluate_failure, config.py)

## Decision 6: Strangler-fig — additive only
- **Question**: Any change to the live /implement path or `.sh` deletions?
- **Resolution**: None. Additive only: create `python/ci_monitor.py` + `python/test_ci_monitor.py`, a one-line `python/README.md` layout bullet, and additive `config.py` constants. Zero change to `ship-pr.sh` or the live `/implement` path; no `.sh` deletions (cutover is Phase 7). gh.py/git.py edits minimized — run `gh pr checks` / extra git verbs via the injected `Runner` inside ci_monitor.py (parity with Phase 4's "git.py stays unedited" approach), reusing existing `gh`/`git` helpers where present.
- **Source**: codebase (#3132 locked architecture; Phase 4 plan precedent)
