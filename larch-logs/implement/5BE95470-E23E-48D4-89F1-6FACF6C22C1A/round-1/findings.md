### FINDING_1: correctness: skills/design/SKILL.md:1541-1617
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] step-5c sentinel is deferred to prose item 6 outside the design-publish.sh fence despite plan requiring in-fence gated write after PLAN_WRITE_OK parse Publish succeeds with PLAN_WRITE_OK=true but step-5c not written yet; pause/resume lands at STEP=5c and re-runs design-publish.sh risking duplicate plan write/rename/log effects Move gated step-5c write into publish fence after parse loop; align tests to require in-fence shell ordering
- **Suggested revision**: Address the concern above.

### FINDING_2: risk-integration: skills/design/SKILL.md:1541-1617
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan required in-fence gated step-5c after PLAN_WRITE_OK parse; implementation keeps step-5c as a separate success-boundary Bash turn outside the publish fence while the audit table still says in-fence gated. Phase 7 turn-reduction goal is only partially met at publish; an orchestrator following item 6 still spends an extra near-empty Bash turn and docs contradict behavior. Fold the gated step-5c write into the publish fence after the parse loop, or update audit table/tests to match the deliberate boundary-local write.
- **Suggested revision**: Address the concern above.

### FINDING_3: risk-integration: scripts/test-design-structure.sh:1914-1926
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] assert_folded_sentinel_writes does not enforce HARD/degraded branch guards on Step 2a.5/2b prelude hosts as the plan test contract required. SIMPLE primary step-2a/step-2a.5 hosts could drift into 2a.5/2b preludes without failing structure tests. Add guard grep assertions tying 2a.5/2b folded writes to classification/degraded anchors; keep SIMPLE writes pinned to the Step 2a entry guard block.
- **Suggested revision**: Address the concern above.

### FINDING_4: risk-integration: scripts/test-design-structure.sh:1424-1431
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] step-5c test only requires PLAN_WRITE_OK and step-5c tokens in markdown prose, not a guarded shell write after publish parsing. A prose-only edit could satisfy the harness while removing the real sentinel write path. Require a Bash fence with guard-before-write ordering for step-5c, or assert lines inside the publish fence after the parse loop.
- **Suggested revision**: Address the concern above.

### FINDING_5: risk-integration: skills/design/scripts/test-design-pause-resume.sh:1114-1131
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Backward-loop direct-review fixture tests save routing to STEP=3 but never exercises design-pause-load.sh on that snapshot. Regression in load-time bypass restoration or pause-requested clearing on backward→direct-review resume would not be caught. Add load assertions mirroring the other new fixtures: no live .pause-requested, STEP=3, bypass markers present.
- **Suggested revision**: Address the concern above.

