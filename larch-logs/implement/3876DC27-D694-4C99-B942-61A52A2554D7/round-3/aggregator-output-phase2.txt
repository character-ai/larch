### FINDING_1: revise-plan-with-waterfall.sh duplicates lib-untrusted-block helpers
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `revise-plan-with-waterfall.sh` keeps local redact/emit helpers while other renderers migrate to `scripts/lib-untrusted-block.sh`. If redact-secrets or escaping rules change in the shared library, revise prompts can diverge from scout/voter/assessor/subprocess surfaces on the same run, reintroducing delimiter or redaction inconsistency.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Source lib-untrusted-block.sh and replace local emit_untrusted_file_block with larch_emit_untrusted_file_block per plan Item 3
  - From cursor-specialist-edge-cases-output.txt: Source lib-untrusted-block.sh and remove local copies.

### FINDING_2: plan-review-loop.sh inline Python duplicates scope-reduction marker regexes
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Inline Python in `plan-review-loop.sh` duplicates scope-reduction candidate regexes; parity `prob()` adds extra `what:` scanning that `problem_text()` lacks. Future marker-format tweaks can update `check-scope-reduction-marker.sh` while dedup tokenization or parity checks behave differently, causing false dedup merges or parity fallbacks to pre-dedup snapshots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Delegate marker semantics to the shell helper only or extract one shared Python module; remove divergent inline regex copies

### FINDING_3: larch_scope_anchor_relay_allowed reads global status variables
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `larch_scope_anchor_relay_allowed` reads global `LOOP_STATUS`/`TALLY_PLAN_REVIEW_STATUS` instead of parameters. A new caller that sets status under different variable names or before globals are assigned could omit or mis-gate `SCOPE_ANCHOR_FILE` without compile-time failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Pass tally_status and loop_status as explicit function arguments

### FINDING_4: validate_design_prompt_file reimplements scope-anchor path rules
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `validate_design_prompt_file` in `render-plan-review-prompt.sh` reimplements scope-anchor path rules already in `lib-scope-anchor-handoff.sh`. Validation limits (64KiB, under-tmpdir, non-symlink) can drift between `render-plan-review-prompt` and `render-assessor-prompt`/`run-step3-review`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Use larch_scope_anchor_validate_design for --feature-file validation

### FINDING_5: Inconsistent symlink/canonicalization policy for scope-anchor paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Inconsistent symlink/canonicalization policy between revise validation and `lib-scope-anchor-handoff` validators. A symlinked scope-anchor path accepted by one consumer and rejected by another breaks handoff on edge-case tmpdir layouts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Unify on lib-scope-anchor-handoff validation helpers with one documented symlink policy

### FINDING_6: [OUT_OF_SCOPE] render-specialist-prompt.sh still defines local emit_untrusted_file_block
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `render-specialist-prompt.sh` still defines local `emit_untrusted_file_block` after `lib-untrusted-block.sh` landed. Primary review prompt path remains the odd one out for untrusted-block normalization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Migrate render-specialist-prompt.sh to lib-untrusted-block.sh in a follow-up

### FINDING_7: [OUT_OF_SCOPE] Branch bundles large unrelated work with #3547 scope-anchor changes
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The branch bundles substantial non-#3547 work (#3462 Python ship default, `python/ship.py`, `larch-logs` flush, broad docs/python edits) with the scope-anchor follow-up. This increases review surface, merge-conflict risk, and makes it harder to separate unrelated regressions from scoped plan work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consider splitting or clearly sectioning PR/commits by concern
  - From cursor-specialist-edge-cases-output.txt: Track separately; no action required for this PR's scope-anchor goals
  - From cursor-specialist-plan-fidelity-output.txt: Keep #3547 scope isolated in the PR narrative, or split unrelated commits if merge risk matters

