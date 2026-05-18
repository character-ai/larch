### FINDING_1: **Important** `risk-integration` `skills/implement/SKILL.md:278` drops parent-provided `LARCH_DYNAMIC_ARCHETYPES_MAX` when `/implement` is invoked with `--session-env`. The new handoff contract says parent session-env files may carry `LARCH_DYNAMIC_ARCHETYPES_MAX=<0..4>` (`skills/shared/subskill-invocation.md:167-169`), and `session-setup.sh` only preserves it when it owns `--write-session-env` (`scripts/session-setup.sh:420-422`), but `/implement` rewrites its own session-env and only includes `--dynamic-archetypes` when `dynamic_archetypes_value` came from an explicit `/implement` flag (`skills/implement/SKILL.md:266-279`). Concrete scenario: a parent writes `LARCH_DYNAMIC_ARCHETYPES_MAX=0` to disable scout and invokes `/implement --session-env parent/session-env.sh`; Step 0 drops the key, `scripts/run-step5-review.sh:111-159` sees no session key, and `review-and-fix.sh` defaults back to cap `4`, running dynamic reviewers anyway. Fix by having `/implement` read and validate `LARCH_DYNAMIC_ARCHETYPES_MAX` from the caller `SESSION_ENV_PATH` when no explicit flag was parsed, then pass that value into `write-session-env.sh`, or switch Step 0 to a session-setup/write-session-env path that preserves the validated caller key.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `skills/implement/SKILL.md:278` drops parent-provided `LARCH_DYNAMIC_ARCHETYPES_MAX` when `/implement` is invoked with `--session-env`. The new handoff contract says parent session-env files may carry `LARCH_DYNAMIC_ARCHETYPES_MAX=<0..4>` (`skills/shared/subskill-invocation.md:167-169`), and `session-setup.sh` only preserves it when it owns `--write-session-env` (`scripts/session-setup.sh:420-422`), but `/implement` rewrites its own session-env and only includes `--dynamic-archetypes` when `dynamic_archetypes_value` came from an explicit `/implement` flag (`skills/implement/SKILL.md:266-279`). Concrete scenario: a parent writes `LARCH_DYNAMIC_ARCHETYPES_MAX=0` to disable scout and invokes `/implement --session-env parent/session-env.sh`; Step 0 drops the key, `scripts/run-step5-review.sh:111-159` sees no session key, and `review-and-fix.sh` defaults back to cap `4`, running dynamic reviewers anyway. Fix by having `/implement` read and validate `LARCH_DYNAMIC_ARCHETYPES_MAX` from the caller `SESSION_ENV_PATH` when no explicit flag was parsed, then pass that value into `write-session-env.sh`, or switch Step 0 to a session-setup/write-session-env path that preserves the validated caller key.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/implement/SKILL.md:139-153
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Independent-flags wording conflicts with coupled --no-dynamic-archetypes / --dynamic-archetypes; no both-present rule. Orchestrator ambiguity if both tokens appear in ARGUMENTS. Document equivalence and tie-break or mutual exclusion.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/implement/SKILL.md:144
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] --forked compatibility list omits new dynamic archetype flags. Doc drift vs argument-hint and actual supported combinations. Append flags to the compatibility bullet.
- **Suggested revision**: Address the concern above.

### FINDING_4: correctness: skills/fix-issue/SKILL.md:4-229
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] /fix-issue never documents or forwards dynamic-archetypes flags to the Step 5a /implement Skill argv despite the feature naming /fix-issue alongside /implement. Operators on the /fix-issue entrypoint cannot use documented CLI to disable the scout or set cap N; only ambient env and downstream defaults govern that path unless they inject keys elsewhere. Mirror the existing --no-logs-commit pass-through: extend argument-hint Flags and the Step 5a canonical /implement invocation line with optional --dynamic-archetypes/--no-dynamic-archetypes tokens aligned to skills/implement/SKILL.md.
- **Suggested revision**: Address the concern above.

### FINDING_5: correctness: skills/implement/SKILL.md:1348-1352
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Step 5 `dynamic_archetypes_cap` derivation ignores process env tier used by `review-and-fix.sh`. `LARCH_DYNAMIC_ARCHETYPES_MAX=1` in shell, no flags, no session key: review uses cap 1 but breadcrumb can show cap=4. Mirror review-and-fix resolution for the printed cap or document intentional divergence.
- **Suggested revision**: Address the concern above.