### FINDING_6: risk-integration: scripts/test-design-structure.sh:1558-1578
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] assert_bash_fences_have_pause_check starts at Step 0c, excluding the Step 0b Q&A-only terminal fence from pause-check scanning. Future removal of pause-check from the Q&A-only contiguous-prefix fence would pass structure tests. Add a dedicated structure assertion for the already-planned Q&A-only Bash block ordering.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: skills/design/SKILL.md:1089-1093
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Step 3 entry unconditionally restores Step 2 bypass markers when missing despite comment limiting this to backward discussion re-entry. First-time Step 3 with missing Step 2 markers could fabricate completion and resume past upstream work. Guard restoration on a re-entry sentinel or add a negative pause/structure test for unintended marker fabrication.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] risk-integration: (branch)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Full branch diff includes unrelated larch-log and Codex launcher test changes from other merged commits. Merge CI/runtime failures may be attributed to Phase 7 while originating elsewhere. Split or clearly label unrelated commits in the PR.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] risk-integration: scripts/design-pause-load.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Phase 7 commit updates pause-load docs but not the script; clearing behavior comes from #3529 on the same branch. Reverting #3529 while keeping Phase 7 would leave docs claiming behavior the script lacks. Ensure #3529 ships with Phase 7 or land the script change in the Phase 7 commit.
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: skills/design/SKILL.md:80-82
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Folded sentinels are written at the next host fence before step bodies are guaranteed complete. A crash or orchestrator halt after the host fence but before LLM work finishes can resume forward and skip discussion/outline/sketch phases while still advancing toward plan publish. Use provisional sentinels until step success or document and test the integrity tradeoff explicitly.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: skills/design/SKILL.md:1084-1093
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Step 3 entry unconditionally recreates Step 2 bypass markers when missing despite prose limiting this to backward re-entry. Reaching Step 3 with absent step-2 markers forges completion and can skip sketches/plan work before plan review. Guard restore behind an explicit re-entry sentinel set only on Gate B(c)/Gate C(b) paths.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: skills/design/SKILL.md:2425-2496
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Step 1d.5 and Step 2a entry batch-write discussion sentinels before downstream brainstorm/sketch work. Pause snapshots taken right after the host fence can encode completed discussion while brainstorm/outline work was still in flight across longer LLM-only gaps. Restrict batch writes to no-brainstorm repair paths or defer promotion until step success boundaries.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: skills/design/SKILL.md:2335-2341
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Q&A-only terminal pause-save omits REPO threading present elsewhere. Fork/upstream-pinned runs may write pause state to the wrong GitHub repo. Add ${REPO:+--repo "$REPO"} to the pause-save invocation.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: skills/design/SKILL.md:649-692
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Step 2a entry writes discussion sentinels before validation failures that exit 1 before pause-check. Corrupt run-params or SIMPLE conflict leaves step-1c..1e set without step-2a; resume/pause metadata implies discussion complete when sketch phase never started. Defer folded discussion writes until after run-params/SIMPLE checks succeed, or unlink markers on those exit paths.
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: skills/design/SKILL.md:649-664 + scripts/design-pause-save.sh:180-186
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] No-brainstorm path has no Bash boundary between step-0c and Step 1d.5 prelude for step-1c/1d. Pause during Step 1c/1d LLM work resumes at STEP=1c and replays Round 1 despite in-session progress. Add a pause host after Step 1d (or at 1d.7 entry) that batch-writes discussion markers before pause-check.
- **Suggested revision**: Address the concern above.

### FINDING_16: architecture: skills/design/SKILL.md:1615-1617
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] step-5c sentinel is prompt-side only, outside design-publish fence. Publish succeeds but orchestrator halts before item 6; resume at STEP=5c with ambiguous re-publish/cleanup state. Move PLAN_WRITE_OK-gated step-5c write into publish fence after parse loop.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: skills/design/SKILL.md:1084-1093
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Step 3 entry always clears step-3..step-4b despite prose limiting to re-entry. Re-run review or mistaken Step 3 re-entry drops step-4 while Gate C pending, widening STEP=4 replay. Guard downstream rm on explicit re-entry sentinel only.
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: skills/design/SKILL.md:76-82
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Crash after host writes absorbed sentinels but before step body completes. 2a entry writes step-1e; crash before step-2a leaves registry prefix lying about progress. Document crash window or narrow which sentinels each host may pre-write.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: skills/design/SKILL.md:452-461
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Q&A-only terminal fence omits step-0c. Terminal branch without prior 0c fence replays symbol grep on resume. Add idempotent step-0c to contiguous-prefix fence.
- **Suggested revision**: Address the concern above.

### FINDING_20: code-quality: scripts/test-design-structure.sh:1383-1395
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Missing HARD-only negative guards for 2a.5/2b hosts. SIMPLE routing regression could satisfy structure tests via wrong host. Assert SIMPLE paths do not use HARD-only prelude hosts as primary writers.
- **Suggested revision**: Address the concern above.

### FINDING_21: correctness: skills/design/SKILL.md:1541-1616
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Step 5c step-5c sentinel is prompt-side (item 6) not in-fence after PLAN_WRITE_OK parse as plan item 20 required On PLAN_WRITE_OK=true the orchestrator may omit a separate Bash turn for step-5c or write it out of order relative to publish parsing; pause/resume can treat 5c incomplete after a successful plan write Add a PLAN_WRITE_OK=true-guarded : > step-5c shell block at the end of the design-publish.sh fence and pin it in assert_folded_sentinel_writes
- **Suggested revision**: Address the concern above.

### FINDING_22: architecture: scripts/test-design-structure.sh:1915-1926
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Structure harness lacks HARD/degraded branch guards for Step 2a.5 and Step 2b prelude marker hosts required by plan test item 3 A SIMPLE-path regression could add unconditional step-2a/2a.5 writes in 2a.5 or 2b preludes without failing CI Extend assert_folded_sentinel_writes with HARD-only guard checks (or explicit skip prose) for 2a.5 and 2b prelude fences
- **Suggested revision**: Address the concern above.

