### OOS_1: [OUT_OF_SCOPE] `norm()` generic bracket stripping predates consolidation / changes detector semantics
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-shell-hygiene-output.txt
- **Severity**: latent
- **Concern**: `norm()` while-loop bracket stripping predates consolidation; multi-bracket headings may match differently than the original single-severity strip. Consolidation also broadened `norm()` from stripping only `[important|nit|latent]` to stripping any `[A-Za-z0-9_-]+` prefix before `[SCOPE-REDUCTION]` detection—detector semantics changed beyond deduplication-only consolidation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Track separately if parity harness needs expansion


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_10: [OUT_OF_SCOPE] Voter ballot filesystem path lacks attribute escaping
- **Reviewer(s)**: dyn-prompt-boundary-output.txt
- **Severity**: latent
- **Concern**: Ballot filesystem path is still interpolated into the voter prompt without attribute escaping; unchanged by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-boundary-output.txt: The ballot filesystem path is still interpolated into the voter prompt without attribute escaping; unchanged by this branch.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_11: [OUT_OF_SCOPE] Empty `SCOPE_MARKER_HELPER` fails open in dedup `is_tagged()`
- **Reviewer(s)**: dyn-marker-flow-output.txt
- **Severity**: latent
- **Concern**: If `SCOPE_MARKER_HELPER` were ever empty/unset, `is_tagged()` returns `False` instead of failing closed. Production wiring always sets a path and non-0/1 helper exits abort dedup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-marker-flow-output.txt: If `SCOPE_MARKER_HELPER` were ever empty/unset, `is_tagged()` returns `False` instead of failing closed; production wiring always sets a path and non-0/1 helper exits abort dedup, so this is a latent foot-gun rather than a regression from this diff.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### OOS_12: [OUT_OF_SCOPE] Canonical helper does not scan `- **Description**:` for scope-reduction marker
- **Reviewer(s)**: dyn-marker-flow-output.txt
- **Severity**: latent
- **Concern**: Marker detection in `check-scope-reduction-marker.sh` only scans `### FINDING_*` headings and `Concern:`/`what:` lines; a `[SCOPE-REDUCTION]` marker placed only on `- **Description**:` would not be detected. Dedup `problem_text()` has a Description fallback, but the canonical helper does not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-marker-flow-output.txt: Marker detection only scans `### FINDING_*` headings, `Concern:`/`what:` lines; a `[SCOPE-REDUCTION]` marker placed only on `- **Description**:` would not be detected. Dedup `problem_text()` has a Description fallback, but the canonical helper does not; pre-existing contract gap, not introduced here.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_13: [OUT_OF_SCOPE] Assessor `mktemp` prompt file lacks `EXIT` trap
- **Reviewer(s)**: dyn-shell-hygiene-output.txt
- **Severity**: nit
- **Concern**: The `mktemp` prompt file in `render-assessor-prompt.sh` has no `EXIT` trap; a mid-write failure under `set -e` can leave `.assessor-prompt.*` debris. Pre-existing pattern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-hygiene-output.txt: The `mktemp` prompt file still has no `EXIT` trap; a mid-write failure under `set -e` can leave `.assessor-prompt.*` debris. Pre-existing pattern, not introduced by the scope-anchor delta.

Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### OOS_2: [OUT_OF_SCOPE] Pre-existing duplicated `redact_untrusted_stream` across renderers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Ongoing maintenance burden when escape contract changes; multiple render scripts carry duplicate redact/escape logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Centralize untrusted block helpers in a shared library script


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### OOS_3: [OUT_OF_SCOPE] Branch bundles unrelated Python ship-driver default (#3462) and run artifacts
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, dyn-ship-driver-output.txt
- **Severity**: latent
- **Concern**: Branch includes large unrelated #3462 Python ship-pr default migration, `python/test_ship.py`, and `larch-logs/` run artifacts beyond #3547 scope-anchor surface. Broader CI failures or regressions can block or obscure scope-anchor fixes; `SECURITY.md` documents open review gaps on the default path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Split or document unrelated scope in PR
  - From cursor-specialist-testing-output.txt: Split unrelated ship work into a separate PR or ensure isolated test ownership.
  - From cursor-specialist-security-output.txt: Address via tracked issues #3446/#3404/#3405/#3449; operators can set LARCH_SHIP_PR_IMPL=bash to opt out.
  - From dyn-ship-driver-output.txt: The branch bundles the scope-anchor follow-up (`ed2320447`) with the Python ship-driver default flip (`4de108c0a` / #3462) plus a large `larch-logs/` run artifact (`c0999699d`). That widens review and rollback blast radius beyond issue #3547’s stated dependency surface.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_4: [OUT_OF_SCOPE] `round-summary.env` writes `SCOPE_ANCHOR_FILE` without terminal gate
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-scope-handoff-output.txt, dyn-ship-driver-output.txt
- **Severity**: latent
- **Concern**: `_write_round_summary()` always records `SCOPE_ANCHOR_FILE` from the materialized anchor variable while durable handoff is terminal-gated in `_scope_anchor_handoff_value()` / `write_step3_result_env()` / `emit_loop_kvs()`. Forensic round artifacts can contradict the normalized handoff contract on `panel-failed` and `tally-error` exits if any consumer treats `round-summary.env` as authoritative.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Optional: gate round-summary SCOPE_ANCHOR_FILE the same way as emit_loop_kvs for consistency.
  - From dyn-scope-handoff-output.txt: `_write_round_summary()` always writes `SCOPE_ANCHOR_FILE=${SCOPE_ANCHOR_FILE:-}` from the materialized anchor variable, without the terminal gate used by `write_step3_result_env()`. This predates the branch diff and is documented in `plan-review-loop.md`, but it remains a secondary path-only surface if any consumer ever treats `round-summary.env` as authoritative for Step 3 handoff rather than forensics.
  - From dyn-ship-driver-output.txt: Route `round-summary.env` through `_scope_anchor_handoff_value()` (or omit the key when tally terminal is not `ok` / `main-agent-vote-required`), and document the gate in `plan-review-loop.md` so passive-summary readers do not treat error-round summaries as authoritative handoff state.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_5: [OUT_OF_SCOPE] 64KiB scope-anchor size cap has no harness on all consumers
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-ship-driver-output.txt
- **Severity**: latent
- **Concern**: 64KiB scope-anchor size cap added in several paths has no harness case on loop materialization or `render-main-agent-scope-anchor.sh`. Oversize anchors might fail opaquely in production without a pinned regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add harness expecting materialization/loop failure when anchor exceeds cap.
  - From dyn-ship-driver-output.txt: `skills/design/scripts/render-main-agent-scope-anchor.sh:46-50` still lacks the 64 KiB cap added elsewhere (`render-voter-prompt.sh:40-45`, `plan-review-loop.sh:178-184`, `render-plan-review-prompt.sh:122-125`); pre-existing asymmetry, not introduced by the loop handoff work.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_6: [OUT_OF_SCOPE] Assessor plan snapshot blocks remain raw fenced markdown
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-prompt-boundary-output.txt, dyn-ship-driver-output.txt
- **Severity**: latent
- **Concern**: Assessor hardens `FEATURE_FILE` only; `PLAN_ORIGINAL`, `PLAN_PREV`, and `PLAN_CURRENT` remain raw `cat` inside markdown fences. Plan content with delimiter-like text or closing fence lines could break fence structure or inject instructions into external assessor models. `SECURITY.md` claims assessor staged-anchor coverage without symmetric plan-body treatment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Wrap plan sections in the same literal-redacted escaped untrusted block contract or document the gap explicitly in SECURITY.md until migrated.
  - From cursor-specialist-edge-cases-output.txt: Pre-existing; address in a dedicated assessor plan-hardening follow-up if desired.
  - From dyn-prompt-boundary-output.txt: The branch hardens the assessor feature block, but `PLAN_ORIGINAL`, `PLAN_PREV`, and `PLAN_CURRENT` are still raw `cat` inside markdown fences with no `<>&` escaping or breakout hardening; that predates this diff and was not regressed here.
  - From dyn-ship-driver-output.txt: `skills/shared/scripts/render-assessor-prompt.sh:66-78` still inlines plan snapshots as raw markdown fences while only the feature file uses the literal-redacted block; the plan explicitly deferred plan-fence hardening, but `SECURITY.md` now claims assessor staged-anchor coverage without the same symmetric treatment for plan bodies.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_7: [OUT_OF_SCOPE] Aggregator still raw-inlines reviewer findings bodies
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-testing-output.txt, dyn-prompt-boundary-output.txt
- **Severity**: latent
- **Concern**: Pre-existing raw `cat` of reviewer findings into aggregator prompt without delimiter escaping; same prompt-injection class as scope-anchor hardening gap, not introduced by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Track separately; apply the same untrusted-block renderer to findings input when hardening the aggregator surface.
  - From cursor-specialist-testing-output.txt: Scope-anchor inline append uses redact-only, not literal-redacted escaping. Delimiter-like anchor text could perturb aggregator prompt structure. Migrate append through emit_untrusted_file_block or equivalent escaping helper.
  - From dyn-prompt-boundary-output.txt: Raw reviewer findings are still inlined with plain `cat` before the new scope-anchor block; that behavior predates this branch and remains a separate prompt-boundary gap.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_8: [OUT_OF_SCOPE] `read-tools` context path not inline-hardened
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `read-tools` path in `launch-claude-subprocess.sh` does not inline-harden context bodies. Context reachable via `--add-dir` remains less bounded than embedded `--context-files` hardening; pre-existing and out of scope for this branch's context-files work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Pre-existing; out of scope for this branch’s --context-files hardening.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### OOS_9: [OUT_OF_SCOPE] `test-check-scope-reduction-marker` registered in two Makefile harness shards
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-marker-flow-output.txt
- **Severity**: nit
- **Concern**: `test-check-scope-reduction-marker` runs in both harness shards 7 and 18, duplicating CI wall time without added coverage signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Keep a single shard registration.
  - From cursor-specialist-edge-cases-output.txt: Deduplicate to one shard when convenient.
  - From dyn-marker-flow-output.txt: `test-check-scope-reduction-marker` is registered in both `test-harnesses-7` and `test-harnesses-18`, so CI runs the same harness twice; harmless but redundant.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

