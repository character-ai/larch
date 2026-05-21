### FINDING_1: correctness: scripts/lib-cursor-launcher-common.sh:167-171
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] find|head|grep tree progress probe runs under inherited pipefail; find often exits 141 after head closes the pipe, so the pipeline status can be non-zero despite a printed path, leaving has_prog false. A developer edits the working tree during resolve-conflict; the first matching path can fail to advance last_prog_ts, so the 180s stall budget can still fire later even though the tree changed, killing a healthy run. Use find -print -quit where portable, or wrap the probe in a subshell with set +o pipefail, or avoid head by reading one line without SIGPIPE (e.g. read -r).
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/launch-cursor-ci.sh:150
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] cursor_launcher_run_stall_monitor is suffixed with || true though the helper is specified to return 0 in all outcomes. Readers infer stall failures are being swallowed at the call site; the suffix adds no behavior when the helper honors its contract. Drop || true or document a concrete non-zero return contract if one is introduced later.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/lib-cursor-launcher-common.sh:199
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Normal exit path always runs rm -f "$tree_baseline" even when tree_baseline is unset for non-tree channels, expanding to rm -f "". On some platforms rm rejects an empty operand; behavior is at least confusing versus tree-only cleanup. Guard with [[ -n "$tree_baseline" ]] && rm -f "$tree_baseline".
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/launch-cursor-ci.sh:180-181
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Unrelated jq read pipeline now ends with || true without rationale. Future edits may hide real parse failures and skip token-record emission silently. Revert or add a short comment explaining the specific set -e interaction being neutralized.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/test-launch-cursor-ci.sh:647-657; larch-logs/implement/D17187C9-6EC5-4231-B141-8D9408547012/plan-goals-test.md:113-117
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Fixture 5 uses a 300s stall threshold while the checked-in plan text still specifies a 3s threshold for the wall-clock regression. Plan readers and future /implement audits see a mismatch between spec and harness and may file false regressions. Update the plan-goals-test / plan narrative to record the intentional threshold bump and why stdout sampling lag required it.
- **Suggested revision**: Address the concern above.

### FINDING_6: risk-integration: scripts/test-launch-cursor-ci.sh:574-686
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] New stall fixtures require python3 for stubs. CI or contributor environments without python3 will skip or fail the whole stall block after the new gate. Document python3 as a harness prerequisite or rewrite stubs without python3.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] code-quality: scripts/launch-cursor-ci.sh:189-192
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Wrapper still exits 0 while emitting LAUNCHER_EXIT via emit_kv; unchanged behavioral contract. Callers must continue to parse emit_kv instead of the process exit code; not introduced by stall detection. No change as part of this review.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: scripts/lib-cursor-launcher-common.sh:167-171
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] find|head progress probe under pipefail can mis-evaluate on SIGPIPE-heavy pipelines. Large or fast-changing trees may yield a non-zero pipeline status while files are still newer than the baseline, so has_prog stays false and a healthy run can be stall-killed. Use a single-shot find form without head truncation under pipefail or temporarily disable pipefail around this probe.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/test-launch-cursor-ci.sh:207-216
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Fixture 5 uses a 300s stall threshold instead of the plan’s 3s for the wall-clock-cap case. Plan-vs-code mismatch for reviewers and later /implement steps. Update plan text or adjust the test to match the agreed spec.
- **Suggested revision**: Address the concern above.

### FINDING_10: architecture: scripts/lib-cursor-launcher-common.sh:133-197
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Stall detection is quantized to the poll interval. Operators may interpret 180s as a hard worst-case bound; actual kill can be up to about threshold plus poll_iv. Document ceil-by-poll in launch-cursor-ci.md.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: scripts/test-launch-cursor-ci.sh:207-226
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Fixture 5 diverges from plan: uses LARCH_CURSOR_CI_STALL_THRESHOLD=300 instead of 3s alongside continuous stdout progress. CI never exercises the planned interaction (3s stall window vs 5s wall-clock with steady stdout); stall could beat wall-clock timeout in production while tests stay green. Restore 3s-threshold coverage with a reliable progress signal or document the spec change and add a separate test for the strict case.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/test-launch-cursor-ci.sh:133-135
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Hard fail entire harness when python3 is missing. Minimal images that previously passed argv-only tests now fail the whole target on missing python3. Skip stall suite with explicit ok/skip or document prerequisite in docs/linting.md.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: scripts/test-launch-cursor-ci.sh:136-205
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No stall tests for bump-classify or changelog-draft despite shared stdout channel. Regression in role-specific argv/prompt wiring could leave those roles untested for stall while fix is covered. Parameterize role in stdout stall tests or add minimal per-role copies.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: scripts/lib-cursor-launcher-common.sh:87-200
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] rm -f "$tree_baseline" runs with empty tree_baseline for non-tree modes; can non-zero under set -e. Future callers without || true could mis-handle exit status; today masked by launch-cursor-ci.sh. Guard rm to tree mode only when baseline path is non-empty.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/test-launch-cursor-ci.sh:153-170
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Tight wall-clock ceilings (<15s/<20s) for stall fixtures. Loaded CI runners may rarely exceed bounds and flake. Widen slack or assert relative bounds with margin.
- **Suggested revision**: Address the concern above.

### FINDING_16: security: scripts/lib-cursor-launcher-common.sh:181-188
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] ps+grep cursor-related processes appended to diag. Unrelated process argv could leak secrets into diag consumed by tooling. Narrow ps scope or redact command field; document sensitivity.
- **Suggested revision**: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] risk-integration: docs/linting.md
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Makefile doc table still omits stall/python/git harness details updated elsewhere. Operators read stale linting.md vs launch-cursor-ci.md. Update docs/linting.md in a follow-up (file not touched here).
- **Suggested revision**: Address the concern above.

