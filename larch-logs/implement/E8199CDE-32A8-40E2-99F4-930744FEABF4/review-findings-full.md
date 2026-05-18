### FINDING_10: panel [code-review/accepted]

## correctness: skills/review-and-fix/scripts/review-and-fix.sh:704-719

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Env branch treats set-but-empty LARCH_DYNAMIC_ARCHETYPES_MAX as authoritative Export LARCH_DYNAMIC_ARCHETYPES_MAX= (empty) makes DYNAMIC_ARCHETYPES empty and fails the 0-4 case with exit 2 instead of session-env or default 4 Treat empty env like unset and fall through to session_get or implement default
- **Suggested revision**: Address the concern above.

### FINDING_13: panel [code-review/accepted]

## risk-integration: scripts/write-session-env.md:44-46 vs scripts/session-setup.sh:131-140,405-432

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] session-setup caller-env and WSE_ARGS omit LARCH_DYNAMIC_ARCHETYPES_MAX despite doc requiring session-setup sync session-setup --caller-env --write-session-env drops scout cap from copied session-env Extend session-setup caller-env case and WSE_ARGS forwarding with 0-4 validation
- **Suggested revision**: Address the concern above.

### FINDING_15: panel [code-review/accepted]

## risk-integration: skills/implement/SKILL.md:1350-1352

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Step 5 banners always print cap=4 Operator uses --dynamic-archetypes 0 or 2 but logs still say cap=4 Derive printed cap from resolved dynamic_archetypes_value or session-env
- **Suggested revision**: Address the concern above.

### FINDING_17: panel [code-review/accepted]

## risk-integration: skills/implement/SKILL.md:4

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] argument-hint omits new dynamic reviewer flags Operators miss flags in surfaces driven by argument-hint Extend argument-hint with optional dynamic archetype flags
- **Suggested revision**: Address the concern above.

### FINDING_5: panel [code-review/accepted]

## architecture: scripts/write-session-env.md:44-46

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Edit-in-sync lists subskill-invocation update; branch did not touch skills/shared/subskill-invocation.md New session-env key undocumented in cross-skill invocation guide Add LARCH_DYNAMIC_ARCHETYPES_MAX to subskill-invocation session-env examples
- **Suggested revision**: Address the concern above.

### FINDING_7: panel [code-review/accepted]

## architecture: scripts/write-session-env.md:44-46 scripts/session-setup.sh:131-140

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] New session-env key documented but Edit-in-sync consumers not updated. Caller session-env that sets LARCH_DYNAMIC_ARCHETYPES_MAX is passed as --caller-env into session-setup; the key is dropped by the whitelist so it never reaches implement session-env or write-session-env unless set in the process environment or via /implement flags. Whitelist and forward LARCH_DYNAMIC_ARCHETYPES_MAX in session-setup.sh (validate 0-4) and update subskill-invocation.md per write-session-env.md Edit-in-sync.
- **Suggested revision**: Address the concern above.

### FINDING_9: panel [code-review/accepted]

## correctness: skills/implement/SKILL.md:153 vs skills/review-and-fix/scripts/review-and-fix.sh:700-710

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Skill claims explicit flags override shell LARCH_DYNAMIC_ARCHETYPES_MAX but script prefers process env over session-env. export LARCH_DYNAMIC_ARCHETYPES_MAX=0 with /implement --dynamic-archetypes 4 still yields cap 0 and contradicts SKILL guidance. Align SKILL text with resolution order or pass session value via run-step5-review.sh --dynamic-archetypes / reorder precedence.
- **Suggested revision**: Address the concern above.

### FINDING_1: panel [code-review/accepted]

