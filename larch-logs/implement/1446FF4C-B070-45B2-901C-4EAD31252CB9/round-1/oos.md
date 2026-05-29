### FINDING_11: [OUT_OF_SCOPE] `SCOUT_LATENCY_MS` reports last tier only
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `SCOUT_LATENCY_MS` is last-tier only. Waterfall latency is under-reported in timing KV output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Sum per-tier ELAPSED or emit per-tier timing keys.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_19: [OUT_OF_SCOPE] `SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_*` env overrides
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_*` env overrides can replace launchers. Malicious or stale env in operator shell could redirect scout launches to arbitrary scripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Document in SECURITY.md; restrict overrides to harness contexts


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_20: [OUT_OF_SCOPE] no max length on scout `prompt_body` in jq validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: No max length on scout `prompt_body` in jq validation. Oversized `prompt_body` could bloat dynamic reviewer prompts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Add prompt_body byte/line cap in scout validation


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_23: [OUT_OF_SCOPE] Codex scout tier embedding path predates this branch
- **Reviewer(s)**: dyn-staged-context-injection-output.txt
- **Severity**: nit
- **Concern**: Codex scout tier still builds prompts via `launch-review.sh` → `render-specialist-prompt.sh` with `--diff-file` pointing at staged paths; Codex remains `codex exec --sandbox read-only` with `--add-dir` limited to the output directory. That embedding path predates this branch; this change mainly widens the Claude tier.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_24: [OUT_OF_SCOPE] implement Step 5 `session-env.sh` layout vs scout `--add-dir`
- **Reviewer(s)**: dyn-staged-context-injection-output.txt
- **Severity**: nit
- **Concern**: For `/implement` Step 5, `session-env.sh` and other implement-wide artifacts live in `$IMPLEMENT_TMPDIR`, while scout `SESSION_ROOT` is `$IMPLEMENT_TMPDIR/round-N`, so tokens in `session-env.sh` are not under `--add-dir` unless copied into the round directory (layout-dependent, not introduced by this diff).
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_25: [OUT_OF_SCOPE] existing scout-output mitigations do not remove new lateral-read risks
- **Reviewer(s)**: dyn-staged-context-injection-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md` and `dispatch-panel.sh` already document scout output as untrusted metadata and synthesize dynamic reviewer prompts from a fixed template; those mitigations remain appropriate but do not remove the new lateral-read and tool-mode risks above.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_26: [OUT_OF_SCOPE] unrelated run-log commit in branch
- **Reviewer(s)**: dyn-staged-context-injection-output.txt
- **Severity**: nit
- **Concern**: Commit `68da004ab` is a run-log flush and is unrelated to the scout security surface. Branch commits reviewed: `d3e01eaa2` (feature), `68da004ab` (larch-logs flush).
- **Suggested revisions (informational for voters; coder decides)**:

---

**Merge notes (for voters, not machine output):**

| Merged IDs | Rationale |
|------------|-----------|
| 1, 13, 27 | Same plan harness gap for presence flags |
| 3, 11 | Same unused Codex argv flags; OOS tag retained per rule |
| 8, 16, 24 | Same `had_probe_miss` → `empty` terminal semantics |
| 9, 20, 30 | Same permission-mode / harness weakness |
| 17, 29 | Same broad `--add-dir` on `SESSION_ROOT` |
| 21, 31 | Same removed bulk size cap |
| 14, 28 | Same plan fidelity test for no Cursor scout tier |

**Kept separate:** FINDING_7 (product: missing Cursor tier vs acceptance) vs FINDING_18 (tests: assert no Cursor tier per Codex→Claude contract) — different fixes and tension with FINDING_7. FINDING_13 vs FINDING_14/18 — narrow `--add-dir` vs design `DESIGN_TMPDIR` layout. FINDING_22 vs FINDING_3 — missing description forwarding vs unused diff flags.

FINDING_23–26 have no suggested-revision bullets where reviewers supplied none beyond “Address the concern above” omitted in source for OOS informational items.

Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_3: [OUT_OF_SCOPE] Codex tier passes unused launch-review context flags
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `run_codex_tier` passes `--diff-file`/`--scope-files` to `launch-review.sh` while using `--prompt-file` without `--agent-file`, so `launch-review` ignores those paths for prompt assembly. Maintainers may assume Codex gets diff via render-specialist embedding rather than Read instructions and `--add-dir` on `SESSION_ROOT`. The same unused flags appear in Codex argv when only `--prompt-file` is used.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Omit unused launch-review context flags or add a comment that context is prompt-driven for scout Codex tier.
  - From cursor-specialist-correctness-output.txt: Remove unused flags from codex_args or document that only the scout prompt paths matter.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

