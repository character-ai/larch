### FINDING_1: Step 5c aborts on driver exit 3 despite continue contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-exit-semantics-output.txt, dyn-orchestrator-parse-contract-output.txt
- **Severity**: important
- **Concern**: Step 5c prints the exit-3 “continuing with stdout parse” WARN, then the next unexpected-rc guard treats any rc outside {0,1} as fatal—including rc 3—so the orchestrator aborts before parsing stdout or running items 5–7. When `design-publish.sh` completes the publish tail but `.design-publish-result.env` write fails (driver exit 3), mandatory final-summary emit, step-5c sentinel, and Step 5d/6 are skipped despite stdout still carrying PLAN_WRITE_OK/PUBLISH_OK and the documented {0,1,3} contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Exclude 3 from the unexpected-rc guard; add a structure-test pin on that fence.
  - From cursor-specialist-structure-output-output.txt: Pin unexpected-rc check to exclude 3 or require ne 3 in the guard.
  - From cursor-specialist-correctness-output.txt: Add && "${_publish_rc:-0}" -ne 3 to the unexpected-rc guard or use case on _publish_rc; pin the fenced block in test-design-structure.sh.
  - From cursor-specialist-testing-output.txt: Exclude rc 3 from the unexpected-rc guard or use allow-list {0,1,3}; pin the Bash block in test-design-structure.sh.
  - From cursor-specialist-edge-cases-output.txt: Exclude rc 3 from the unexpected-rc guard or reorder with a case statement; add a structure-test pin so 3 cannot fall through to abort.
  - From cursor-specialist-plan-fidelity-output.txt: Exclude exit 3 from the unexpected-rc guard (e.g. add && _publish_rc -ne 3) so parse and items 5–7 can run.
  - From dyn-bash-exit-semantics-output.txt: **Suggested fix:** Exclude `3` from the unexpected-rc guard, e.g. `if [[ "${_publish_rc:-0}" -ne 0 && "${_publish_rc:-0}" -ne 1 && "${_publish_rc:-0}" -ne 3 ]]; then`, or restructure as an `if/elif` chain (`2` → abort, `3` → warn+continue, `0|1` → parse, else → abort). Add a `test-design-structure.sh` pin on that fence so the prose contract cannot drift again.
  - From dyn-orchestrator-parse-contract-output.txt: **Suggested fix:** Extend the unexpected-rc guard to exclude 3 (e.g. `… -ne 0 && … -ne 1 && … -ne 3`), or use an explicit allowlist `case "${_publish_rc:-0}" in 0|1|3) ;; *) abort ;; esac` before parsing. Add a structural pin in `scripts/test-design-structure.sh` that the Bash fence's abort condition does not match rc=3.


### FINDING_11: Post-install stamp on unverified upgrade-larch install inflates retention priority
- **Reviewer(s)**: dyn-prune-retention-logic-output.txt
- **Severity**: important
- **Concern**: Post-install `write_install_stamp` now runs before stable verification while pruning remains gated on `VERIFIED_TARGET=true`. When verification fails but `claude plugin install` leaves a version-shaped cache directory, that directory receives a fresh `date +%s` stamp even though prune is skipped. On the next successful prune, the orphan ranks as recently installed and can displace legitimately useful rollback directories from the eight-slot retention window—opposite of mtime-based `backfill_install_stamps` semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prune-retention-logic-output.txt: **Suggested fix:** Restrict post-install `write_install_stamp` to the verified-stable path (keep unconditional stamping on the already-latest idempotent branch at lines 357–360), or stamp unverified installs with directory mtime (same semantics as `backfill_install_stamps`) instead of `date +%s`, so failed installs do not inflate retention priority on subsequent prunes.


### FINDING_2: `set +e` after marker write never restored in design-publish.sh
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-exit-semantics-output.txt
- **Severity**: important
- **Concern**: After `design_reentry_marker_write`, `design-publish.sh` runs `set +e` and never restores `set -e` for the remainder of the success tail (~120 lines: upsert, publish capture, post-publish render, rename, final `write_result_env_and_emit`). Upsert/publish lack the plan-specified scoped `set +e`/`set -e` capture blocks used by siblings. Errexit-off persists for unguarded commands, so later failures can fail silently while the driver still exits 0 with a partially applied publish tail; a future `set -e` restore could also change abort-vs-warn semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Restore set -e after marker; wrap upsert and design-log-publish in explicit set +e / set -e subshell capture per plan.
  - From cursor-specialist-correctness-output.txt: Restore set -e after marker; wrap publish and upsert captures in explicit set +e/set -e like design-route.sh.
  - From cursor-specialist-edge-cases-output.txt: Restore set -e after marker handling; use scoped set +e only around upsert and design-log-publish captures (mirror design-route.sh).
  - From dyn-bash-exit-semantics-output.txt: **Suggested fix:** After the marker failure-handling block (after line 206), add `set -e`, then wrap upsert and publish captures in their own `set +e` / `_rc=$?` / `set -e` pairs (matching `design-publish.md` ordering prose), leaving the remainder of the script under `set -euo pipefail`.


### FINDING_3: Doc gates still require `_publish_rc` 0 or 1 only, not {0,1,3}
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Anti-halt reminder (line 29), Final summary block (line 446), and Step 5d post-driver emit gate (line 1381) still gate mandatory final-summary emit on `_publish_rc` 0 or 1 only. After fixing the exit-3 abort guard, an orchestrator following those passages may still omit mandatory verbatim summary emit on exit 3 even when `final-summary.md` exists and stdout carries `FINAL_SUMMARY_PATH`. Harness greps in `test-render-cost-line-callsites.sh` enforce the stale prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Align anti-halt text with rc in {0,1,3} per Step 5c items 5-7.
  - From cursor-specialist-structure-output.txt: Match Step 5d gate wording to item 5 ({0,1,3}).
  - From cursor-specialist-correctness-output.txt: Align those passages with items 5-7 (_publish_rc in {0,1,3}).
  - From cursor-specialist-testing-output.txt: Unify all fences to 0, 1, or 3; update test-render-cost-line-callsites.sh greps accordingly.
  - From cursor-specialist-edge-cases-output.txt: Update Final summary block (and render-cost-line pin if desired) to match Step 5c item 5: non-empty file after driver return when _publish_rc ∈ {0,1,3}.


### FINDING_5: Marker-write failure harness does not assert execution-issues append
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The marker-write failure path in `test-design-publish.sh` does not assert that `execution-issues.md` receives an append-tool-failure entry. Regression could drop Warnings append while the harness still passes (only checks exit 0 and `PLAN_WRITE_OK=true`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert execution-issues.md contains marker-write site after MARKER_STUB_RC=1.


### FINDING_6: Retention harness missing agent-lint exclude entry
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: New `test-upgrade-larch-retention.sh` lacks an `agent-lint.toml` exclude entry. `make lint` / `relevant-checks` agent-lint `--pedantic` may fail on the uncited Makefile-only harness when upgrade-larch files change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add test-upgrade-larch-retention.sh to agent-lint.toml exclude list like test-design-publish.sh.


