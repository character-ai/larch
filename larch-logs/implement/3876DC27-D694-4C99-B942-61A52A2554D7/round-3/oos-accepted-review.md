### FINDING_17: [OUT_OF_SCOPE] aggregate-findings.sh embeds raw reviewer findings without untrusted framing
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Aggregator still embeds raw reviewer findings without redaction/escaping; only scope-anchor appendix was hardened in this branch. Untrusted reviewer prose in `findings.md` flows verbatim into Codex aggregator prompts on plan-review merge rounds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Apply the same untrusted-block renderer to findings input when touching aggregate-findings (future work).


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_18: [OUT_OF_SCOPE] launch-claude-subprocess.sh --read-tools path lacks untrusted hardening
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-untrusted-escaping-output.txt
- **Severity**: latent
- **Concern**: The `--read-tools` path still embeds prompt bytes verbatim without literal-redacted context wrapping. Scout/read-tools launches can inline unredacted context reachable via `--add-dir` without the new `context_file_N` hardening. Pre-existing; unchanged by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Migrate read-tools prompt assembly to the same redact/escape/framing path as default context-files mode.
  - From cursor-specialist-edge-cases-output.txt: Future hardening if READ_TOOLS + context-files becomes a supported combination.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_19: [OUT_OF_SCOPE] revise-plan-with-waterfall.sh duplicates lib-untrusted-block.sh (security slot)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Local `emit_untrusted_file_block` duplicates `scripts/lib-untrusted-block.sh`. Future security fixes to the shared helper may not reach `revise-plan-with-waterfall` `compose_prompt`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Source lib-untrusted-block.sh from revise-plan-with-waterfall.sh instead of duplicating helpers.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_25: [OUT_OF_SCOPE] render-main-agent-scope-anchor.sh duplicates lib-untrusted-block.sh
- **Reviewer(s)**: dyn-doc-code-parity-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/render-main-agent-scope-anchor.sh:46-50` duplicates the redact/escape logic in `scripts/lib-untrusted-block.sh` instead of sourcing the shared helper; functionally aligned with `SECURITY.md` but increases drift risk (landed in #3548, not new to this delta).
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_27: [OUT_OF_SCOPE] MainAgent re-tally scope-anchor isolation is prose-only
- **Reviewer(s)**: dyn-anchor-state-isolation-output.txt
- **Severity**: latent
- **Concern**: MainAgent re-tally `_RETALLY_SCOPE_ANCHOR_IN` / `_RETALLY_PARSED_SCOPE_ANCHOR_FILE` isolation is prose-only in the orchestrator; there is no script-level enforcement comparable to `plan-review-loop.sh` / `run-step3-review.sh`. Stale-anchor prevention on re-tally depends entirely on the main agent following SKILL instructions.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_28: [OUT_OF_SCOPE] Mid-loop round-summary.env can carry SCOPE_ANCHOR_FILE with empty LOOP_STATUS
- **Reviewer(s)**: dyn-anchor-state-isolation-output.txt
- **Severity**: latent
- **Concern**: Mid-loop `_write_round_summary` calls `_scope_anchor_handoff_value` while global `LOOP_STATUS` is still `complete` from `_run_plan_review_round`, so intermediate `round-summary.env` files can carry `SCOPE_ANCHOR_FILE` with an empty `LOOP_STATUS=` field; terminal gating in `.step3-plan-review-result.env` remains correct, but per-round summaries are inconsistent for downstream readers.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_30: [OUT_OF_SCOPE] dispatch-plan-review-panel and render-specialist-prompt duplicate inline redact/escape helpers
- **Reviewer(s)**: dyn-untrusted-escaping-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/dispatch-plan-review-panel.sh:73-80` and `scripts/render-specialist-prompt.sh:226-237` duplicate inline redact/escape helpers instead of `lib-untrusted-block.sh`; logic currently matches the shared library, but drift could reintroduce inconsistent escaping outside the files this branch centralized.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_31: [OUT_OF_SCOPE] launch-claude-subprocess.sh sources unused lib-scope-anchor-handoff.sh
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Uncommitted working-tree change sources `lib-scope-anchor-handoff.sh` without calling any symbol from it. If committed, `launch-claude-subprocess` gains a fatal dependency on an unrelated lib and on the still-untracked handoff file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Drop the unused source line from launch-claude-subprocess.sh; keep only lib-untrusted-block.sh there.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_33: [OUT_OF_SCOPE] test-render-assessor-prompt exercises weaker validation path than production
- **Reviewer(s)**: dyn-untrusted-escaping-output.txt
- **Severity**: latent
- **Concern**: The harness invokes `render-assessor-prompt.sh` without `--design-tmpdir`, exercising the weaker `larch_scope_anchor_common_shape_ok` fallback instead of the production `larch_scope_anchor_validate_design` containment path; production dispatch always passes `--design-tmpdir` (`dispatch-plan-assessors.sh:69`).
- **Suggested revisions (informational for voters; coder decides)**:

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_6: [OUT_OF_SCOPE] render-specialist-prompt.sh still defines local emit_untrusted_file_block
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `render-specialist-prompt.sh` still defines local `emit_untrusted_file_block` after `lib-untrusted-block.sh` landed. Primary review prompt path remains the odd one out for untrusted-block normalization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Migrate render-specialist-prompt.sh to lib-untrusted-block.sh in a follow-up


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_7: [OUT_OF_SCOPE] Branch bundles large unrelated work with #3547 scope-anchor changes
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The branch bundles substantial non-#3547 work (#3462 Python ship default, `python/ship.py`, `larch-logs` flush, broad docs/python edits) with the scope-anchor follow-up. This increases review surface, merge-conflict risk, and makes it harder to separate unrelated regressions from scoped plan work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consider splitting or clearly sectioning PR/commits by concern
  - From cursor-specialist-edge-cases-output.txt: Track separately; no action required for this PR's scope-anchor goals
  - From cursor-specialist-plan-fidelity-output.txt: Keep #3547 scope isolated in the PR narrative, or split unrelated commits if merge risk matters


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


