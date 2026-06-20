### OOS_1: [OUT_OF_SCOPE] correctness: python/ci_monitor.py:396-433
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Pre-existing: empty_checks_grace=0 maps zero checks to pending; callers outside merge loop not wired by this branch remain hang-prone. Step 10 ci wait or other paths without post-push grace can still poll full budget on zero checks. Wire post-push grace or NO_CHECKS handling into all ship CI wait entrypoints (separate change).
- **Suggested revision**: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] risk-integration: python/ship.py:1428-1510
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Resume with unchanged HEAD does not re-apply post-push grace. Operator retries after no-ci-checks-observed without a new push; monitor polls full CI_WAIT_TIMEOUT_SEC again. Set expect-fresh-ci on resume when prior stall was no-ci-checks-observed, or document manual CI re-trigger before retry.
- **Suggested revision**: Address the concern above.


### OOS_3: [OUT_OF_SCOPE] architecture: python/design_log_ship.py:93,178
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Non-merge passive CI wait still uses empty_checks_grace=0. /implement without --merge could hang 30min on zero-check heads after CI-fix. Wire the same post-push grace logic into design_log_ship passive wait paths.
- **Suggested revision**: Address the concern above.


### OOS_4: correctness: python/ci_agentic_fix.py:285-303
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] Autonomous CI-fix delegate waits without empty-checks grace after a successful push. A fix push that produces zero PR checks still blocks in python/cli.py ci wait for 1800s before the outer ship loop can apply its new grace. Pass --empty-checks-grace config.CI_WAIT_POST_FIX_EMPTY_CHECKS_GRACE_SEC for post-push waits, or use a dedicated bounded post-push wait helper.
- **Suggested revision**: Address the concern above.