### FINDING_23: correctness: skills/design/scripts/test-design-pause-resume.sh:1114-1131
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Backward-loop direct-review fixture never runs design-pause-load.sh after save Load regressions on the Gate A direct-to-Step-3 route after backward discussion would not be caught Add a load leg asserting LOAD_OK STEP=3 cleared pause-requested and restored step-2a through step-2b.5 markers
- **Suggested revision**: Address the concern above.

### FINDING_24: architecture: scripts/design-pause-load.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan listed script update but branch has no design-pause-load.sh diff vs main Reviewers may assume Phase 7 landed the pause-requested clear when it was already on main; only md changed in a22174d1a Document pre-existence in PR or add a focused regression pin tying Phase 7 to the existing rm line
- **Suggested revision**: Address the concern above.

### FINDING_25: **security** `scripts/design-log-publish.sh:308-325`, `skills/design/scripts/assess-plan-round.sh:171-179` — The new `#3534` deny arms block raw plan-review panel transcripts (`cursor-plan-*-output*.txt`, `codex-primary-plan-*-output*.txt`, `claude-plan-*-output*.txt`) and their sidecars, but plan-quality assessor artifacts remain top-level publishable. `assess-plan-round.sh` writes `claude-plan-assessor-round-<N>.txt`, `codex-plan-assessor-round-<N>.txt`, and `cursor-plan-assessor-round-<N>.txt` (plus `.json` sidecars via `launch-review.sh`) under `$DESIGN_TMPDIR`; none match the new `*-output*` globs because they use the `-assessor-round-` slug. Those files contain full external/Claude reasoning about plan diffs—the same sensitivity class the branch now excludes for panel reviewers—so after merge they become the dominant remaining raw-LLM leak at the design-log publication boundary. **Suggested fix:** Either add explicit top-level deny patterns for `*-plan-assessor-round-*.txt` and `*-plan-assessor-round-*.txt.json` (and document the policy in `SECURITY.md` / `design-log-publish.md`), or state clearly in `SECURITY.md` that assessor transcripts are intentionally public forensics and add a negative test proving they are not accidentally caught by a future broadening of the `*-output*` arms.
- **Reviewer**: dyn-artifact-exclusion-precision-output.txt
- **Concern**: - **security** `scripts/design-log-publish.sh:308-325`, `skills/design/scripts/assess-plan-round.sh:171-179` — The new `#3534` deny arms block raw plan-review panel transcripts (`cursor-plan-*-output*.txt`, `codex-primary-plan-*-output*.txt`, `claude-plan-*-output*.txt`) and their sidecars, but plan-quality assessor artifacts remain top-level publishable. `assess-plan-round.sh` writes `claude-plan-assessor-round-<N>.txt`, `codex-plan-assessor-round-<N>.txt`, and `cursor-plan-assessor-round-<N>.txt` (plus `.json` sidecars via `launch-review.sh`) under `$DESIGN_TMPDIR`; none match the new `*-output*` globs because they use the `-assessor-round-` slug. Those files contain full external/Claude reasoning about plan diffs—the same sensitivity class the branch now excludes for panel reviewers—so after merge they become the dominant remaining raw-LLM leak at the design-log publication boundary. **Suggested fix:** Either add explicit top-level deny patterns for `*-plan-assessor-round-*.txt` and `*-plan-assessor-round-*.txt.json` (and document the policy in `SECURITY.md` / `design-log-publish.md`), or state clearly in `SECURITY.md` that assessor transcripts are intentionally public forensics and add a negative test proving they are not accidentally caught by a future broadening of the `*-output*` arms.
- **Suggested revision**: Address the concern above.

