### FINDING_1: **Important** `risk-integration` — `scripts/session-setup.sh:131`  
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` — `scripts/session-setup.sh:131`      The new `LARCH_DYNAMIC_ARCHETYPES_MAX` session-env key is written by `scripts/write-session-env.sh`, but `scripts/session-setup.sh:131-140` still ignores it when reading `--caller-env`, and `scripts/session-setup.sh:409-432` never forwards it into the child session env. Concrete failing scenario: a parent session-env contains `LARCH_DYNAMIC_ARCHETYPES_MAX=0`, `session-setup.sh --caller-env ... --write-session-env ...` drops the key, then `skills/review-and-fix/scripts/review-and-fix.sh:708-713` sees no session value and defaults `/implement` review rounds back to `4`, launching the scout despite the inherited disable. Add a `CALLER_DYNAMIC_ARCHETYPES_MAX` parse/pass-through path, validate `0..4`, pass `--dynamic-archetypes "$CALLER_DYNAMIC_ARCHETYPES_MAX"` to `write-session-env.sh`, and cover it in the session-env roundtrip tests/docs.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] correctness: skills/review/scripts/review-core.sh:30-65
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Same empty-env edge as review-and-fix for LARCH_DYNAMIC_ARCHETYPES_MAX Direct review-core invocations with empty exported var fail validation Align review-core env handling with review-and-fix if env-based config is supported (file not in diff)
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] risk-integration: skills/fix-issue/SKILL.md:229
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] No pass-through of dynamic reviewer flags to /implement in Step 5a template Cannot disable scout from /fix-issue argv without env or custom args Forward flags in fix-issue Step 5a if product requires (not introduced by this diff)
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] risk-integration: skills/fix-issue/SKILL.md:4-6 227-229
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] /fix-issue entrypoint lacks documented pass-through for new archetype flags though feature_description names fix-issue. Default cap=4 still applies via /implement delegation; disabling scout from /fix-issue needs env override or non-canonical args. Extend implementation plan and fix-issue SKILL if first-class /fix-issue flags are required.
- **Suggested revision**: Address the concern above.

### FINDING_5: architecture: scripts/write-session-env.md:44-46
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Edit-in-sync lists subskill-invocation update; branch did not touch skills/shared/subskill-invocation.md New session-env key undocumented in cross-skill invocation guide Add LARCH_DYNAMIC_ARCHETYPES_MAX to subskill-invocation session-env examples
- **Suggested revision**: Address the concern above.

### FINDING_6: architecture: scripts/write-session-env.md:44-46
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Edit-in-sync list not reflected in skills/shared/subskill-invocation.md for the new key. Consumer docs omit propagation guidance for the new session-env field. Update subskill-invocation.md per repo contract.
- **Suggested revision**: Address the concern above.

### FINDING_7: architecture: scripts/write-session-env.md:44-46 scripts/session-setup.sh:131-140
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] New session-env key documented but Edit-in-sync consumers not updated. Caller session-env that sets LARCH_DYNAMIC_ARCHETYPES_MAX is passed as --caller-env into session-setup; the key is dropped by the whitelist so it never reaches implement session-env or write-session-env unless set in the process environment or via /implement flags. Whitelist and forward LARCH_DYNAMIC_ARCHETYPES_MAX in session-setup.sh (validate 0-4) and update subskill-invocation.md per write-session-env.md Edit-in-sync.
- **Suggested revision**: Address the concern above.

### FINDING_8: architecture: skills/implement/SKILL.md:152-153
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] No mutex or precedence between --no-dynamic-archetypes and --dynamic-archetypes N Both flags present; outcome depends on undocumented parse order Document last-wins or abort with explicit warning like other mutex flags
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: skills/implement/SKILL.md:153 vs skills/review-and-fix/scripts/review-and-fix.sh:700-710
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Skill claims explicit flags override shell LARCH_DYNAMIC_ARCHETYPES_MAX but script prefers process env over session-env. export LARCH_DYNAMIC_ARCHETYPES_MAX=0 with /implement --dynamic-archetypes 4 still yields cap 0 and contradicts SKILL guidance. Align SKILL text with resolution order or pass session value via run-step5-review.sh --dynamic-archetypes / reorder precedence.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: skills/review-and-fix/scripts/review-and-fix.sh:704-719
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Env branch treats set-but-empty LARCH_DYNAMIC_ARCHETYPES_MAX as authoritative Export LARCH_DYNAMIC_ARCHETYPES_MAX= (empty) makes DYNAMIC_ARCHETYPES empty and fails the 0-4 case with exit 2 instead of session-env or default 4 Treat empty env like unset and fall through to session_get or implement default
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: skills/review-and-fix/scripts/review-and-fix.sh:704-719
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Empty-but-set LARCH_DYNAMIC_ARCHETYPES_MAX errors at validation. Operator runs with export LARCH_DYNAMIC_ARCHETYPES_MAX= ; review-and-fix hits the env branch with an empty value and exits 2 before review-core runs. Treat empty env like unset before the [0-4] case, or skip the env branch when the value is empty.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/test-session-env-roundtrip.sh:194-219; skills/implement/scripts/test-implement-review-token-propagation.sh:75-120
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No automated tests added for new write-session-env validation or review-core forwarding of --dynamic-archetypes. Regression could drop flag wiring or validation without CI failure. Extend test-session-env-roundtrip.sh and stub-capture assertions in test-implement-review-token-propagation.sh.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: scripts/write-session-env.md:44-46 vs scripts/session-setup.sh:131-140,405-432
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] session-setup caller-env and WSE_ARGS omit LARCH_DYNAMIC_ARCHETYPES_MAX despite doc requiring session-setup sync session-setup --caller-env --write-session-env drops scout cap from copied session-env Extend session-setup caller-env case and WSE_ARGS forwarding with 0-4 validation
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: skills/fix-issue/SKILL.md:16-22,229
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] /fix-issue does not document or forward --dynamic-archetypes/--no-dynamic-archetypes to Step 5a /implement despite feature text naming fix-issue. Operators cannot disable scout or set cap from /fix-issue while other flags pass through; behavior diverges from /implement ergonomics. Mirror implement: add Flags bullets and optional tokens in the Step 5a /implement argv template.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: skills/implement/SKILL.md:1350-1352
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Step 5 banners always print cap=4 Operator uses --dynamic-archetypes 0 or 2 but logs still say cap=4 Derive printed cap from resolved dynamic_archetypes_value or session-env
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: skills/implement/SKILL.md:153
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] --dynamic-archetypes parsing lacks mechanical next-token rules Malformed argv may bind feature text as N or leave value unset Add explicit parse steps and validation before treating remainder as FEATURE_DESCRIPTION
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: skills/implement/SKILL.md:4
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] argument-hint omits new dynamic reviewer flags Operators miss flags in surfaces driven by argument-hint Extend argument-hint with optional dynamic archetype flags
- **Suggested revision**: Address the concern above.

