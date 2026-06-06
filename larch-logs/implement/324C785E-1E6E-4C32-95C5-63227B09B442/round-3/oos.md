### OOS_1: [OUT_OF_SCOPE] run-negotiation-round.sh inline Codex auth duplicates shared launcher patterns
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Inline Codex auth duplicates shared launcher patterns. Plan-intentional; future auth contract changes need manual sync in negotiation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared ephemeral-home/auth helper in a follow-up.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] run-external-agent.sh and unwired codex exec paths remain outside sweep
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-auth-sweep-output.txt, dyn-retry-contract-output.txt
- **Severity**: nit
- **Concern**: Generic wrapper and other unwired `codex exec` paths outside this PR scope still bypass or partially bypass shared auth; follow-up sweep still needed per #3475 OOS. `/research` lanes are largely addressed via `launch-codex-exec.sh` wrapping `run-external-agent.sh`; negotiation remains a deliberate inline site.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Wire remaining call sites per #3475 OOS.
  - From cursor-specialist-edge-cases-output.txt: Follow-up sweep only if centralizing all exec inside one launcher is desired.
  - From dyn-retry-contract-output.txt: This PR does not claim to fix that path.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] launch-codex-exec.sh vs launch-codex-ci.sh auth/retry consolidation deferred
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Heavy overlap with `launch-codex-ci.sh` auth/retry stack. Plan excluded consolidating existing launchers onto `launch-codex-exec.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Defer consolidation to a later refactor PR.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_4: [OUT_OF_SCOPE] lint-codex-exec-auth.sh scanner scope excludes hooks/agents/docs
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Linter scope excludes `hooks/`, `agents/`, and docs/ markdown fences. A future unwired `codex exec` added outside scanned paths would bypass `make lint` until manually discovered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Extend scanner scope or document the explicit allowlist of directories that must remain clean by convention.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_5: [OUT_OF_SCOPE] lint-fix-loop.sh launcher env override lacks path guard
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `LINT_FIX_LOOP_LAUNCH_CODEX_EXEC_SH` env override has no canonical launcher-path guard. Same-UID env injection during `/implement` CI-fix could redirect Codex dispatch to an arbitrary executable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Resolve and verify the launcher path against $SCRIPT_DIR/launch-codex-exec.sh (realpath + basename check), or ignore the override outside test harnesses.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_6: [OUT_OF_SCOPE] research SKILL.md still describes raw codex exec launches
- **Reviewer(s)**: dyn-auth-sweep-output.txt, dyn-linter-coverage-output.txt
- **Severity**: nit
- **Concern**: `skills/research/SKILL.md:53` still describes `/research` Codex lanes as direct `codex exec --full-auto -C "$PWD"` launches while references route through `launch-codex-exec.sh`. Skill entrypoint prose can mislead readers about env-key auth coverage; markdown scanner ignores non-fence prose.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_7: [OUT_OF_SCOPE] run-negotiation-round.sh serial-lock failure branch effectively dead
- **Reviewer(s)**: dyn-auth-sweep-output.txt
- **Severity**: nit
- **Concern**: `run-negotiation-round.sh` treats serial-lock acquisition failure as exit 2 with cleanup, but `external_serial_lock_acquire` fail-opens with `return 0` after exhausting tries. That branch is effectively dead on Darwin today and predates this PR.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### OOS_8: [OUT_OF_SCOPE] jq-less multi-add-dir retry limitation documented but unresolved
- **Reviewer(s)**: dyn-retry-contract-output.txt
- **Severity**: latent
- **Concern**: When `jq` is absent at collector retry time, both launch sites fall back to a single `--add-dir "$META_OUTER_LAUNCHER_WORKDIR"`, even if `.meta` records multiple grants. Multi-dir callers can still lose sandbox grants on retry in jq-less environments.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_9: [OUT_OF_SCOPE] dispatch voter scripts use launch-review.sh not launch-codex-exec.sh
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `dispatch-plan-voters.sh` / `dispatch-code-voters.sh` still use `launch-review.sh` not `launch-codex-exec.sh`. Auth already covered; only `voting-protocol` prose needed updating unless consolidating launchers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Track as follow-up doc alignment or migrate dispatch path in a separate change.
  - From cursor-specialist-edge-cases-output.txt: No functional change required unless consolidating launchers.

---

**Merge summary**: 42 raw inputs → 18 in-scope findings + 9 OOS blocks. Subsumed without separate output: FINDING_42 (verified-OK attestation, not an actionable defect). FINDING_17/28 doc/runtime voter mismatch folded into FINDING_3. FINDING_37 folded into OOS_8 (same jq-less limitation, explicitly OOS-tagged in source). FINDING_35 informational note folded into OOS_2.

Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

