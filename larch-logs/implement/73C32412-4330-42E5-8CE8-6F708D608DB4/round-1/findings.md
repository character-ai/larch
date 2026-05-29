### FINDING_1: code-quality: skills/design/SKILL.md:542-560
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Step 2a.3 contains two identical Quick mode collect-agent-results fences after fence collapse. An orchestrator may treat both blocks as mandatory and run sketch collection twice or waste tokens reconciling duplicate instructions. Remove one duplicate Quick mode block; keep a single foreground collector example.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/implement/SKILL.md:1156
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Step 8+ still tells the orchestrator to run the phantom probe before a ship-pr background+monitor invocation despite collapsed foreground ship-pr fences. Models may search for a monitor pair or mis-order Step 8 pre-bump vs ship-pr relative to the deleted contract. Reword to foreground ship-pr invocation only; align with NEVER #16 and the Invoke block below.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: docs/run-logs.md:85-117
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Plan-required run-logs trim of live-stream/monitor language was not applied; file still describes live breadcrumb streams and hidden monitor sidecars. Operators and reviewers read outdated publication semantics inconsistent with Stage 4 SECURITY.md and the removed monitor. Update run-logs.md to match post-rip-out quiet-log forensics publication; drop or legacy-label live-stream/monitor prose.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: docs/linting.md:29
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Usage section still claims make lint runs foreground markers though lint-foreground-markers was removed in Stage 3. Contributors expect a linter that no longer exists. Remove foreground markers from the make lint Usage bullet.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: AGENTS.md:40
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Canonical lib-quiet bullet still lists emit_breadcrumb though lib-quiet.md no longer documents that API. Entrypoint readers look for a removed helper. Trim the bullet to emit/emit_kv (and LARCH_QUIET_DISABLE).
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: skills/design/SKILL.md:562
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Redundant timeout guidance duplicates foreground vs timeout: 1260000 instructions after fence collapse. Minor confusion when copying Step 2a.3 collector calls. Consolidate to one foreground invocation sentence with optional timeout.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: scripts/test-implement-structure.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] No inverted assertion prevents background+monitor or breadcrumb-monitor prose returning to implement SKILL.md. Stale orchestration text like implement/SKILL.md:1156 can land without structure-test failure. Add implement-structure inverted greps mirroring test-design-structure.sh Stage 4 checks.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] code-quality: scripts/implement-bootstrap.md:163
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Still references deleted lint-foreground-markers DENYLIST. Pre-existing doc drift outside Stage 4 file list. Update bootstrap doc in a separate sweep.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] code-quality: .gitleaks.toml:25-26
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Allowlist still names deleted test-breadcrumb-monitor harness paths. No functional impact; config clutter only. Remove obsolete allowlist entries when editing gitleaks config.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: skills/design/references/plan-review.md:142
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Fence collapse left mktemp path using undefined _launch_id after removing the variable assignment. Operator runs the reference fence: abort under set -u or dispatch-plan-voters..stdout paths that collide across runs. Restore _launch_id= dispatch-plan-voters.$$ before mktemp or embed $$ in the template.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: skills/design/references/plan-review.md:141-149
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Collapsed dispatch-plan-voters fence no longer reads/evals stdout KVs the prose requires. Manual fence run leaves VOTER_* unset so tallying mis-routes voter paths and statuses. After foreground dispatch cat the stdout file and eval or parse VOTER_* KVs like the old success branch.
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: docs/run-logs.md:85-117
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Planned Stage 4 doc trim for live-stream/monitor references was not applied; file still describes live ndjson streams. Operator follows run-logs.md and expects live streams or monitor sidecars that Stage 4 no longer creates. Rewrite breadcrumbs section for quiet-log forensics only; align with SECURITY.md ignore rules.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: skills/shared/voting-protocol.md:149,170
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Still claims plan review gets run_in_background from dispatch-plan-voters after foreground collapse. Orchestrator backgrounds dispatch-plan-voters per voting-protocol contradicting plan-review and NEVER #16. Say plan-review dispatch is foreground; limit run_in_background to direct external launch paths.
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] correctness: docs/linting.md:29
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] make lint description still mentions foreground markers lint removed in Stage 3. Contributor expects make lint-foreground-markers to exist. Update linting.md to drop foreground-markers from the local make lint bullet list.
- **Suggested revision**: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] correctness: AGENTS.md:40
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Canonical lib-quiet bullet still references removed emit_breadcrumb API. Reader searches for emit_breadcrumb and finds no implementation. Trim AGENTS.md canonical line to emit/emit_kv only.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: scripts/test-design-structure.sh:400-406
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Only brainstorm.md has inverted Family-B absence greps; plan acceptance requires peers to assert fence absence across all collapsed skill markdown Re-adding a background+monitor block to skills/implement/SKILL.md or skills/design/SKILL.md would pass make lint until someone runs the manual grep gate Extend structure harnesses (at minimum test-implement-structure.sh) with the same && fail pattern for forbidden literals on each plan-listed skill path
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: (plan testing strategy)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Final grep gate is manual; not registered in Makefile or CI make lint green while a new harness line mentions LARCH_DONE_SENTINEL would violate acceptance without failing CI Add scripts/test-breadcrumb-ripout-grep-gate.sh and wire it into make lint
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: skills/implement/SKILL.md:1224-1247
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] FINDING_1 writer_rc routing is prose-only with no harness pins Partial revert to monitor_rc or LARCH_STATUS_FILE routing would mis-handle ship-pr stalls; tests would not catch it Add test-implement-structure.sh contains/absent greps for writer_rc routing and forbidden monitor_rc symbols
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: docs/linting.md:29
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Usage section still documents removed foreground-markers lint under make lint Contributors search for a dead lint target after Stage 3 removal Update the Usage bullet to list actual make lint shell static checks
- **Suggested revision**: Address the concern above.

