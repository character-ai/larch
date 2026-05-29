### FINDING_1: code-quality: skills/design/SKILL.md:542-560
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Step 2a.3 contains two identical Quick mode collect-agent-results fences after fence collapse. An orchestrator may treat both blocks as mandatory and run sketch collection twice or waste tokens reconciling duplicate instructions. Remove one duplicate Quick mode block; keep a single foreground collector example.
- **Suggested revision**: Address the concern above.


### FINDING_10: correctness: skills/design/references/plan-review.md:142
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Fence collapse left mktemp path using undefined _launch_id after removing the variable assignment. Operator runs the reference fence: abort under set -u or dispatch-plan-voters..stdout paths that collide across runs. Restore _launch_id= dispatch-plan-voters.$$ before mktemp or embed $$ in the template.
- **Suggested revision**: Address the concern above.


### FINDING_12: correctness: docs/run-logs.md:85-117
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Planned Stage 4 doc trim for live-stream/monitor references was not applied; file still describes live ndjson streams. Operator follows run-logs.md and expects live streams or monitor sidecars that Stage 4 no longer creates. Rewrite breadcrumbs section for quiet-log forensics only; align with SECURITY.md ignore rules.
- **Suggested revision**: Address the concern above.


### FINDING_13: correctness: skills/shared/voting-protocol.md:149,170
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Still claims plan review gets run_in_background from dispatch-plan-voters after foreground collapse. Orchestrator backgrounds dispatch-plan-voters per voting-protocol contradicting plan-review and NEVER #16. Say plan-review dispatch is foreground; limit run_in_background to direct external launch paths.
- **Suggested revision**: Address the concern above.


### FINDING_19: risk-integration: docs/linting.md:29
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Usage section still documents removed foreground-markers lint under make lint Contributors search for a dead lint target after Stage 3 removal Update the Usage bullet to list actual make lint shell static checks
- **Suggested revision**: Address the concern above.


### FINDING_2: code-quality: skills/implement/SKILL.md:1156
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Step 8+ still tells the orchestrator to run the phantom probe before a ship-pr background+monitor invocation despite collapsed foreground ship-pr fences. Models may search for a monitor pair or mis-order Step 8 pre-bump vs ship-pr relative to the deleted contract. Reword to foreground ship-pr invocation only; align with NEVER #16 and the Invoke block below.
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


### FINDING_26: correctness: scripts/test-design-structure.sh:401-406
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Inverted absence tests embed final-grep-forbidden literals (breadcrumb-monitor, Background pair required, BASH_AUTHORING.md §4) Pre-close repo grep for plan acceptance tokens hits the structure harness even when skill prose is clean; contradicts zero-hit grep gate and no test-only exclusions Rewrite assertions without forbidden substrings in tracked source, or document a single allowed exclusion in the close checklist if the project accepts that tradeoff
- **Suggested revision**: Address the concern above.


### FINDING_27: correctness: docs/linting.md:29
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Usage still claims make lint runs foreground markers after lint-foreground-markers removal Contributors expect a removed linter when reading local make lint docs Replace foreground markers with checks that actually run, or remove the phrase
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


### FINDING_7: code-quality: scripts/test-implement-structure.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] No inverted assertion prevents background+monitor or breadcrumb-monitor prose returning to implement SKILL.md. Stale orchestration text like implement/SKILL.md:1156 can land without structure-test failure. Add implement-structure inverted greps mirroring test-design-structure.sh Stage 4 checks.
- **Suggested revision**: Address the concern above.


