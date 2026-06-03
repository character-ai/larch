### FINDING_1: Orchestrator skip banner ignores workflow_path vs design_classification mismatch
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Step 3.6 orchestrator pre-read uses `workflow_path` only for skip/HARD breadcrumbs while `design-plan-quality-assessor.sh` aligns to `design_classification` on mismatch. When `workflow_path=SIMPLE` and `design_classification=HARD`, the operator sees a skip breadcrumb (no 🔶) while the driver still runs the full HARD lane (`write-after`, assess, WORSE Continue/Stop). Harness case 19b currently codifies this inconsistent UX.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Apply the same mismatch resolution before banner text or call a shared resolve helper; update test 19b.
  - From cursor-specialist-correctness-output.txt: Apply driver-style disagreement alignment before banner (or derive banner from parsed WORKFLOW_PATH); update test 19b.
  - From cursor-specialist-testing-output.txt: Add classification-aware pre-read matching driver; update apply_step3_6_handoff expectations
  - From cursor-specialist-edge-cases-output.txt: Align orchestrator pre-read with driver mismatch rule for banner and invocation gating.
  - From cursor-specialist-plan-fidelity-output.txt: Before the skip/HARD banner, mirror the driver's alignment rule (if both fields are set and differ, set `_wp` from `_dc` and optionally print the same mismatch `WARN` once). Update case 19b to expect a HARD `🔶` banner (or an explicit "lane follows design_classification" breadcrumb), not `workflow_path=SIMPLE; skipped`.


### FINDING_10: Child stderr merged into stdout before KV parse
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The driver merges stderr into stdout before `parse_kv_from_output` for `read-cursor` and `assess-plan-round`. A child can exit 0 while stderr contains spoof lines like `ASSESSOR_VERDICT=not-worse`, which the driver may write to `.step3.6-assessor.env` and cause the orchestrator to skip WORSE Continue/Stop. Noisy stderr could also mask or interfere with KV parsing if the emit contract regresses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Capture stdout alone for KV parsing; log stderr separately; validate KV values (no newlines) before writing result env.
  - From cursor-specialist-edge-cases-output.txt: Capture stdout/stderr separately; parse stdout only.


### FINDING_12: Pause checkpoint writes ASSESSOR_STATUS=skipped instead of paused
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-bash-shell-correctness-output.txt
- **Severity**: important
- **Concern**: `_assessor_pause_checkpoint` flushes `ASSESSOR_STATUS=skipped` / `ASSESSOR_VERDICT=skipped` before `exec design-pause-save.sh`, unlike the sibling `design-postplan-emit.sh` pause helper which writes `POSTPLAN_EMIT_STATUS=paused`. Mid-driver pause inside `$()` capture can return skipped KVs and the SKILL proceeds to Step 3b instead of halting. After a successful `write-after`, pause leaves `.step3.6-assessor.env` claiming the lane was "skipped" even though partial Step 3.6 artifacts may exist, conflating pause with the non-HARD skip path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Use ASSESSOR_STATUS=paused and handoff guard like design-postplan-emit.sh.
  - From dyn-bash-shell-correctness-output.txt: Add a dedicated settled status (for example `ASSESSOR_STATUS=paused`), document it in `design-plan-quality-assessor.md` and `assessor.md`, and teach the Step 3.6 orchestrator handoff to treat it like postplan's `paused` (no WORSE gate, fail-closed only when status is truly empty).


### FINDING_13: read-cursor failure defaults ROUND_NUM=1 and continues HARD lane
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: On `read-cursor` failure the driver defaults `ROUND_NUM=1` and continues HARD `write-after`/assess. A real cursor at round 2+ with a failed read snapshots/assesses round 1, producing wrong verdict artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Settle cursor-read-failed; skip write-after and assess.


### FINDING_15: Orchestrator handoff docs omit classification-alignment rule
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The driver contract says disagreements follow `design_classification`, but §Orchestrator handoff in `design-plan-quality-assessor.md` only documents a cheap `workflow_path` pre-read for breadcrumbs. That documentation gap allowed the orchestrator/driver banner mismatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add an explicit handoff step: when `workflow_path` and `design_classification` conflict, the orchestrator must align `_wp` to `design_classification` before printing skip/HARD banners (same rule as the driver).


### FINDING_17: Pause not re-checked on driver terminal exit paths
- **Reviewer(s)**: dyn-bash-shell-correctness-output.txt
- **Severity**: important
- **Concern**: Pause is only checked at entry, after HARD `read-cursor`, and immediately before launching assess on the write-after success path. Terminal paths that settle and `exit 0`—`write-after-failed` rollback, `assess-failed`, empty-status assess, and the happy assess tail—never re-check `.pause-requested`, so a pause requested while rollback logging or assess is running is deferred until the driver finishes and the orchestrator moves on.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-shell-correctness-output.txt: Call `_assessor_pause_checkpoint` immediately before every `_write_result_and_emit` on settled exit paths (and after a successful assess return), mirroring the postplan driver's checkpoint spacing.