### FINDING_8: Shared lib-scope-anchor-handoff.sh and lib-untrusted-block.sh are sourced but not committed
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-doc-code-parity-output.txt, dyn-untrusted-escaping-output.txt
- **Severity**: important
- **Concern**: Committed scripts source `scripts/lib-scope-anchor-handoff.sh` and `scripts/lib-untrusted-block.sh`, but neither file is in any branch commit (only untracked on disk). Fresh checkout/CI runs of `plan-review-loop`, `run-step3-review`, `render-assessor-prompt`, `launch-claude-subprocess`, `aggregate-findings`, and dependent harnesses fail immediately on missing `source` before scope-anchor relay or untrusted rendering runs. `SECURITY.md` claims centralized literal-redacted rendering and terminal-gated `SCOPE_ANCHOR_FILE` relay, but the implementing libraries are absent from `HEAD`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Commit both library scripts to the branch and add a structure pin so sourced helpers cannot be omitted again.
  - From cursor-specialist-testing-output.txt: Add and commit both library files; wire relevant-checks direct targets for them.
  - From cursor-specialist-plan-fidelity-output.txt: Add, commit, and ship both scripts/lib-scope-anchor-handoff.sh and scripts/lib-untrusted-block.sh (plus any contract docs) before merge; verify make test-plan-review-loop and related targets on a clean checkout.
  - From dyn-doc-code-parity-output.txt: Add both libraries to the shipped tree (with `.md` contracts and harness coverage), register them in relevant checks, and cross-reference them from `SECURITY.md` as the mechanical enforcement layer for inline renderers and path-only handoffs.
  - From dyn-untrusted-escaping-output.txt: Add and commit both helper scripts (and register them in the plugin ship surface / relevant harness copies) before merge; add a CI check that every `source …/lib-untrusted-block.sh` and `source …/lib-scope-anchor-handoff.sh` path exists in the tree.

### FINDING_9: Case-sensitive SCOPE-REDUCTION stripping breaks dedup parity
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `comparison_text()` strips `[SCOPE-REDUCTION]` case-sensitively after this branch, while the parity-check Python block still uses `re.I`. A finding with `[scope-reduction]` casing keeps the marker in `comparison_text` tokens but may still be scope-tagged elsewhere, so Jaccard dedup treats it as distinct from an identical `[SCOPE-REDUCTION]` finding. Non-canonical casing may also fail dedup parity and leave duplicate scope-reduction findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Restore case-insensitive SCOPE-REDUCTION stripping in comparison_text or centralize marker normalization before dedup.
  - From cursor-specialist-edge-cases-output.txt: Align case rules with check-scope-reduction-marker.sh; add regression fixture.

### FINDING_10: Single-pass tally-error leaves LOOP_STATUS=complete
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Legacy single-pass tally-error leaves `LOOP_STATUS=complete`; multi-round sets `LOOP_STATUS=tally-error`. `SCOPE_ANCHOR_FILE` is correctly omitted, but downstream logs show `complete`+`tally-error` together and can be misread as a successful terminal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Align single-pass LOOP_STATUS on tally-error or document the intentional asymmetry in plan-review-loop.md.

### FINDING_11: No relevant-checks mapping for new shared library files
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No direct `relevant-checks.sh` mapping exists for the new shared lib files. Lib-only security or relay-contract edits can merge without running dependent harnesses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Map lib-untrusted-block and lib-scope-anchor-handoff to test-plan-review-loop, test-run-step3-review, test-launch-claude-subprocess, test-render-assessor-prompt, and test-dispatch-plan-assessors.

### FINDING_12: test-render-assessor-prompt.sh never passes --design-tmpdir
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The assessor prompt harness never passes `--design-tmpdir`, so production path-containment validation (`larch_scope_anchor_validate_design`) is untested. An outside-path feature file could regress in `dispatch-plan-assessors` without `test-render-assessor-prompt` failing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add --design-tmpdir success and outside-path rejection cases mirroring dispatch-plan-assessors.sh.
  - From cursor-specialist-plan-fidelity-output.txt: Extend the harness to pass --design-tmpdir "$TMP" and add a case where --feature-file points at $TMP/plan-review-scope-anchor.txt with assertions on framing and literal-redacted output.

### FINDING_13: Loop harness lacks CR/LF SCOPE_ANCHOR_FILE rejection case
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Loop harness lacks a CR/LF-parsed `SCOPE_ANCHOR_FILE` rejection case required by plan edge cases. A malicious or malformed tally stdout KV with embedded CR/LF could persist through loop relay undetected by loop-level regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a tally stub emitting SCOPE_ANCHOR_FILE with CR/LF on ok and assert stdout/result env omit the key.

### FINDING_14: Re-tally SCOPE_ANCHOR_FILE refresh is prose-pinned only
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Re-tally `SCOPE_ANCHOR_FILE` refresh is prose-pinned only, not behaviorally tested. Stale-anchor or missing-KV re-tally regressions in SKILL orchestration could slip past CI despite documentation pins.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a behavioral fence case with re-tally stub stdout for ok vs tally-error and dual env file assertions.