### FINDING_26: **security** `scripts/design-log-publish.sh:309-310` — Top-level exclusion covers `codex-primary-plan-*-output*.txt` but not the legacy basename family `codex-plan-*-output*.txt`. Current producers emit `codex-primary-plan-*` (`skills/design/scripts/dispatch-plan-review-panel.sh:210`), so fresh runs are covered, but pause snapshots restored from older plugin versions (or any residual session files still named `codex-plan-<archetype>-output.txt`) would pass `design_artifact_excluded` and flush raw Codex transcripts into committed `larch-logs/design/`. The branch’s `lib-design-round-artifacts.sh` rename fixed round staging naming but did not add a backward-compat deny arm at the top-level gate. **Suggested fix:** Add `codex-plan-*-output*.txt` (and matching sidecar arms mirroring the `codex-primary-plan-*` set, or a single merged pattern if bash `case` allows) to `design_artifact_excluded`, plus a fixture in `scripts/test-design-log-publish.sh` asserting `codex-plan-arch-output.txt` is denied even when `codex-primary-plan-arch-output.txt` is also present.
- **Reviewer**: dyn-artifact-exclusion-precision-output.txt
- **Concern**: - **security** `scripts/design-log-publish.sh:309-310` — Top-level exclusion covers `codex-primary-plan-*-output*.txt` but not the legacy basename family `codex-plan-*-output*.txt`. Current producers emit `codex-primary-plan-*` (`skills/design/scripts/dispatch-plan-review-panel.sh:210`), so fresh runs are covered, but pause snapshots restored from older plugin versions (or any residual session files still named `codex-plan-<archetype>-output.txt`) would pass `design_artifact_excluded` and flush raw Codex transcripts into committed `larch-logs/design/`. The branch’s `lib-design-round-artifacts.sh` rename fixed round staging naming but did not add a backward-compat deny arm at the top-level gate. **Suggested fix:** Add `codex-plan-*-output*.txt` (and matching sidecar arms mirroring the `codex-primary-plan-*` set, or a single merged pattern if bash `case` allows) to `design_artifact_excluded`, plus a fixture in `scripts/test-design-log-publish.sh` asserting `codex-plan-arch-output.txt` is denied even when `codex-primary-plan-arch-output.txt` is also present.
- **Suggested revision**: Address the concern above.

### FINDING_27: **risk-integration** `scripts/design-log-publish.md:38-42` — The updated doc still claims Cursor/Codex plan-review outputs have no `.stderr`/`.jsonl` producers and omits Codex `.json` from the listed sidecar set, but the code at `scripts/design-log-publish.sh:313-317` now denies Cursor/Codex `.stderr-tail`, `.launch-stderr`, and Codex-primary `.json`, and `SECURITY.md:49-53` documents Codex-primary `.json` exclusion. This doc/code drift is a maintenance hazard: a future contributor trusting `design-log-publish.md` could remove working deny arms believing no producers exist (the exact failure mode that previously leaked `codex-primary-plan-*-output-phase2.txt.json` into committed design logs). **Suggested fix:** Align `design-log-publish.md` with `SECURITY.md` and the live deny arms—list Codex-primary `.json`/`.stderr-tail` as producer-backed exclusions and note that Cursor/Codex do not emit Claude-style standalone `.stderr` or `.jsonl` sidecars on plan-review slots.
- **Reviewer**: dyn-artifact-exclusion-precision-output.txt
- **Concern**: - **risk-integration** `scripts/design-log-publish.md:38-42` — The updated doc still claims Cursor/Codex plan-review outputs have no `.stderr`/`.jsonl` producers and omits Codex `.json` from the listed sidecar set, but the code at `scripts/design-log-publish.sh:313-317` now denies Cursor/Codex `.stderr-tail`, `.launch-stderr`, and Codex-primary `.json`, and `SECURITY.md:49-53` documents Codex-primary `.json` exclusion. This doc/code drift is a maintenance hazard: a future contributor trusting `design-log-publish.md` could remove working deny arms believing no producers exist (the exact failure mode that previously leaked `codex-primary-plan-*-output-phase2.txt.json` into committed design logs). **Suggested fix:** Align `design-log-publish.md` with `SECURITY.md` and the live deny arms—list Codex-primary `.json`/`.stderr-tail` as producer-backed exclusions and note that Cursor/Codex do not emit Claude-style standalone `.stderr` or `.jsonl` sidecars on plan-review slots.
- **Suggested revision**: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] security
- **Reviewer**: dyn-artifact-exclusion-precision-output.txt
- **Concern**: - **security** `scripts/design-log-publish.sh:294-327` — Top-level `*-plan-voter-prompt.txt` files (e.g. `codex-plan-voter-prompt.txt` from `scripts/dispatch-plan-voters.sh:67`) remain publishable; round staging excludes `*-vote-prompt.txt` but the top-level gate does not. Committed design logs already contain these prompt files. Pre-existing gap, not introduced by this branch.
- **Suggested revision**: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-artifact-exclusion-precision-output.txt
- **Concern**: - **architecture** `scripts/lib-design-round-artifacts.sh:8` — The `dyn-*-output.txt` exclude pattern matches no current producer (`cursor-plan-dyn-*-output.txt` and `codex-primary-plan-dyn-*-output.txt` are covered by other arms / the default catch-all). Harmless for publication today but repeats the dead-pattern class the branch fixed for `codex-plan-*` → `codex-primary-plan-*`.
- **Suggested revision**: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] security
- **Reviewer**: dyn-artifact-exclusion-precision-output.txt
- **Concern**: - **security** `scripts/larch-log.sh:85-99` — `round_artifact_included()` ordering looks correct on this branch: the `dyn-*-codex-output-retry*` deny sits before the explicit dynamic-Codex allow and before the broad `*-output*` catch-all; `scripts/test-larch-log.sh` pins the intended include/exclude matrix. No ordering regression found relative to the scout checklist.
- **Suggested revision**: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] security
- **Reviewer**: dyn-artifact-exclusion-precision-output.txt
- **Concern**: - **security** `scripts/design-pause-load.sh:321` — Phase 7’s post-restore `rm -f "$restore_tmp/.pause-requested"` is a positive hardening change (prevents immediate re-pause loops); no defect found.
- **Suggested revision**: Address the concern above.