### FINDING_20: code-quality: AGENTS.md:40
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Canonical lib-quiet bullet still lists emit_breadcrumb after API removal Misleading agent/doc cross-references when authoring quiet helpers Remove emit_breadcrumb from the AGENTS.md canonical-sources line
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: scripts/test-collect-agent-results.sh:211-212
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] C_DONE comment still says done sentinel after sentinel env strip was removed Future editors may reintroduce LARCH_DONE_SENTINEL setup believing the test requires it Rename the case comment to describe plain collector OK on .done files
- **Suggested revision**: Address the concern above.

### FINDING_22: security: skills/implement/SKILL.md:1533-1536
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Removed export of LARCH_CLAUDE_SOURCE_FILE before child token-report.sh calls while token-claude-source.sh only reads that path from the environment. Orchestrator fence sets LARCH_CLAUDE_SOURCE_FILE in the parent shell only; token-report invokes token-claude-source.sh without the snapshot env, so concurrent sessions can bind the newest-mtime transcript and write wrong token usage into committed larch-logs batches and public summaries. Restore export LARCH_CLAUDE_SOURCE_FILE=… (and LARCH_TIMING_LEDGER where timing-ledger needs it) immediately before each token-report/timing-report child call, or pass explicit CLI overrides; align test-implement-timing-rehydration.sh.
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: skills/implement/SKILL.md:1156
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Stale background+monitor wording remains above Step 8+ ship-pr.sh despite foreground-only fences. Operators following SKILL.md may use deprecated Family-B patterns, weakening completion discipline on long ship-pr runs. Reword to foreground ship-pr.sh invocation; remove background+monitor.
- **Suggested revision**: Address the concern above.

### FINDING_24: correctness: skills/implement/SKILL.md vs scripts/test-implement-timing-rehydration.sh:116-118
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Three-key export lines removed but harness still requires export count to match token rehydration read count. make lint / test-implement-timing-rehydration should fail on this branch unless the harness is updated elsewhere. Restore exports or update the harness and document the new rehydration contract in the same change.
- **Suggested revision**: Address the concern above.

### FINDING_25: correctness: skills/implement/SKILL.md:1224-1247
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Exit matrix branches on Bash tool rc while stall semantics live in ship-pr-state.sh; no explicit timeout/mismatch guard. Harness timeout or auto-background returns non-4 while state already has STALL_TRACKING/EXIT_CODE=4; orchestrator skips Exit 4 → Step 16 or mis-routes continuation. Add precedence: on timeout/mismatch, skip exit matrix and follow L1188 state-driven re-invoke; branch matrix on ship-pr-state EXIT_CODE when call completes normally.
- **Suggested revision**: Address the concern above.

### FINDING_26: correctness: scripts/test-design-structure.sh:401-406
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Inverted absence tests embed final-grep-forbidden literals (breadcrumb-monitor, Background pair required, BASH_AUTHORING.md §4) Pre-close repo grep for plan acceptance tokens hits the structure harness even when skill prose is clean; contradicts zero-hit grep gate and no test-only exclusions Rewrite assertions without forbidden substrings in tracked source, or document a single allowed exclusion in the close checklist if the project accepts that tradeoff
- **Suggested revision**: Address the concern above.

### FINDING_27: correctness: docs/linting.md:29
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Usage still claims make lint runs foreground markers after lint-foreground-markers removal Contributors expect a removed linter when reading local make lint docs Replace foreground markers with checks that actually run, or remove the phrase
- **Suggested revision**: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] correctness: scripts/implement-bootstrap.md
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Stale lint-foreground-markers reference possible Not in Stage 4 file list; unchanged in feature commit Trim in a follow-up public-doc sweep
- **Suggested revision**: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] code-quality: scripts/relevant-checks.sh:137
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Stale lint-foreground-markers pragma on case pattern Not in Stage 4 plan file list Remove or retarget comment when touching relevant-checks
- **Suggested revision**: Address the concern above.