## **Important** `risk-integration` `skills/implement/SKILL.md:278` drops parent-provided `LARCH_DYNAMIC_ARCHETYPES_MAX` when `/implement` is invoked with `--session-env`. The new handoff contract says parent session-env files may carry `LARCH_DYNAMIC_ARCHETYPES_MAX=&lt;0..4&gt;` (`skills/shared/subskill-invocation.md:167-169`), and `session-setup.sh` only preserves it when it owns `--write-session-env` (`scripts/session-setup.sh:420-422`), but `/implement` rewrites its own session-env and only includes `--dynamic-archetypes` when `dynamic_archetypes_value` came from an explicit `/implement` flag (`skills/implement/SKILL.md:266-279`). Concrete scenario: a parent writes `LARCH_DYNAMIC_ARCHETYPES_MAX=0` to disable scout and invokes `/implement --session-env parent/session-env.sh`; Step 0 drops the key, `scripts/run-step5-review.sh:111-159` sees no session key, and `review-and-fix.sh` defaults back to cap `4`, running dynamic reviewers anyway. Fix by having `/implement` read and validate `LARCH_DYNAMIC_ARCHETYPES_MAX` from the caller `SESSION_ENV_PATH` when no explicit flag was parsed, then pass that value into `write-session-env.sh`, or switch Step 0 to a session-setup/write-session-env path that preserves the validated caller key.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `skills/implement/SKILL.md:278` drops parent-provided `LARCH_DYNAMIC_ARCHETYPES_MAX` when `/implement` is invoked with `--session-env`. The new handoff contract says parent session-env files may carry `LARCH_DYNAMIC_ARCHETYPES_MAX=&lt;0..4&gt;` (`skills/shared/subskill-invocation.md:167-169`), and `session-setup.sh` only preserves it when it owns `--write-session-env` (`scripts/session-setup.sh:420-422`), but `/implement` rewrites its own session-env and only includes `--dynamic-archetypes` when `dynamic_archetypes_value` came from an explicit `/implement` flag (`skills/implement/SKILL.md:266-279`). Concrete scenario: a parent writes `LARCH_DYNAMIC_ARCHETYPES_MAX=0` to disable scout and invokes `/implement --session-env parent/session-env.sh`; Step 0 drops the key, `scripts/run-step5-review.sh:111-159` sees no session key, and `review-and-fix.sh` defaults back to cap `4`, running dynamic reviewers anyway. Fix by having `/implement` read and validate `LARCH_DYNAMIC_ARCHETYPES_MAX` from the caller `SESSION_ENV_PATH` when no explicit flag was parsed, then pass that value into `write-session-env.sh`, or switch Step 0 to a session-setup/write-session-env path that preserves the validated caller key.
- **Suggested revision**: Address the concern above.

### FINDING_5: panel [code-review/accepted]

## correctness: skills/implement/SKILL.md:1348-1352

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Step 5 `dynamic_archetypes_cap` derivation ignores process env tier used by `review-and-fix.sh`. `LARCH_DYNAMIC_ARCHETYPES_MAX=1` in shell, no flags, no session key: review uses cap 1 but breadcrumb can show cap=4. Mirror review-and-fix resolution for the printed cap or document intentional divergence.
- **Suggested revision**: Address the concern above.

### FINDING_6: panel [code-review/accepted]

## correctness: skills/implement/SKILL.md:1348-1352

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Step 5 banner derives dynamic_archetypes_cap only from explicit flags or session-env (fallback 4), ignoring non-empty process env that review-and-fix honors. Operator exports LARCH_DYNAMIC_ARCHETYPES_MAX=1 without persisting it to session-env and without /implement dynamic flags; Step 5 prints cap=4 while review-and-fix uses 1. Mirror review-and-fix resolution in Step 5 prose (include process env) or persist resolved cap to session-env whenever process env is set; align banner with runtime.
- **Suggested revision**: Address the concern above.

### FINDING_7: panel [code-review/accepted]

## correctness: skills/implement/SKILL.md:1348-1352

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Step 5 breadcrumb derivation for dynamic_archetypes_cap ignores process LARCH_DYNAMIC_ARCHETYPES_MAX. review-and-fix.sh uses env before session default; operator with only shell env sees printed cap 4 while scout runs at env N. Mirror review-and-fix priority (env before session fallback) or remove misleading cap from prose.
- **Suggested revision**: Address the concern above.