### FINDING_15: Assessor prompts raw-cat plan bodies without redact/escape
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-untrusted-escaping-output.txt
- **Severity**: important
- **Concern**: Assessor prompts redact/escape the feature block but still raw-cat `PLAN_ORIGINAL`/`PLAN_PREV`/`PLAN_CURRENT` into markdown fences without `redact-secrets` or delimiter escaping. Plan text copied from a GitHub issue can embed secrets or instruction-like lines; `dispatch-plan-assessors` forwards the rendered prompt to external Codex/Cursor assessors, leaking secrets or enabling fence-breakout injection adjacent to hardened feature blocks and above required output grammar.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Render all three plan inputs through larch_untrusted_redact_stream / larch_emit_untrusted_file_block (or equivalent) and add harness cases for secrets and delimiter-like plan content.
  - From cursor-specialist-security-output.txt: Replace markdown fences with literal-redacted escaped untrusted blocks for external assessor plan evidence.
  - From dyn-untrusted-escaping-output.txt: Render all three plan inputs through the same redact-then-escape pipeline used for `feature_file` (or use length-matched fenced blocks with explicit untrusted framing), and add harness cases for fence-breakout and fake `ASSESSMENT:` injection in plan fixtures.

### FINDING_16: MainAgent re-tally SCOPE_ANCHOR_FILE refresh is orchestrator-prose-only
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: MainAgent re-tally `SCOPE_ANCHOR_FILE` refresh is orchestrator-prose-only; loop/run-step3 use mechanical `lib-scope-anchor-handoff` gating. After `main-agent-vote-required`, an orchestrator that reuses exported `SCOPE_ANCHOR_FILE` without parsing re-tally stdout on tally-error or omits KV on ok can write stale anchor paths into refreshed `.step3-plan-review-result.env` / `.step3-review-result.env`, widening downstream pre-vote render scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Move re-tally scope-anchor persist logic into a shell helper mirroring _scope_anchor_handoff_value and invoke it from the re-tally path; add an integration harness for stdout/env stale-seed cases.

### FINDING_17: [OUT_OF_SCOPE] aggregate-findings.sh embeds raw reviewer findings without untrusted framing
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Aggregator still embeds raw reviewer findings without redaction/escaping; only scope-anchor appendix was hardened in this branch. Untrusted reviewer prose in `findings.md` flows verbatim into Codex aggregator prompts on plan-review merge rounds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Apply the same untrusted-block renderer to findings input when touching aggregate-findings (future work).

### FINDING_18: [OUT_OF_SCOPE] launch-claude-subprocess.sh --read-tools path lacks untrusted hardening
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-untrusted-escaping-output.txt
- **Severity**: latent
- **Concern**: The `--read-tools` path still embeds prompt bytes verbatim without literal-redacted context wrapping. Scout/read-tools launches can inline unredacted context reachable via `--add-dir` without the new `context_file_N` hardening. Pre-existing; unchanged by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Migrate read-tools prompt assembly to the same redact/escape/framing path as default context-files mode.
  - From cursor-specialist-edge-cases-output.txt: Future hardening if READ_TOOLS + context-files becomes a supported combination.

### FINDING_19: [OUT_OF_SCOPE] revise-plan-with-waterfall.sh duplicates lib-untrusted-block.sh (security slot)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Local `emit_untrusted_file_block` duplicates `scripts/lib-untrusted-block.sh`. Future security fixes to the shared helper may not reach `revise-plan-with-waterfall` `compose_prompt`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Source lib-untrusted-block.sh from revise-plan-with-waterfall.sh instead of duplicating helpers.

### FINDING_20: Post-redaction empty scope anchor is not rejected at materialization
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Materialization validates pre-redaction content only; post-redaction empty anchor is not rejected. An issue body of only redactable tokens yields empty `plan-review-scope-anchor.txt`; MAV path may downgrade to `panel-failed` while assessor silently falls back to legacy feature file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: After redact-secrets, require -s on SCOPE_ANCHOR_FILE or fail materialization with a loud error.

### FINDING_21: 64KiB scope-anchor cap exits with code 2 and no LOOP_STATUS
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: New 64KiB anchor cap exits with code 2 and no `LOOP_STATUS`; undocumented in `plan-review-loop.md`. Large issue + outline design sessions abort Step 3 as argv/config failure instead of a normalized terminal operators can branch on.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document cap; add harness; consider panel-failed or WARN+truncate instead of bare exit 2.

