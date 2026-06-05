### FINDING_1: architecture: skills/design/SKILL.md:388-409
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Cancel-route termination moved from in-fence exit 1 to prose-only post-fence abort while the route bash fence exits 0 for cancel routes. Orchestrator omits post-fence stop instruction; sub-steps 3-6 are skipped but Step 0c+ still runs with ROUTE=cancel-title-filter or cancel-reentry-guard, continuing design after a rejection. Add mechanical post-fence bash abort or in-fence exit for cancel routes; keep driver-owned render and orchestrator verbatim summary emit.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/design/scripts/design-route.sh:234-255
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Quiet child stderr bridge duplicated inline in cancel render and resume paths instead of a shared helper per plan emit_diag reference. Future quiet-channel tweak updated in one site but not others; resume/init diagnostics diverge under larch_quiet_init. Extract phase_driver_invoke_quiet_child helper in lib-phase-driver.sh or lib-quiet.sh; call from route and init drivers; pin once in test-design-structure.sh.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/design/scripts/design-route.sh:235-254
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] render_cancel_summary captures _render_rc but always returns 0; variable is unused dead code. No runtime breakage; adds noise for readers and obscures intentional tolerate-render-failure contract. Remove _render_rc capture or document with explicit || true without assignment.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/test-design-structure.sh:1246-1261
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Post-fence handoff pins omit refuse-symlinks and do-not-rely-on-_route_out prose from the plan acceptance list. Contract drift in SKILL.md post-fence text goes undetected until a live cancel run misbehaves. Add grep pins for missing post-fence literals or a minimal cancel-route harness asserting abort before Step 0c.
- **Suggested revision**: Address the concern above.

### FINDING_5: correctness: skills/design/SKILL.md:384-409,509-513
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Cancel routes rely on post-fence prose abort while Step 0c+ is unguarded; fence exits 0 on cancel Orchestrator misses post-fence abort after cancel-title-filter/reentry-guard, skips gated sub-steps 3-6, still runs Step 0c/1c and continues design on a refused issue Add mechanical post-fence bash exit for cancel routes or explicit Step 0c entry guard excluding cancel-* ROUTE values
- **Suggested revision**: Address the concern above.

### FINDING_6: correctness: skills/design/SKILL.md:409
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Post-fence cancel detection forbids stdout fallback but does not define behavior when symlink/missing result-env read fails Symlink or unreadable .design-route-result.env leaves post-fence ROUTE empty; cancel abort skipped despite driver stdout containing ROUTE=cancel-* Abort conservatively on unreadable result-env or document/implement a cancel-only stdout fallback
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: scripts/test-design-structure.sh:1217-1222
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Missing harness pin for ${REPO:+--repo "$REPO"} on both cancel render quiet branches per plan acceptance Future regression drops --repo on one render branch; wrong-repo GitHub upsert on fork/non-default-repo runs without CI failure Add grep pins for ${REPO:+--repo "$REPO"} on both render-final-summary.sh invocations in design-route.sh
- **Suggested revision**: Address the concern above.

### FINDING_8: risk-integration: scripts/test-design-structure.sh:1207-1301
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan-required pin for ${REPO:+--repo "$REPO"} on both cancel render-final-summary.sh quiet branches is missing from test-design-structure.sh despite being in acceptance criteria. A future edit removes repo forwarding from render_cancel_summary; cancel summary upserts target the hub default repo on fork/non-default-repo /design runs and CI stays green. Add grep -Fq '${REPO:+--repo "$REPO"}' "$DESIGN_ROUTE_SH" scoped to render_cancel_summary or both quiet branches.
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: scripts/test-design-structure.sh:1257-1261
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Post-fence pins omit refuse symlinks and Do not rely on _route_out prose required by the plan (present in SKILL.md:409). Post-fence cancel handling reverts to captured stdout KVs or sources a symlinked result-env; cancel abort or ROUTE parsing becomes unreliable without test failure. Add step0b_block greps for refuse symlinks and Do not rely on _route_out after the route fence.
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: skills/design/SKILL.md:388-409
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Cancel routes exit the bash fence with rc=0; unconditional abort before sub-step 3 is orchestrator prose only, not bash-enforced. Orchestrator skips post-fence abort after title-filter or re-entry-guard; /design continues into clarify or init on a route that should terminate. Add offline driver harness or stronger post-fence prose/fence pins; consider mechanical abort if feasible.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: scripts/test-design-structure.sh (absent)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No behavioral harness exercises design-route.sh cancel/resume/render paths despite plan driver smoke list; only structural greps were added. Resume refresh failure emits ROUTE=resume@*, render stdout pollutes KV capture, or cancel wrong-repo upsert regressions ship undetected. Add test-design-route.sh with stubbed children covering cancel exit 0, resume exit 1, and KV stdout isolation.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/test-design-structure.sh:1294-1295
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No line-order pin ensures resume env-refresh exit 1 precedes ROUTE=resume@* emission (unlike cancel emit_cancel_route_result ordering). Refactor emits resume ROUTE before write-design-current-env.sh failure handling; orchestrator resumes with stale env while driver exits 1 inconsistently. Add awk ordering check: exit 1 / resume larch_err before ROUTE="resume@ and emit_route_result.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: scripts/test-design-structure.sh:1227-1244
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] larch_err/larch_errf before render-final-summary.sh ordering inside route_emit_cancel_side_effects is not pinned. Reject banner moves after render; operators see summary side effects before rejection text. Add awk over route_emit_cancel_side_effects asserting larch_err/larch_errf precedes render_cancel_summary.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: scripts/test-design-structure.sh:1298-1301
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] bare_devnull_count >= 2 is a file-wide weak proxy for non-quiet stdout redirection on render/resume children. Unrelated >/dev/null lines mask missing render/resume redirects or cause false failures on unrelated redirects. Scope devnull count to render_cancel_summary and resume write-design-current-env blocks only.
- **Suggested revision**: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] risk-integration: scripts/test-step0b-router-flag-recovery.sh:163-174
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Init recovery harness does not cover new driver-owned contract-drift or env-refresh-failed larch_err paths or quiet FD-4 bridge behavior. Init failure regressions in moved banners or quiet stderr bridging are only caught by manual runs. Extend test-step0b with stub failing write-design-current-env.sh and contract-drift cases asserting stderr content.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: skills/design/SKILL.md:388-409
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Cancel routes no longer exit inside the Step 0b bash fence; abort is prompt-only post-fence while anti-halt pushes continuation after Bash success. Sub-steps 3-6 skip cancel ROUTEs but Step 0c+ has no cancel guard. An orchestrator that continues after the route fence exit 0 without executing the post-fence stop can proceed into Step 0c/1c/full design on issues that should be refused by lifecycle title filter or re-entry guard, defeating those access controls. Add a mechanical cancel stop: post-route bash fence that reads .design-route-result.env with symlink refusal, optionally emits final-summary.md, then exit 1 for cancel-title-filter/cancel-reentry-guard; or restore in-fence exit 1 while keeping driver-owned render/reject side effects.
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: scripts/test-design-structure.sh:1493-1494
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Check 21 still asserts resume env refresh via write-design-current-env.sh in SKILL.md after resume refresh moved to design-route.sh The grep passes on Step 0a references alone so resume refresh could be removed from design-route.sh without failing the harness Retarget Check 21 to design-route.sh resume refresh pins; remove misleading SKILL.md resume assertion
- **Suggested revision**: Address the concern above.

