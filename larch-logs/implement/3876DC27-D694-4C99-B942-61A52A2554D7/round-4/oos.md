### FINDING_10: [OUT_OF_SCOPE] `resolve_feature_file()` falls through to missing design feature path
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `assess-plan-round.sh` `resolve_feature_file()` falls through to a possibly missing design feature path. Degraded session without feature files gets a non-existent path passed downstream.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Return empty or fail closed when no readable feature file exists.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_11: [OUT_OF_SCOPE] `recover_main_agent_scope_anchor()` degrades to panel-failed on recovery failure
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `run-step3-review.sh` `recover_main_agent_scope_anchor()` degrades `main-agent-vote-required` to `panel-failed` on recovery failure. Missing handoff KV with no recoverable staged anchor skips MainAgent voting entirely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Document as fail-closed or add loop-side fallback so recovery rarely triggers on happy path.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_18: [OUT_OF_SCOPE] `plan-review-feature-context.txt` written without redaction and unused
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `plan-review-feature-context.txt` is written without `redact-secrets` and has no production consumer. Future wiring could inline raw brainstorm text into prompts without additional hardening.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Redact/escape at write time or enforce `emit_untrusted_file_block` at any future reader.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_19: [OUT_OF_SCOPE] Documented Python-default ship driver parity gaps remain open
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-python-default-flip-output.txt
- **Severity**: latent
- **Concern**: Open parity gaps documented for default `python/ship.py` driver (`#3446`, `#3449`). Default-path `/implement` runs inherit documented ship-driver exposure unrelated to scope-anchor fixes. `python/README.md` does not mention these gaps, so operators reading only the Python README may underestimate residual ship-path risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Track/close #3446 and #3449 or keep `LARCH_SHIP_PR_IMPL=bash` until parity is proven.
  - From dyn-python-default-flip-output.txt: `SECURITY.md:96` documents open #3446/#3449 parity gaps as live default-path exposure and documents `LARCH_SHIP_PR_IMPL=bash` rollback accurately; that acknowledgment is not silently closed by this branch. `python/README.md` describes the default flip and bash opt-out but does not mention #3446/#3449, so operators who read only the Python README may underestimate residual ship-path risk.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_23: [OUT_OF_SCOPE] `--read-tools` subprocess path lacks literal-redacted context embedding
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-untrusted-framing-output.txt, dyn-python-default-flip-output.txt
- **Severity**: latent
- **Concern**: `launch-claude-subprocess.sh` `--read-tools` path still `cat`s the base prompt and does not inline or redact `--context-files`; staged files are read raw via Claude `Read` under `staged-context/`. Pre-existing boundary documented in `SECURITY.md:148`, outside embedded `<context_file_N>` hardening added on this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Migrate read-tools path or document as accepted residual risk.
  - From dyn-untrusted-framing-output.txt: The `--read-tools` path still `cat`s the base prompt and does not inline or redact `--context-files`; staged files are read raw via Claude `Read` under `staged-context/`. That predates this branch and is documented separately in `SECURITY.md:148`; it is outside the embedded `<context_file_N>` hardening added here.
  - From dyn-python-default-flip-output.txt: The `--read-tools` branch still embeds only the prompt file and relies on filesystem reads under `--add-dir`; context-body hardening in this branch applies to the legacy `--context-files` embed path. Pre-existing split boundary, not a regression from the scope-anchor work.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_24: [OUT_OF_SCOPE] `assessor_path_valid` requires `DESIGN_TMPDIR` for outputs only
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `assessor_path_valid` requires `DESIGN_TMPDIR` for outputs only. Pre-existing; unrelated to staged-anchor preference.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: No change required for this issue.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_26: [OUT_OF_SCOPE] Brief `LOOP_STATUS=complete` window before `tally-error` rewrite
- **Reviewer(s)**: dyn-scope-anchor-relay-output.txt
- **Severity**: latent
- **Concern**: Inside `_run_plan_review_round`, `LOOP_STATUS` is set to `complete` before the caller rewrites it to `tally-error`. Relay emission is still safe because `larch_scope_anchor_relay_allowed` keys off `TALLY_PLAN_REVIEW_STATUS` first, but the brief `complete`+`tally-error` window is easy to misread when extending the round function.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-anchor-relay-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_27: [OUT_OF_SCOPE] Unit harness lacks direct pins for full `lib-scope-anchor-handoff` relay API
- **Reviewer(s)**: dyn-scope-anchor-relay-output.txt
- **Severity**: latent
- **Concern**: `test-lib-scope-anchor-handoff.sh` exercises only `larch_scope_anchor_retally_handoff_value`; it does not directly test `larch_scope_anchor_relay_allowed` or `larch_scope_anchor_design_handoff_value` (parsed-vs-fallback priority, `panel-failed` / `skipped-empty-findings` terminals). Integration coverage largely compensates for loop/Step 3, but the shared library’s dual-gate API lacks direct regression pins.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-anchor-relay-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_28: [OUT_OF_SCOPE] Re-tally scope-anchor behavior enforced via grep prose pins only
- **Reviewer(s)**: dyn-scope-anchor-relay-output.txt
- **Severity**: latent
- **Concern**: Re-tally scope-anchor behavior is enforced via `grep -Fq` prose pins in `SKILL.md` / `approval-gates.md`, not via a script-level re-tally env refresh harness; this matches the plan’s SKILL-only delta but leaves the highest-risk handoff boundary on prompt discipline rather than executable contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-anchor-relay-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_29: [OUT_OF_SCOPE] Aggregator still raw-cats reviewer findings into prompt
- **Reviewer(s)**: dyn-untrusted-framing-output.txt
- **Severity**: latent
- **Concern**: `aggregate-findings.sh` still raw-catts reviewer findings into the aggregator prompt; `SECURITY.md:89` already treats findings as a separate untrusted surface from scope-anchor inline renderers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-untrusted-framing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_30: [OUT_OF_SCOPE] Trusted base `--prompt-file` still raw-catted before context blocks
- **Reviewer(s)**: dyn-untrusted-framing-output.txt
- **Severity**: latent
- **Concern**: The trusted base `--prompt-file` body is still raw-catted before context blocks; hardening applies to `--context-files` payloads only (pre-existing boundary).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-untrusted-framing-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_33: [OUT_OF_SCOPE] README omits Python-default driver, 3.12 floor, and bash rollback
- **Reviewer(s)**: dyn-python-default-flip-output.txt
- **Severity**: latent
- **Concern**: Top-level `README.md` feature matrix does not mention the Python-default Step 8+ driver, the 3.12 floor, or `LARCH_SHIP_PR_IMPL=bash` rollback, while `docs/installation-and-setup.md`, `docs/configuration-and-permissions.md`, and `AGENTS.md` do. Minor doc-surface inconsistency for operators who start from README only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-python-default-flip-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_34: [OUT_OF_SCOPE] Scope-reduction marker `re.match` vs `startswith` subtle drift risk
- **Reviewer(s)**: dyn-python-default-flip-output.txt
- **Severity**: latent
- **Concern**: Marker detection changed from `norm(cand).startswith("[SCOPE-REDUCTION]")` to `re.match(r"^\[SCOPE-REDUCTION\]", norm(cand))` during consolidation; behavior should be equivalent for normalized candidates, and stdin/file parity is now covered by `test-check-scope-reduction-marker.sh`, but any subtle normalization drift would affect dedup parity in `plan-review-loop.sh` as well. Worth watching, not a confirmed regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-python-default-flip-output.txt: Address the concern above.

Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_6: [OUT_OF_SCOPE] Parallel untrusted-block helpers remain in specialist renderer
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Parallel untrusted-block helpers remain in `render-specialist-prompt.sh` after `lib-untrusted-block.sh` landed. Future security fixes may need duplicate edits across specialist and plan-review renderers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consolidate `render-specialist-prompt` onto `lib-untrusted-block.sh` in a follow-up.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_7: [OUT_OF_SCOPE] Branch bundles large unrelated changes outside scope-anchor plan
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Unrelated changes (Python ship driver, implement skill, review aggregation, and other surfaces outside the #3547 plan) ride on the same branch/PR. Large orthogonal diff complicates review, revert of scope-anchor work, and plan-fidelity certification for #3547-focused reviewers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Prefer splitting or documenting explicit dependency if bundling is intentional.
  - From cursor-specialist-plan-fidelity-output.txt: Split or clearly label non-#3547 commits in the PR description so reviewers can separate scope-anchor work from other landed features.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

