Normalized aggregator output from the supplied reviewer slots. FINDING_6, FINDING_10, and FINDING_13 describe the same ship-pr / auto-background / Step 8+ completion race and are merged below; all other inputs stay separate.

### FINDING_1: lib-quiet.md still uses Family B terminology
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Stage 4 removed shim docs but the Invariants section still labels callers as Family B scripts. Contributors editing lib-quiet after the rip-out may think Family-B pairing rules still apply to larch_err progress lines. Reword to long-running quiet scripts (or list ship-pr/ci-wait/collect-agent-results) and remove Family B terminology.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: SECURITY.md bullet 1 still titled “Live streams”
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Bullet 1 still titled Live streams after live monitor machinery was deleted. Security reviewers may believe FD-3 live breadcrumb streaming remains a runtime surface. Retitle bullet 1 to session breadcrumb directories and match docs/run-logs.md quiet-log publication wording.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] run-step5-review.md still documents monitor pairing until Stage 4
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Sibling doc still claims skill fences carry the monitor pair until Stage 4. After merge an operator reads run-step5-review.md and expects breadcrumb-monitor pairing that SKILL.md no longer documents. Update the contract to foreground-only Step 5 invocation; remove the until Stage 4 sentence. File was not modified on this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] collect-agent-results.md still uses Family B writer wording
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Script sibling docs still call collectors Family B writers. Terminology drift makes Stage 4 completion harder to grep-verify for authors. Replace with neutral blocking-writer wording or a one-line Stage 4 past-tense note.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] .gitleaks.toml allowlist references deleted breadcrumb-monitor tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Allowlist still names deleted test-breadcrumb-monitor files. None functional; adds noise when auditing gitleaks config. Remove the two stale path patterns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Step 8 ship-pr exit routing before full invocation completes
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: After Stage 4 removed Family-B PID wait/monitor coupling, foreground `ship-pr` plus harness auto-background can return Bash early while `ship-pr.sh` is still running (including writes to `ship-pr-state.sh`). Step 8+ then parses exit code, applies the Exit 0–6 matrix, or re-invokes from partial state while anti-halt encourages immediate continuation—without an in-fence wait or script-level overlap guard. That can cause orphan or double `ship-pr`, wrong bail/stall paths, or overlapping git/gh work on one clone (2454-class / #2454-class risk).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: Structure harness gaps for fence-collapsed skill docs
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Stage 4 absence assertions exist only for brainstorm.md and implement SKILL.md, not for other fence-collapsed skill docs the plan names. A contributor reintroduces Family-B fence prose in research-phase.md or plan-review.md; make lint and existing structure harnesses stay green until manual grep at PR close. Port the #3119 hex-encoded grep-absence block (or a shared function) to every orchestrator .md file listed in the plan, starting with research-phase.md, validation-phase.md, plan-review.md, and heavy-worker.md.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: test-collect-agent-results.sh C_OK vs C_DONE label mismatch
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Case comment says C_OK but assert_line label still says C_DONE. Failed harness output shows C_DONE while the case comment says C_OK, slowing triage on collector regressions. Align assert_line label with C_OK (or revert the case id everywhere).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] No CI/make gate for plan final forbidden-token grep
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No automated CI target enforces the plan final grep gate after lint-foreground-markers removal. PR merges with forbidden Family-B strings in un-pinned files if implement close grep is skipped; structure tests only catch regressions where pins exist. Wire a small make target or pre-commit check for the forbidden token set (excluding larch-logs and forensics paths), or expand structure pins per finding #1.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: Round-1 exports session token keys into child process env
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Round-1 exports LARCH_TOKEN_SESSION_ID and related keys into child process env. Same-UID local observers can read session identifiers from child /proc during long runs. Document intent in SECURITY.md or limit exports to helpers that cannot use read-session-env-key.sh.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] SECURITY.md still describes monitor sidecar as publish inputs
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Doc still mentions monitor sidecar filenames as silently skipped publish inputs. Operators may think live monitor files are still produced at runtime. Clarify legacy-only wording in Stage 5 or a small doc-only follow-up.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