### FINDING_32: **correctness** `skills/design/SKILL.md:649-692` — Phase 7 moved the Step 2a entry pause-check to the end of the fence (after folded `step-1c`/`step-1d`/`step-1d.7`/`step-1e` writes and the SIMPLE block), but the fence still has `exit 1` paths at lines 665–667 (unreadable `run-params.json`) and 680–682 (SIMPLE artifact conflict) between those sentinel writes and the pause-check. On `main`, pause-check ran immediately after `source-env`, so a `.pause-requested` marker was still honored before those failures; on this branch the fence can write discussion completion markers and then exit without ever reaching `design-pause-save.sh`, dropping the pause at that Bash boundary. **Suggested fix:** After the folded discussion sentinel block (through `step-1e` / conditional `step-1d.5`), run the canonical pause-check before any fail-closed `exit 1` or SIMPLE validation work—or duplicate pause-check on each early-exit path—so every Step 2a entry invocation still honors pause after sentinels are persisted.
- **Reviewer**: dyn-sentinel-before-pause-ordering-output.txt
- **Concern**: - **correctness** `skills/design/SKILL.md:649-692` — Phase 7 moved the Step 2a entry pause-check to the end of the fence (after folded `step-1c`/`step-1d`/`step-1d.7`/`step-1e` writes and the SIMPLE block), but the fence still has `exit 1` paths at lines 665–667 (unreadable `run-params.json`) and 680–682 (SIMPLE artifact conflict) between those sentinel writes and the pause-check. On `main`, pause-check ran immediately after `source-env`, so a `.pause-requested` marker was still honored before those failures; on this branch the fence can write discussion completion markers and then exit without ever reaching `design-pause-save.sh`, dropping the pause at that Bash boundary. **Suggested fix:** After the folded discussion sentinel block (through `step-1e` / conditional `step-1d.5`), run the canonical pause-check before any fail-closed `exit 1` or SIMPLE validation work—or duplicate pause-check on each early-exit path—so every Step 2a entry invocation still honors pause after sentinels are persisted.
- **Suggested revision**: Address the concern above.

### FINDING_33: **correctness** `skills/design/SKILL.md:842-875` — The Step 2a.5 SIMPLE repair fence runs `design-pause-save.sh` at line 844 before any `: > "$DESIGN_TMPDIR/.completed/step-2a"` / `step-2a.5` writes at lines 869–874, violating the Phase 7 folded contract that absorbed sentinel writes must precede pause-check. If pause fires at the repair fence entry while `step-2a.5` is still missing (the common legacy-SIMPLE repair case), the snapshot can persist without that marker even though Step 2a.5 prelude may have already written `step-2a`, so resume can re-enter repair/sketch routing instead of advancing cleanly to Step 2b. **Suggested fix:** Reorder the repair fence to `source-env → mkdir → conditional step-2a/step-2a.5 writes → pause-check`, matching the Step 2a entry / zero-sketch degraded fences, and extend `assert_folded_sentinel_writes` (or add a dedicated guard) so this host is pinned like the other folded hosts.
- **Reviewer**: dyn-sentinel-before-pause-ordering-output.txt
- **Concern**: - **correctness** `skills/design/SKILL.md:842-875` — The Step 2a.5 SIMPLE repair fence runs `design-pause-save.sh` at line 844 before any `: > "$DESIGN_TMPDIR/.completed/step-2a"` / `step-2a.5` writes at lines 869–874, violating the Phase 7 folded contract that absorbed sentinel writes must precede pause-check. If pause fires at the repair fence entry while `step-2a.5` is still missing (the common legacy-SIMPLE repair case), the snapshot can persist without that marker even though Step 2a.5 prelude may have already written `step-2a`, so resume can re-enter repair/sketch routing instead of advancing cleanly to Step 2b. **Suggested fix:** Reorder the repair fence to `source-env → mkdir → conditional step-2a/step-2a.5 writes → pause-check`, matching the Step 2a entry / zero-sketch degraded fences, and extend `assert_folded_sentinel_writes` (or add a dedicated guard) so this host is pinned like the other folded hosts.
- **Suggested revision**: Address the concern above.

