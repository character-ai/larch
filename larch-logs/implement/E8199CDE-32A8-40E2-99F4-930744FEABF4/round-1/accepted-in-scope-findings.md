### FINDING_10: correctness: skills/review-and-fix/scripts/review-and-fix.sh:704-719
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Env branch treats set-but-empty LARCH_DYNAMIC_ARCHETYPES_MAX as authoritative Export LARCH_DYNAMIC_ARCHETYPES_MAX= (empty) makes DYNAMIC_ARCHETYPES empty and fails the 0-4 case with exit 2 instead of session-env or default 4 Treat empty env like unset and fall through to session_get or implement default
- **Suggested revision**: Address the concern above.


### FINDING_13: risk-integration: scripts/write-session-env.md:44-46 vs scripts/session-setup.sh:131-140,405-432
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] session-setup caller-env and WSE_ARGS omit LARCH_DYNAMIC_ARCHETYPES_MAX despite doc requiring session-setup sync session-setup --caller-env --write-session-env drops scout cap from copied session-env Extend session-setup caller-env case and WSE_ARGS forwarding with 0-4 validation
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: skills/implement/SKILL.md:1350-1352
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Step 5 banners always print cap=4 Operator uses --dynamic-archetypes 0 or 2 but logs still say cap=4 Derive printed cap from resolved dynamic_archetypes_value or session-env
- **Suggested revision**: Address the concern above.


### FINDING_17: risk-integration: skills/implement/SKILL.md:4
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] argument-hint omits new dynamic reviewer flags Operators miss flags in surfaces driven by argument-hint Extend argument-hint with optional dynamic archetype flags
- **Suggested revision**: Address the concern above.


### FINDING_5: architecture: scripts/write-session-env.md:44-46
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Edit-in-sync lists subskill-invocation update; branch did not touch skills/shared/subskill-invocation.md New session-env key undocumented in cross-skill invocation guide Add LARCH_DYNAMIC_ARCHETYPES_MAX to subskill-invocation session-env examples
- **Suggested revision**: Address the concern above.


### FINDING_7: architecture: scripts/write-session-env.md:44-46 scripts/session-setup.sh:131-140
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] New session-env key documented but Edit-in-sync consumers not updated. Caller session-env that sets LARCH_DYNAMIC_ARCHETYPES_MAX is passed as --caller-env into session-setup; the key is dropped by the whitelist so it never reaches implement session-env or write-session-env unless set in the process environment or via /implement flags. Whitelist and forward LARCH_DYNAMIC_ARCHETYPES_MAX in session-setup.sh (validate 0-4) and update subskill-invocation.md per write-session-env.md Edit-in-sync.
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: skills/implement/SKILL.md:153 vs skills/review-and-fix/scripts/review-and-fix.sh:700-710
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Skill claims explicit flags override shell LARCH_DYNAMIC_ARCHETYPES_MAX but script prefers process env over session-env. export LARCH_DYNAMIC_ARCHETYPES_MAX=0 with /implement --dynamic-archetypes 4 still yields cap 0 and contradicts SKILL guidance. Align SKILL text with resolution order or pass session value via run-step5-review.sh --dynamic-archetypes / reorder precedence.
- **Suggested revision**: Address the concern above.