### FINDING_18: SECURITY.md missing assess-failed trust-boundary entry
- **Reviewer(s)**: dyn-assess-failed-propagation-output.txt
- **Severity**: important
- **Concern**: The branch adds a settled `ASSESSOR_STATUS=assess-failed` path, but the Step 3.6 trust-boundary paragraph in `SECURITY.md` still only names `missing-snapshot`, `degraded-default-open`, and `write-after-failed`. Anyone using `SECURITY.md` as the cross-cutting fail-open catalog will not see `assess-failed`, even though `SKILL.md` and `assessor.md` were updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-assess-failed-propagation-output.txt: Extend the `SECURITY.md` Step 3.6 bullet to include `assess-failed` (assess child failure or empty child KV envelope; log via `append-tool-failure.sh`, settle `ASSESSOR_VERDICT=skipped`, continue to Step 3b with no Continue/Stop prompt), and add `SECURITY.md` to the driver doc "Edit in sync" list in `design-plan-quality-assessor.md`.


### FINDING_19: assessor.md incomplete no-prompt ASSESSOR_STATUS enumeration
- **Reviewer(s)**: dyn-assess-failed-propagation-output.txt
- **Severity**: latent
- **Concern**: `assessor.md` Operator UX adds `assess-failed` but still does not document `ASSESSOR_STATUS=skipped` (non-HARD, pause, round<2) or `missing-snapshot` (`assess-plan-round.sh` preflight), while `SKILL.md:1143` lists all five no-prompt statuses. Gate routing is split across SKILL prose and `assessor.md`; partial updates risk mis-routing readers who load only `assessor.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-assess-failed-propagation-output.txt: Add a short "No Continue/Stop prompt" subsection enumerating every `ASSESSOR_STATUS` that bypasses the WORSE gate (`skipped`, `missing-snapshot`, `write-after-failed`, `assess-failed`, `degraded-default-open`), aligned byte-for-byte with `SKILL.md:1143` and the success-marker list at `SKILL.md:1149`.


### FINDING_21: Missing handoff harness assertion for assess-failed WARN replay
- **Reviewer(s)**: dyn-assess-failed-propagation-output.txt
- **Severity**: latent
- **Concern**: Case 17 asserts `assess-failed` in `.step3.6-assessor.env` and on driver stdout, but unlike write-after-failed (`D3` + handoff) and `EFFECTIVE_ASSESSORS=0` (`D4` + handoff), there is no `apply_step3_6_handoff` assertion that the assess-failed `WARN=` reaches chat when file parse succeeds. The file-parse WARN replay path for the new status is unguarded against regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-assess-failed-propagation-output.txt: Add a handoff mirror case (e.g. `D14B`) that runs `apply_step3_6_handoff` after `ASSESS_STUB_RC=1` and asserts the assess-failure sentence appears in `chat.out`; pin it in `test-design-plan-quality-assessor.md`.


### FINDING_22: D6 handoff case lacks 0/3 WARN dedup and stdout-fallback pins
- **Reviewer(s)**: dyn-harness-mirror-fidelity-output.txt
- **Severity**: latent
- **Concern**: The `EFFECTIVE_ASSESSORS=0` handoff case (`D6`) only checks that `chat.out` contains the substring `0/3 effective assessors`. Unlike the write-after path, it has no companion dedup assertion (cf. `D12`) and no stdout-fallback-only control (cf. `D7B`). If the stdout-merge `WARN)` gate regressed to always replay, duplicate 0/3 lines could reach chat while `D6` still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-mirror-fidelity-output.txt: Add a `D6`-parallel dedup test (expect `grep -Fc` of `ZERO_ASSESSORS_WARN` == 1 after successful file parse) and optionally a symlink or `_assessor_force_stdout` case that asserts the full `ZERO_ASSESSORS_WARN` string via stdout fallback only, mirroring the `D5`/`D12`/`D7B` trio.


### FINDING_6: 0/3 WARN filename mismatch vs assessor.md
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: The 0/3 WARN references `ASSESSOR_VERDICT_ENV` while `assessor.md` cites `assessor-verdict-round-N.env`. Operators following assessor.md may look for the wrong filename when the WARN shows a different path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Align assessor.md prose with the emitted WARN text.


### FINDING_7: assess-plan-round resolve_workflow_path lacks test coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `resolve_workflow_path` in `assess-plan-round.sh` now changes tier resolution to match the driver, but `test-assess-plan-round.sh` was not updated. Legacy or hand-edited run-params with classification/path mismatch could run or skip the assessor differently than expected; the harness still only sets `workflow_path`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend test-assess-plan-round.sh for empty workflow_path + HARD classification and SIMPLE/HARD mismatch; or limit alignment logic to design-plan-quality-assessor.sh only


### FINDING_8: relevant-checks.sh missing driver/harness mapping
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No file mapping in `relevant-checks.sh` for `test-design-plan-quality-assessor.sh`. Future driver-only PRs might skip the dedicated harness under selective relevant-checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add relevant-checks case for driver + harness paths


### FINDING_9: No harness test for --timeout argv forwarding
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No test asserts `--timeout` passthrough from driver to `assess-plan-round.sh`. Regression in `--timeout` forwarding would not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert stub receives forwarded --timeout in harness