### FINDING_34: [OUT_OF_SCOPE] `scripts/test-design-structure.sh:1914-1926` asserts sentinel-before-pause ordering for the Step 2a.5 **prelude** and Step 2b prelude, but does not extract or check the separate SIMPLE repair fence (`skills/design/SKILL.md:842-875`). That leaves the repair-fence ordering gap above uncaught by CI even though Phase 7 documents the global before-pause contract.
- **Reviewer**: dyn-sentinel-before-pause-ordering-output.txt
- **Concern**: - `scripts/test-design-structure.sh:1914-1926` asserts sentinel-before-pause ordering for the Step 2a.5 **prelude** and Step 2b prelude, but does not extract or check the separate SIMPLE repair fence (`skills/design/SKILL.md:842-875`). That leaves the repair-fence ordering gap above uncaught by CI even though Phase 7 documents the global before-pause contract.
- **Suggested revision**: Address the concern above.

### FINDING_35: [OUT_OF_SCOPE] Most other pinned hosts (Step 1d.5 prelude, Step 2a entry SIMPLE guards with `jq`/`brainstorm_requested`, zero-sketch degraded fence, Step 3 entry, Step 5/6 preludes, Step 6 cleanup after-pause exception, Step 5c publish pause-before-`design-publish.sh`) match the plan’s ordering in the current `SKILL.md` text; the Step 2a entry regression and the uncovered repair fence are the material correctness gaps found in this review.
- **Reviewer**: dyn-sentinel-before-pause-ordering-output.txt
- **Concern**: - Most other pinned hosts (Step 1d.5 prelude, Step 2a entry SIMPLE guards with `jq`/`brainstorm_requested`, zero-sketch degraded fence, Step 3 entry, Step 5/6 preludes, Step 6 cleanup after-pause exception, Step 5c publish pause-before-`design-publish.sh`) match the plan’s ordering in the current `SKILL.md` text; the Step 2a entry regression and the uncovered repair fence are the material correctness gaps found in this review.
- **Suggested revision**: Address the concern above.

### FINDING_36: **correctness** `scripts/test-check-reviewers.sh:30-43` — `assert_argv_immediately_after_c` exits on the **first** matching `-c` → `want` pair found in the file and reports pass, regardless of whether `want` also appears at other positions not preceded by `-c`. If `check-reviewers.sh` has a bug where it simultaneously passes a config value correctly via `-c` AND emits it in a different argv position (e.g., as a `--config=value` form, or verbatim as a positional argument), the function would report pass because the first valid adjacency pair was found. For the specific tested values (`model_provider="openai-larch-env"` etc.) this scenario is unlikely in practice, but the assertion is necessary rather than sufficient for the property "config value only appears when preceded by `-c`". The awk `NR > 1` guard is meanwhile technically redundant (an uninitialized `prev` already cannot equal `"-c"`), making the true first-line case dead code; the guard is correct but could mislead a reader into thinking it does more than it does. **Suggested fix:** After the adjacency assertion, add a complementary occurrence-count check: `count=$(grep -Fxc "$config_value" "$argv_file" 2>/dev/null || echo 0); paired=$(awk ... | wc -l)`; assert they are equal, so any extra non-`-c`-adjacent occurrence is caught. Alternatively, use awk to count total occurrences of `want` and compare against total `-c` → `want` pairs.
- **Reviewer**: dyn-test-helper-awk-logic-output.txt
- **Concern**: - **correctness** `scripts/test-check-reviewers.sh:30-43` — `assert_argv_immediately_after_c` exits on the **first** matching `-c` → `want` pair found in the file and reports pass, regardless of whether `want` also appears at other positions not preceded by `-c`. If `check-reviewers.sh` has a bug where it simultaneously passes a config value correctly via `-c` AND emits it in a different argv position (e.g., as a `--config=value` form, or verbatim as a positional argument), the function would report pass because the first valid adjacency pair was found. For the specific tested values (`model_provider="openai-larch-env"` etc.) this scenario is unlikely in practice, but the assertion is necessary rather than sufficient for the property "config value only appears when preceded by `-c`". The awk `NR > 1` guard is meanwhile technically redundant (an uninitialized `prev` already cannot equal `"-c"`), making the true first-line case dead code; the guard is correct but could mislead a reader into thinking it does more than it does. **Suggested fix:** After the adjacency assertion, add a complementary occurrence-count check: `count=$(grep -Fxc "$config_value" "$argv_file" 2>/dev/null || echo 0); paired=$(awk ... | wc -l)`; assert they are equal, so any extra non-`-c`-adjacent occurrence is caught. Alternatively, use awk to count total occurrences of `want` and compare against total `-c` → `want` pairs.
- **Suggested revision**: Address the concern above.

