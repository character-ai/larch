### FINDING_1: P3119 helper `fail()` text trips breadcrumb-monitor grep gate
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The new regression helper’s `fail()` message embeds the literal substring `breadcrumb-monitor.sh`. Plan close-time grep requires zero `breadcrumb-monitor` hits outside `larch-logs`, `CHANGELOG`, and forensics breadcrumbs. This harness can fail that gate and block PR merge even when skill fences are clean.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_2: Hex-encoded patterns vs literal `fail()` diagnostics
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Hex-encoded detection coexists with literal `fail()` text on line 24, which is inconsistent and harder to maintain: structure failures require decoding hex while the grep gate still matches the literal fail line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Sourced `lib-p3119-fence-absence.sh` lacks script-md sibling
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The sourced library has no sibling `.md` contract unlike peer `lib-*` helpers. `agent-lint` and contributors expect script-md-sibling docs for sourced libraries, increasing discovery and audit cost.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] Stale gitleaks allowlist for removed breadcrumb-monitor tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `.gitleaks.toml` allowlist entries still name deleted `test-breadcrumb-monitor` paths. No functional breakage; dead config noise.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Timeout/autobackground recovery may re-invoke ship-pr before task-notification
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Stage 4 fence collapse removes in-fence shell `background`/`wait` coupling for long-running implement scripts (`ship-pr.sh`, `run-step5-review.sh`, `run-step2-dispatch.sh`), relying on harness auto-background and task-notification. When `ship-pr.sh` exceeds the Bash timeout, the harness auto-backgrounds and returns a non-contract exit; orchestrator prose (including NEVER #16 / Step 8+) can direct same-turn re-invoke without waiting for task-notification, while `AGENTS.md` requires notification-first completion. A prior auto-backgrounded `ship-pr` may still be running, producing dual writers racing on `ship-pr-state.sh` and git, weakening the single-runner invariant and risking interleaved `git`/`gh` publication state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-security-output.txt: Address the concern above.

### FINDING_6: Step 8+ exit routing when Bash `writer_rc` and `ship-pr-state` disagree
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: After timeout or auto-background, Bash may return `124`/`143` while `ship-pr.sh` is still running and `ship-pr-state.sh` has stale `PHASE`/`EXIT_CODE`. Dual exit authority between process exit and state is not reconciled for non-contract Bash exits; orchestrator may follow Bash return, miss Exit 4/6 branches, or Step 18a classification may default `EXIT_CODE` to 0. The Exit 0–6 matrix should key off `EXIT_CODE` and related keys from `ship-pr-state.sh` after a completed invocation; on timeout or in-progress `PHASE`, use NEVER #16 resume—not matrix branches from `writer_rc` alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: `assert_p3119` does not cover all plan grep-gate tokens
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `assert_p3119` omits `LARCH_*` sentinels and `monitor_rc`. Partial fence regression (sentinel exports only) can pass structure tests and mis-route stalls per plan failure mode 3.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: No structural pin for foreground `writer_rc` routing in implement SKILL
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test-implement-structure.sh` does not pin FINDING_1-style foreground `writer_rc` routing. Re-added `monitor_rc` or `LARCH_STATUS_FILE` prose in `skills/implement/SKILL.md` would not fail CI until runtime mis-routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: `skills/research/SKILL.md` omitted from Family-B P3119 fence checks
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `skills/research/SKILL.md` is not in the `assert_p3119` set used by structure tests. Collector Family-B shape could return to research `SKILL.md` without failing structure tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: No dedicated harness for hex-encoded P3119 patterns
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No offline harness exercises hex-encoded pattern pass/fail paths; helper regression (broken `printf` patterns) could noop assertions silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Anti-polling harness does not pin task-notification guidance
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-implement-anti-polling-rule.sh` does not grep-pin new task-notification / auto-background guidance. `AGENTS.md` could lose that text while `make lint` still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Bootstrap doc still references removed foreground-marker linter
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/implement-bootstrap.md:163` still documents `scripts/lint-foreground-markers.sh` DENYLIST after Stage 3 removal. Not on the Stage 4 file list; operators following bootstrap docs may look for a deleted script.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Stale `lint-foreground-markers` pragma in `relevant-checks.sh`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/relevant-checks.sh:137` retains a stale `# lint-foreground-markers: ok` pragma on the `collect-agent-results` case pattern. Harmless for behavior; may confuse grep-based audits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