### FINDING_6: correctness: skills/implement/SKILL.md:1348-1352
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Step 5 banner derives dynamic_archetypes_cap only from explicit flags or session-env (fallback 4), ignoring non-empty process env that review-and-fix honors. Operator exports LARCH_DYNAMIC_ARCHETYPES_MAX=1 without persisting it to session-env and without /implement dynamic flags; Step 5 prints cap=4 while review-and-fix uses 1. Mirror review-and-fix resolution in Step 5 prose (include process env) or persist resolved cap to session-env whenever process env is set; align banner with runtime.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: skills/implement/SKILL.md:1348-1352
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Step 5 breadcrumb derivation for dynamic_archetypes_cap ignores process LARCH_DYNAMIC_ARCHETYPES_MAX. review-and-fix.sh uses env before session default; operator with only shell env sees printed cap 4 while scout runs at env N. Mirror review-and-fix priority (env before session fallback) or remove misleading cap from prose.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: skills/implement/SKILL.md:152-153
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] No mutual-exclusion semantics if `--dynamic-archetypes` and `--no-dynamic-archetypes` both appear. Combined flags: scout on/off and persisted cap depend on undocumented parse order. Add explicit rule (abort or last-wins).
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: skills/implement/SKILL.md:152-153
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Both --no-dynamic-archetypes and --dynamic-archetypes can appear without documented resolution. Orchestrator emits both tokens; scout on/off depends on undocumented parse order. Declare last-wins or abort with a mutual-exclusion warning consistent with other flags.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: skills/review-and-fix/scripts/review-and-fix.sh:700-715
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Process-env tier uses non-empty test for LARCH_DYNAMIC_ARCHETYPES_MAX instead of the plan's set-vs-unset guard. An exported empty LARCH_DYNAMIC_ARCHETYPES_MAX skips the env tier and falls through to session-env or default cap 4 in implement mode rather than binding tier-2 then failing validation per the plan snippet. Replace the elif with [[ ${LARCH_DYNAMIC_ARCHETYPES_MAX+x} ]] and assign LARCH_DYNAMIC_ARCHETYPES="$LARCH_DYNAMIC_ARCHETYPES_MAX" before the session_get branch or document and test the chosen empty-export semantics.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: skills/review-and-fix/scripts/review-and-fix.sh:704-705
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Empty `LARCH_DYNAMIC_ARCHETYPES_MAX` export is treated as unset vs plan’s `+x` set-detection. Empty export + session-env=3: code uses 3; strict `+x` empty-bind would differ. Confirm intended semantics in spec or align implementation.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/test-run-step5-review.md:12-14
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Contract doc overstates that forwarding alone makes operator flags override all ambient env. Env-only cap with empty session-env: no argv forwarding; process env still affects `review-and-fix.sh`. Narrow wording to persisted-key + CLI override, or document env-only path.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: skills/fix-issue/SKILL.md:123-133,229
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] /fix-issue skill not updated for dynamic-archetypes flags or session-env propagation despite feature scope naming /fix-issue. Operator expects the same scout cap controls as /implement; only /implement SKILL documents flags and write-session-env wiring, so /fix-issue-driven runs lack documented parity unless args are hand-edited. Mirror implement flag + write-session-env / Step 5 forwarding in fix-issue SKILL, or document that fix-issue only inherits implement defaults unless operator adds flags manually.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: skills/fix-issue/SKILL.md:18-22
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] No /fix-issue flag docs or Step 5a pass-through for dynamic archetypes vs /implement. /requirements: fix-issue path cannot officially set scout cap; behavior is implicit only. Add flags and Step 5a forwarding consistent with --no-logs-commit; extend bail harness if needed.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: skills/fix-issue/SKILL.md:4,skills/fix-issue/SKILL.md:17-21
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] No argument-hint/Flags/Step-5a pass-through for --dynamic-archetypes/--no-dynamic-archetypes unlike other /implement toggles. Operator uses /fix-issue only and wants scout off or a custom cap; must hand-edit Step 5a /implement args. Add flags + Step 5a forwarding (or document that toggles require /implement).
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: skills/review-and-fix/scripts/review-and-fix.sh:700-715
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Empty-string LARCH_DYNAMIC_ARCHETYPES_MAX in the process environment is treated as unset (falls through to session-env/defaults). Profile exports LARCH_DYNAMIC_ARCHETYPES_MAX= to clear; session-env still supplies a cap; behavior differs from a literal reading of process-env priority. Document non-empty-only semantics or use set-test if empty should override session-env.
- **Suggested revision**: Address the concern above.

### FINDING_17: security: skills/review-and-fix/scripts/test-review-and-fix.sh:new harness (~CURSOR_API_KEY line)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Literal CURSOR_API_KEY=test-cursor-key in committed test. False positives from gitleaks/trufflehog-style scanners or org secret policies on CI. Use a clearly non-credential dummy value, external fixture, or scanner allowlist comment per repo policy.
- **Suggested revision**: Address the concern above.

