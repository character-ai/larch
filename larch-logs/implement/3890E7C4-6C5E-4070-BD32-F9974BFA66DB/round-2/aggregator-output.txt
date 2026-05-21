Aggregating duplicate reviewer slots into normalized findings. Not calling CreatePlan — the requested deliverable is only the structured finding list (read-only aggregation of the supplied input).

```text
### FINDING_1: Redundant `final_report_*` initialization in `ship-pr.sh`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Concern**: Duplicate assignments to `final_report_rc` / `final_report_output` right after local initialization obscure control flow and invite misreads about resets, branches, or unset state; no functional bug identified.
- **Suggested revision**: Collapse to a single initialization site (remove redundant reassignment).

### FINDING_2: `postmerge_missing_manifest` harness diverges from real post-merge preconditions
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Concern**: The test omits `post-merge-sentinel` and related ordering/assertions used by sibling post-merge tests; the stubbed `larch-log` path can pass while production’s sentinel + bypass predicate chain regresses.
- **Suggested revision**: Add `touch post-merge-sentinel` (or equivalent), align assertions with other post-merge ordering tests, and assert the intended `status=done` / write-final-report / commit sequence where that is the regression signal you want.

### FINDING_3: `LARCH_LOG_COMMIT_POSTMERGE_SHIP_PR` is an env-gated, weakly attested commit bypass
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: The bypass is convention-driven (env + sentinel + tmpdir shape). In shared or long-lived shells, a mistaken/malicious `export` could widen what later `larch-log.sh commit` invocations are allowed to do; several reviewers treat this as latent integration/security risk unless explicitly narrowed and documented.
- **Suggested revision**: Treat as a private contract: document clearly (including `SECURITY.md` threat model if you accept that maintenance surface), and if tightening is required, mechanically narrow coupling (e.g., one-shot/nonce file touched only by `ship-pr`, unset after use, tmpdir/repo pairing) rather than env alone.

### FINDING_4: No CI harness exercises the real `larch-log.sh` commit bypass guard end-to-end
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Tests may stub `larch-log` such that regressions in real bypass guard logic ship while CI stays green.
- **Suggested revision**: Add a disposable-repo harness that invokes the real `larch-log.sh commit` with/without `LARCH_LOG_COMMIT_POSTMERGE_SHIP_PR` on `main` with the sentinel present, asserting the intended refusal/allow behavior.

### FINDING_5: Post-merge transient `write-final-report` uses `exit_transient_net` (exit 6) before `PHASE=done`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-capture-pattern-output.txt
- **Concern**: After a successful merge, a transient-classified failure can strand automation in `postmerge` with exit code 6 while non-transient failures record failure and still advance to `done`; docs/tests may promise different parity than shipped behavior.
- **Suggested revision**: Either document and test the contract (including `--resume-phase postmerge` idempotency) or align transient handling with the non-transient branch so phase/exit semantics are consistent for operators.

### FINDING_6: Post-merge flush failures can yield `PHASE=done` / exit 0 while logs remain inconsistent (e.g., `OUTCOME=bailed`)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Non-transient `write-final-report` / `larch-log` commit failures may be best-effort (`record_failure` / warnings) yet the flow still advances to `done` with exit 0, producing “success-shaped” orchestration state alongside stale or misleading committed log fields—undermining audits/automation that assume flush success implies log correctness.
- **Suggested revision**: Decide explicitly: accept as best-effort (document/breadcrumb what operators must inspect), or fail-closed when log commit is enabled (non-zero exit / stall / block `done` until flush succeeds).

### FINDING_7: `is_transient_net_signature "$(cat "$fail_file")"` may hit `ARG_MAX` for huge `fail_file`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Passing the entire captured stderr file as a single argv to a helper is theoretically vulnerable to very large failure blobs (same class of concern called out elsewhere for similar patterns).
- **Suggested revision**: If this is a real threat in your environments, stream/bound the bytes fed into signature classification (or otherwise avoid expanding the whole file into argv).

### FINDING_8: Capturing full `write-final-report.sh` stdout into failure artifacts may amplify sensitive leakage
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Full stdout capture/appends (and downstream transient classification inputs) can duplicate sensitive material into ship-pr failure logs/breadcrumbs beyond any truncation/redaction guarantees.
- **Suggested revision**: Keep stdout as a minimal envelope; route details to stderr with existing redaction, or truncate before append.

### FINDING_9: [OUT_OF_SCOPE] Committed `larch-logs/implement/3890E7C4-…` tree looks like low-signal / placeholder run material in the shipped surface
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-bypass-scope-output.txt, dyn-capture-pattern-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Mixed guidance: some call it intentional chore/noise; others argue it pollutes shipped `larch-logs/` audits/topology with placeholder manifest fields and embedded plan text unrelated to the behavioral fix.
- **Suggested revision**: Resolve per repo run-log policy (revert/remove vs keep), and if kept, ensure manifests meet the repo’s “real flush” bar; otherwise drop from the PR.

### FINDING_10: [OUT_OF_SCOPE] `postmerge_missing_manifest` lacks stronger tail assertions (`status=done`, ordering)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Limited regression signal for post-recovery tail; framed as optional / pre-existing relative to the change.
- **Suggested revision**: Extend assertions only if you want stronger coverage (optional follow-up).

### FINDING_11: [OUT_OF_SCOPE] Non-zero `implement-finalize` post-merge does not abort manifest/report/commit path
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Broad continuation after finalize warnings described as pre-existing, not introduced by this diff.
- **Suggested revision**: Treat as follow-up only if you want stricter abort semantics.

### FINDING_12: [OUT_OF_SCOPE] Extra `skills/implement/SKILL.md` documentation beyond a strict two-file plan scope
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Collateral doc churn with low CI risk; optional to trim for strict plan traceability.
- **Suggested revision**: Keep if helpful cross-doc; otherwise trim to plan scope.

### FINDING_13: [OUT_OF_SCOPE] Test harness unsets `LARCH_QUIET_BREADCRUMB_FD` for reliable greps
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Harness robustness tweak not demanded by the feature/plan; acceptable if it reduces flakes.
- **Suggested revision**: None required for plan fidelity; keep if it stabilizes CI/local runs.

### FINDING_14: [OUT_OF_SCOPE] Collateral documentation updates beyond the plan’s named file list
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Additional touched docs (`skills/implement/SKILL.md`, `scripts/larch-log.md`) beyond “Files to modify” naming only `ship-pr` + `ship-pr.md`.
- **Suggested revision**: Accept as desirable cross-doc alignment; track stricter plan file lists in future plans if desired.

### FINDING_15: [OUT_OF_SCOPE] Plan fidelity / verification evidence gap in the diff itself
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Summarizes that stated plan behaviors appear reflected, while verification commands are not evidenced in the diff (expected); includes “no TSV block when no in-scope findings” meta guidance from that reviewer output.
- **Suggested revision**: None for code correctness; handle via process/runbook if you require diff-evidenced verification.

### FINDING_16: [OUT_OF_SCOPE] Defensive confirmations: established capture pattern, bool gating, and `manifest_ok` skip behavior
- **Reviewer(s)**: dyn-capture-pattern-output.txt
- **Concern**: Confirms the stderr capture / `cat` / transient-signature pattern matches pre-PR `run_pr_create_phase` behavior; `${LARCH_NO_LOGS_COMMIT:-false}` matches validated bool export; initial `final_report_rc=1` correctly prevents commit when `manifest_ok` is false.
- **Suggested revision**: No change required unless you are separately hardening the pre-existing class of issues (see FINDING_7).
```
