### FINDING_22: [OUT_OF_SCOPE] Linter does not scan hooks/, agents/, or python/
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The linter does not scan `hooks/`, `agents/`, or `python/` for raw `codex exec`. New unwired call sites outside scanned trees would not fail `make lint`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Extend scope or document explicit exclusions and periodic audit.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_28: [OUT_OF_SCOPE] `run-external-agent.sh` still outside env-key auth sweep
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `run-external-agent.sh` is still not in the env-key auth sweep. `OPENAI_API_KEY` preference does not apply to any future direct Codex paths through this helper. Follow-up sweep per original OOS; out of plan scope for this PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_31: [OUT_OF_SCOPE] `review-and-fix.sh` omits quota mirror and auth-retry loop
- **Reviewer(s)**: dyn-auth-parity-output.txt
- **Severity**: latent
- **Concern**: The allowlisted Step 5 Codex dispatch path in `review-and-fix.sh` also omits `external_launcher_mirror_quota_from_events` and the `LARCH_EXTERNAL_AUTH_RETRIES` auth-retry loop. This predates the branch and was not introduced by it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-auth-parity-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_4: [OUT_OF_SCOPE] Fourth parallel Codex launcher increases drift risk
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `launch-codex-exec.sh` adds a fourth parallel Codex launcher alongside CI, implement, and review paths. Auth retry timing and metadata semantics can drift across launchers, increasing review burden on every external-tool change. Explicitly out of scope for #3475.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_5: [OUT_OF_SCOPE] Negotiation model-args failure uses distinct exit grammar
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: On `agent-model-args.sh` failure, negotiation exits with the helper RC and does not emit `RESPONSE_FILE=`, unlike other Codex failure paths. Callers expecting exit 2 plus `RESPONSE_FILE=` on all Codex failures may mis-handle model-config errors. Pre-existing and outside this PR focus.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Align model-args failure with auth/exec paths or document distinct exit grammar; pre-existing outside this PR focus.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_8: [OUT_OF_SCOPE] Stale `skills/research/SKILL.md` still describes raw `codex exec`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-auth-parity-output.txt
- **Severity**: latent
- **Concern**: `SKILL.md` still describes Codex launching as bare `codex exec --full-auto -C "$PWD"` even though research lanes now route through `launch-codex-exec.sh` per `research-phase.md`. Misleading operator docs only; not changed in this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Update SKILL.md contract prose when convenient.
  - From cursor-specialist-plan-fidelity-output.txt: Update read-only contract prose when touching research skill docs.
  - From dyn-auth-parity-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