### FINDING_22: recover_main_agent_scope_anchor downgrades MAV to panel-failed on anchor recovery failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `recover_main_agent_scope_anchor` downgrades MAV to `panel-failed` when staged anchor recovery fails. Transient invalid anchor (empty post-redaction, permissions) loses entire main-agent vote path and skips Gate B/Step 3.6.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Use a narrower error terminal with WARN; reserve panel-failed for infra failures.

### FINDING_23: SECURITY.md overstates #3404 as unresolved vs python/README.md and tests
- **Reviewer(s)**: dyn-doc-code-parity-output.txt
- **Severity**: latent
- **Concern**: The "Python-default Step 8+ driver posture" paragraph in `SECURITY.md:96` lists issue #3404 among "unresolved" default-path gaps, but the same branch's `python/README.md:68-80` and `python/test_ship.py:1301+` document and test `PrePushConflictHandoff` / `ship-pr-rrr-phase14` resume via `ship-pr-rrr-after-phase14.flag`. The blanket wording is internally inconsistent and overstates #3404 exposure relative to code landed in `python/ship.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-doc-code-parity-output.txt: Split the paragraph into per-issue status (closed vs open vs intentional divergence, mirroring `python/README.md`'s #3405 note) so `SECURITY.md` accurately reflects which default-path risks are still live.

### FINDING_24: SECURITY.md overstates aggregator prompt hardening coverage
- **Reviewer(s)**: dyn-doc-code-parity-output.txt
- **Severity**: latent
- **Concern**: The inline-renderer bullet in `SECURITY.md:184-189` names "aggregator merge prompts" as scope-anchor consumers with staged `plan-review-scope-anchor.txt` provenance; `aggregate-findings.sh` appends a hardened scope-anchor block when `--scope-anchor-file` validates, but still embeds raw reviewer findings via `cat "$AGGREGATE_SOURCE_FILE"` with no untrusted framing or `encoding="literal-redacted"` wrapper. `SECURITY.md` does not qualify that only the anchor block is hardened.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-doc-code-parity-output.txt: Either narrow the `SECURITY.md` claim to "aggregator scope-anchor block only; findings input remains a separate untrusted surface" or extend `aggregate-findings.sh` to render findings through the same `larch_emit_untrusted_file_block` contract.