### FINDING_18: security: scripts/lib-cursor-launcher-common.sh:180-188
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Stall diagnostics append a broad ps axww snapshot filtered only by a case-sensitive substring match on command text, not ownership or parentage. Unrelated local processes whose argv contains cursor can be copied into OUTPUT.diag and downstream failure surfaces, leaking tokens or other secrets present on those command lines. Remove the broad grep-based snapshot or restrict diagnostics to the known wrapper PID and its descendant process tree only; avoid default argv harvesting from arbitrary processes.
- **Suggested revision**: Address the concern above.

### FINDING_19: security: scripts/lib-cursor-launcher-common.sh:167-171
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Tree stall monitoring uses find on the live tree without disabling symlink follow, so traversal can leave the intended directory via symlink edges. A hostile checkout could steer find into adjacent paths, increasing read surface and surprising operators in shared runners. Use find -P (or document trust boundary and add opt-in hardening) so symlink escapes are not followed during stall polling.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: scripts/launch-cursor-ci.sh:161-164
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Stall snapshots are written raw to OUTPUT.diag before optional redacted ingestion into execution-issues.md. Secrets in captured argv may persist in the full diag file even when execution-issues redaction would have caught common patterns, widening accidental disclosure if diag is copied elsewhere. Stop dumping broad argv into diag, or redact stall snippets with the same redact-secrets pipeline before append.
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] architecture: larch-logs/implement/D17187C9-6EC5-4231-B141-8D9408547012/plan-goals-test.md:113-117
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Committed implement plan text does not match the final stall fixture 5 tuning in the test harness. Misleads future readers auditing the run; does not change runtime behavior. Update only if you edit that run log for accuracy; not required for the feature itself.
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: scripts/lib-cursor-launcher-common.sh:179-193;scripts/launch-cursor-ci.sh:136-151
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Stall monitor kills run-external-agent wrapper PID not inner cursor PID; EXIT trap cannot run after SIGKILL Stall SIGKILL on wrapper can orphan cursor/sleep child; fixtures use exec sleep 300 leaking long-lived processes on CI Kill inner agent PID like run-external-agent timeout path or add cooperative stall kill / published child PID
- **Suggested revision**: Address the concern above.

### FINDING_23: correctness: scripts/lib-cursor-launcher-common.sh:167-171;scripts/launch-cursor-ci.sh:81-83
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Tree stall channel prunes .git for resolve-conflict Legit long .git-only git work with unchanged worktree can hit 180s false stall Include .git for this role or add parallel watcher; document unsupported case
- **Suggested revision**: Address the concern above.

### FINDING_24: architecture: scripts/lib-cursor-launcher-common.sh:93-106
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Silent return 0 disables stall on bad channel threshold or mktemp/touch failure Typo in channel or disk full silently disables early kill Surface diagnostic or fail closed when monitoring cannot start
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: scripts/test-launch-cursor-ci.sh:648-667;larch-logs/implement/D17187C9-6EC5-4231-B141-8D9408547012/plan-goals-test.md:113-118
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Fixture 5 uses 300s stall threshold while plan text still says 3s Misleading reproduction steps for wall-clock vs stall interaction Align docs and test comments with chosen threshold and rationale
- **Suggested revision**: Address the concern above.

### FINDING_26: code-quality: scripts/lib-cursor-launcher-common.sh:199
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] rm -f empty tree_baseline on non-tree modes Spurious rm errors for rm -f "" Guard rm when tree_baseline non-empty
- **Suggested revision**: Address the concern above.

### FINDING_27: code-quality: scripts/launch-cursor-ci.sh:180-181
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] read || true masks read failures beyond jq Token sidecar may be skipped silently Narrow suppression or warn on token extraction failure
- **Suggested revision**: Address the concern above.

### FINDING_28: correctness: Implementation plan Fixture 5; scripts/test-launch-cursor-ci.sh:207-216
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Fixture 5 deviates from planned LARCH_CURSOR_CI_STALL_THRESHOLD=3 The plan explicitly runs fixture 5 with the same 3s stall budget as other fixtures while using --timeout 5 and frequent stdout writes; the test uses 300s instead, so CI no longer validates that a short stall threshold loses to the wall-clock cap under continuous tiny writes. Restore threshold 3 per plan and address flakiness another way, or update the plan to the new parameters and intent.
- **Suggested revision**: Address the concern above.

### FINDING_29: correctness: scripts/lib-cursor-launcher-common.sh:192-199
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] rm -f "$tree_baseline" with empty tree_baseline on stdout/file modes Non-tree modes leave tree_baseline unset to empty; rm may receive an empty path, which is platform-dependent and can error or behave oddly. Only rm when a tree baseline path was created (non-empty tree_baseline in tree mode).
- **Suggested revision**: Address the concern above.

### FINDING_30: correctness: Implementation plan Fixture 1; scripts/test-launch-cursor-ci.sh:150-151; scripts/launch-cursor-ci.sh:189-192
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan says exits non-zero; harness asserts process exit 0 and LAUNCHER_EXIT non-zero Readers expecting the launcher script to exit non-zero on failure will misread the test against the plan; behavior may still be intentional. Align plan wording with LAUNCHER_EXIT vs process exit, or change exit semantics if non-zero process exit is required.
- **Suggested revision**: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] code-quality: scripts/launch-cursor-ci.sh:180-181
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] jq/read pipeline guarded with || true not in plan Unrelated to stall feature; possible pipefail hardening only. Keep or drop based on separate review; not a plan item.
- **Suggested revision**: Address the concern above.