### FINDING_37: **correctness** `scripts/test-check-reviewers.sh:447-449` — The API-key sentinel leak assertion `grep -Fr '<REDACTED-TOKEN>' "$SCRATCH/t10-env-key-false" 2>/dev/null` suppresses all grep stderr. If any file under that directory is unreadable (e.g., `check-reviewers.sh` creates a temp file with restrictive permissions due to a bug), grep exits status 2 (file-read error) rather than 0 (match found). The `if` condition fires only on exit 0, so a genuine sentinel leak in an unreadable file would pass silently rather than fail the test. This turns an undetected permission bug in the production code into a false pass for the security property being checked. **Suggested fix:** Remove `2>/dev/null` or add an explicit existence check before grep; alternatively use `grep -rF ... 2>&1 | grep -v '^grep:'` to suppress only "no such file" noise while preserving read-error output, then check both the exit code and stderr for unexpected errors.
- **Reviewer**: dyn-test-helper-awk-logic-output.txt
- **Concern**: - **correctness** `scripts/test-check-reviewers.sh:447-449` — The API-key sentinel leak assertion `grep -Fr '<REDACTED-TOKEN>' "$SCRATCH/t10-env-key-false" 2>/dev/null` suppresses all grep stderr. If any file under that directory is unreadable (e.g., `check-reviewers.sh` creates a temp file with restrictive permissions due to a bug), grep exits status 2 (file-read error) rather than 0 (match found). The `if` condition fires only on exit 0, so a genuine sentinel leak in an unreadable file would pass silently rather than fail the test. This turns an undetected permission bug in the production code into a false pass for the security property being checked. **Suggested fix:** Remove `2>/dev/null` or add an explicit existence check before grep; alternatively use `grep -rF ... 2>&1 | grep -v '^grep:'` to suppress only "no such file" noise while preserving read-error output, then check both the exit code and stderr for unexpected errors.
- **Suggested revision**: Address the concern above.

### FINDING_38: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-test-helper-awk-logic-output.txt
- **Concern**: - **code-quality** `scripts/test-check-reviewers.sh:30-43` — The `2>/dev/null` on the awk invocation in `assert_argv_immediately_after_c` suppresses awk diagnostic output (e.g., "can't open input file"). When the argv log file is absent (test setup failure), the function correctly calls `fail` via the `else` branch, but the developer sees only the generic label-based message rather than the file-not-found context. This makes debugging setup failures harder but does not create a correctness issue since awk exits non-zero on a missing input file.
- **Suggested revision**: Address the concern above.

### FINDING_39: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-test-helper-awk-logic-output.txt
- **Concern**: - **code-quality** `scripts/test-check-reviewers.sh:19-27` — `assert_no_probe_homes` uses `find "$tmpdir" -maxdepth 1 ... 2>/dev/null || true`. If `$tmpdir` was never created (test-setup failure), `find` errors are silenced and `survivors` is the empty string, causing the function to pass silently. In the current callers, the tmpdir is always created by `run_cr` before this assertion, so this is not a practical concern, but adding a `[[ -d "$tmpdir" ]] || fail "$label: tmpdir missing: $tmpdir"` guard would make setup failures visible.
- **Suggested revision**: Address the concern above.