### FINDING_25: [OUT_OF_SCOPE] render-main-agent-scope-anchor.sh duplicates lib-untrusted-block.sh
- **Reviewer(s)**: dyn-doc-code-parity-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/render-main-agent-scope-anchor.sh:46-50` duplicates the redact/escape logic in `scripts/lib-untrusted-block.sh` instead of sourcing the shared helper; functionally aligned with `SECURITY.md` but increases drift risk (landed in #3548, not new to this delta).
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_26: Raw-tally stdout relay can persist stale ok status on tally-error symlink path
- **Reviewer(s)**: dyn-anchor-state-isolation-output.txt
- **Severity**: important
- **Concern**: The new raw-tally relay prints pre-correction `_tally_raw` lines (only `SCOPE_ANCHOR_FILE=` is stripped) onto loop stdout before `_terminal_exit` emits normalized KVs. On the supported symlink-inner fallback path (`INNER_RESULT_ENV` is a symlink, so `run-step3-review.sh` ignores the gated `.step3-plan-review-result.env` and parses stdout with first-wins semantics), a tally subprocess that emits `TALLY_PLAN_REVIEW_STATUS=ok` and then exits non-zero can leave `TALLY_PLAN_REVIEW_STATUS=ok` in captured stdout even though the loop later forces `tally-error` and omits `SCOPE_ANCHOR_FILE` from result env. `larch_scope_anchor_relay_allowed` then sees `ok` + `complete`, `recover_main_agent_scope_anchor` may repopulate from the staged anchor, and `SCOPE_ANCHOR_FILE` is emitted/persisted on what is effectively a tally-error path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-anchor-state-isolation-output.txt: Do not relay uncorrected `_tally_raw` terminal KVs to outer stdout (relay WARN only, or re-emit corrected `TALLY_PLAN_REVIEW_STATUS`/`VOTING_TALLY_FILE` from script state instead of `printf … _tally_raw`), and/or change `run-step3-review.sh` stdout fallback to last-wins for terminal keys and/or refuse `SCOPE_ANCHOR_FILE` relay whenever `TALLY_PLAN_REVIEW_STATUS` resolves to `tally-error` or `LOOP_STATUS` is `panel-failed`.

### FINDING_27: [OUT_OF_SCOPE] MainAgent re-tally scope-anchor isolation is prose-only
- **Reviewer(s)**: dyn-anchor-state-isolation-output.txt
- **Severity**: latent
- **Concern**: MainAgent re-tally `_RETALLY_SCOPE_ANCHOR_IN` / `_RETALLY_PARSED_SCOPE_ANCHOR_FILE` isolation is prose-only in the orchestrator; there is no script-level enforcement comparable to `plan-review-loop.sh` / `run-step3-review.sh`. Stale-anchor prevention on re-tally depends entirely on the main agent following SKILL instructions.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_28: [OUT_OF_SCOPE] Mid-loop round-summary.env can carry SCOPE_ANCHOR_FILE with empty LOOP_STATUS
- **Reviewer(s)**: dyn-anchor-state-isolation-output.txt
- **Severity**: latent
- **Concern**: Mid-loop `_write_round_summary` calls `_scope_anchor_handoff_value` while global `LOOP_STATUS` is still `complete` from `_run_plan_review_round`, so intermediate `round-summary.env` files can carry `SCOPE_ANCHOR_FILE` with an empty `LOOP_STATUS=` field; terminal gating in `.step3-plan-review-result.env` remains correct, but per-round summaries are inconsistent for downstream readers.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_29: launch-claude-subprocess.sh has dead local xml_escape_attr alongside live larch_xml_escape_attr call
- **Reviewer(s)**: dyn-untrusted-escaping-output.txt
- **Severity**: important
- **Concern**: The committed launcher defines a local `xml_escape_attr()` helper but the context-wrap path calls `larch_xml_escape_attr` from the missing `lib-untrusted-block.sh`; the local helper is dead code and the live call depends entirely on the uncommitted library. Even after the library lands, leaving both names invites a regression where a future edit wires `ctx_attr` to the wrong helper and skips `"` escaping in `path="…"`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-untrusted-escaping-output.txt: Drop the unused local `xml_escape_attr` (the working-tree diff already does this) and keep a single `larch_xml_escape_attr` implementation in the committed `lib-untrusted-block.sh`; extend `scripts/test-launch-claude-subprocess.sh` to fail if the launcher reintroduces a duplicate helper.

### FINDING_30: [OUT_OF_SCOPE] dispatch-plan-review-panel and render-specialist-prompt duplicate inline redact/escape helpers
- **Reviewer(s)**: dyn-untrusted-escaping-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/dispatch-plan-review-panel.sh:73-80` and `scripts/render-specialist-prompt.sh:226-237` duplicate inline redact/escape helpers instead of `lib-untrusted-block.sh`; logic currently matches the shared library, but drift could reintroduce inconsistent escaping outside the files this branch centralized.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_31: [OUT_OF_SCOPE] launch-claude-subprocess.sh sources unused lib-scope-anchor-handoff.sh
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Uncommitted working-tree change sources `lib-scope-anchor-handoff.sh` without calling any symbol from it. If committed, `launch-claude-subprocess` gains a fatal dependency on an unrelated lib and on the still-untracked handoff file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Drop the unused source line from launch-claude-subprocess.sh; keep only lib-untrusted-block.sh there.

### FINDING_32: test-check-scope-reduction-marker registered under test-harnesses-7 not test-harnesses-18
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `test-check-scope-reduction-marker` is registered under `test-harnesses-7`, not `test-harnesses-18` as the plan suggested. No functional failure; only shard placement differs from the plan example.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Optionally move the target to test-harnesses-18 for plan alignment, or leave as-is if shard-7 placement is intentional.

### FINDING_33: [OUT_OF_SCOPE] test-render-assessor-prompt exercises weaker validation path than production
- **Reviewer(s)**: dyn-untrusted-escaping-output.txt
- **Severity**: latent
- **Concern**: The harness invokes `render-assessor-prompt.sh` without `--design-tmpdir`, exercising the weaker `larch_scope_anchor_common_shape_ok` fallback instead of the production `larch_scope_anchor_validate_design` containment path; production dispatch always passes `--design-tmpdir` (`dispatch-plan-assessors.sh:69`).
- **Suggested revisions (informational for voters; coder decides)**:
