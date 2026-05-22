```text
### FINDING_1: Stale public `--panel` docs for `review-and-fix`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Concern**: Orchestrator-facing markdown still documents a public `--panel simple|hard` argv surface after the shell entrypoint stopped parsing/forwarding `--panel`, so readers, grepped “contracts,” and operators can follow docs into `unknown option` / wrong automation assumptions.
- **Suggested revision**: Remove `--panel` from the `review-and-fix.sh` orchestrator flag table; document the internal `review-core.sh --panel hard` chain only; keep “Edit-In-Sync” prose aligned with the actual `review-and-fix.sh` argv.

### FINDING_2: Step 5 harness markdown contract drift (`test-run-step5-review`)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: `scripts/test-run-step5-review.md` still claims `run-step5-review` derives/forwards `--panel hard` while the harness/launcher no longer passes `--panel`, risking stale assertions and future CI/doc-sync confusion.
- **Suggested revision**: Update the harness markdown “coverage” lines to match real argv (e.g., round-cap, dynamic-archetypes, session paths) and explicitly state `--panel` is not forwarded.

### FINDING_3: Oversized PR diff mixes unrelated work with the cutover
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Unrelated fixes plus large `larch-logs`/review artifact trees bundled with the primary contract/cutover change impairs attribution, bisectability, and selective revert risk management.
- **Suggested revision**: Split unrelated commits/log flushes into separate PRs or land them separately; keep the cutover PR minimal.

### FINDING_4: Unknown-flag exit code inconsistency (`clarify-label.sh`)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Unknown-option path exits `1` after usage, unlike peer scripts that commonly exit `2`, which can mis-route thin automation that maps exit `2` to “bad argv.”
- **Suggested revision**: Align unknown-option exit code with the repo’s dominant convention (and any harness expectations), or document the intentional divergence.

### FINDING_5: Deprecated argv loop token consumption (`post-design-boundary.sh`)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Stub/legacy argv parsing uses single-token shifts for unknown flags, leaving hypothetical dangling tokens / undefined tail behavior (likely low practical risk if callers are gone).
- **Suggested revision**: Tighten argv consumption to a well-defined end state, or explicitly document “undefined tail” behavior for unknown args.

### FINDING_6: [OUT_OF_SCOPE] Normative docs still describe removed flags / old Step 5 argv
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Representative `docs/*` surfaces still describe removed `/implement` flags and public `review-and-fix --panel` wiring; post-merge operators may infer obsolete CLI contracts (not asserted as changed in the reviewed diff hunks).
- **Suggested revision**: Schedule a docs-only follow-up aligned with `skills/implement/SKILL.md` and the issue-anchored plan docs.

### FINDING_7: [OUT_OF_SCOPE] Doc-sync fixtures canonize obsolete `--panel hard` phrasing
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: `scripts/test-quick-mode-docs-sync.sh` fixtures still encode `review-and-fix.sh --panel hard` as a positive canonical phrase, which can ossify obsolete wording in self-tests.
- **Suggested revision**: Refresh fixtures the next time that harness is touched to match internal `review-core` wiring and updated operator language.

### FINDING_8: `agnix-fix` SKILL missing normative `/implement` exit-code routing (esp. `3`, incl. ambiguous caveat)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: `.claude/skills/agnix-fix/SKILL.md` lacks an explicit outcomes/exit-code subsection mirroring `skills/implement/SKILL.md` (`0` vs `2` vs `3`), increasing risk that wrappers treat non-zero exits generically, retry incorrectly, or fail to route operators back to `/design` after preflight refuse / ambiguous clarify-related failures.
- **Suggested revision**: Add an exit/outcomes subsection: document `3` as a terminal branch for that attempt until upstream `/design` resolves clarify/plan issues; include the `2` vs `3` split and the ambiguous-state caveat as applicable.

### FINDING_9: Stale header comment referencing removed `/implement --issue` (`find-lock-issue.sh`)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Maintainer-facing header still points at a removed `--issue` flag shape, encouraging rediscovery/reintroduction of obsolete argv.
- **Suggested revision**: Reword to the supported positional `/implement <issue-N>` contract (and any related lock-script notes).

### FINDING_10: External/issue prose vs normative SKILL on audit-refusal exit semantics
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Older feature/issue text may still imply exit `0` on audit refusal while `skills/implement/SKILL.md` defines exit `3`, causing external automation keyed to the wrong contract.
- **Suggested revision**: Update external-facing artifacts to match the normative SKILL; explicitly treat superseded issue prose as non-authoritative for exit semantics.

### FINDING_11: `/design` “simple tier” sketch-count operator expectation drift
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: `skills/design/SKILL.md` wording may imply a different sketch budget than `sketch_budget=2`, creating cost/expectation mismatch without a direct runtime failure.
- **Suggested revision**: Align operator-facing prose with the actual simple-tier sketch budget.

### FINDING_12: Plugin marketing copy may misstate what controls post-plan depth (`plugin.json`)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Description implies `POST_PLAN_WORKFLOW_PATH` provenance tied to “classification,” while implement defaults/issue-anchored behavior may differ; readers may misunderstand the knob.
- **Suggested revision**: Align `plugin.json` copy with implement Step 1 defaults, or clarify tier/classification vs session key responsibilities.

### FINDING_13: [OUT_OF_SCOPE] Historical `larch-logs/implement/*` commands show obsolete argv
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Captured logs can contain old `--panel` / `--issue` strings; noise if mistaken for the live runtime contract.
- **Suggested revision**: None required by policy unless the repo wants log hygiene; treat as historical artifact.

### FINDING_14: [OUT_OF_SCOPE] `aggregate-findings.sh` slot-label normalization edge case
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Latent validator gap around nested-parenthesis slot suffixes could cause rare false validation failures on exotic labels; separate from the primary cutover thread.
- **Suggested revision**: Track/harden under aggregate-findings maintenance if observed.

### FINDING_15: [OUT_OF_SCOPE] `agnix-fix` removed per-run delimiter-wrapped `FEATURE_FILE` handoff
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Behavioral change increases reliance on `/implement` Preflight trust-boundary correctness; may be intentional but warrants explicit verification if further hardening `agnix-fix`.
- **Suggested revision**: If hardening: verify preflight envelope assumptions explicitly in skill docs and/or add guardrails consistent with the chosen trust model.

### FINDING_16: Prompt-injection / hijack risk: untrusted issue body materialized into `FEATURE_FILE` without a robust delimiter envelope
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Raw GitHub issue title/body written to `FEATURE_FILE` without a strong per-run delimiter/nonce envelope (and related collision handling) enables delimiter escape and downstream “requirements” spoofing against tooling/orchestrators that treat the file as trusted input.
- **Suggested revision**: Restore a nonce-delimited envelope + collision refusal for materialization, or enforce an equivalent trusted wrap at every model-facing read; document fork-operator expectations.

### FINDING_17: Delimiter-collision weakness in fixed XML-like `reviewer_*` preflight audit framing
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Known-fixed tag-like delimiters for Preflight audit context can be collided with by issue-body content, weakening the perceived “untrusted envelope” boundary for models/parsers.
- **Suggested revision**: Use per-run delimiter nonces for audit context, or refuse/sanitize collisions; cross-link `SECURITY.md` so the framing is not mistaken for a hard parser boundary.

### FINDING_18: [OUT_OF_SCOPE] `SECURITY.md` empty-merge attestation limitation (already acknowledged)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Documented non-proof vs hostile model; not introduced as a regression by the reviewed diff.
- **Suggested revision**: No change required for this review scope.

### FINDING_19: [OUT_OF_SCOPE] `SECURITY.md` notes gh plan/clarify helpers omit injection scanning (documented non-goal)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Explicitly documented limitation/non-goal extended by the same contract assumptions.
- **Suggested revision**: No change required for this review scope.

### FINDING_20: `PLAN_FILE` miss can fall back to local `design-export/plan.txt` in Step 1 / Step 5 runners
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: On `PLAN_FILE` absence, scripts may consume a stale local export instead of the GitHub-validated `larch:plan` materialization expected after Preflight, masking session-env writer bugs/partial writes.
- **Suggested revision**: Remove or strictly gate the `design-export` fallback on issue-anchored runs; fail closed with an error pointing maintainers at `persist-post-plan-keys.sh` (or equivalent writer contract).

### FINDING_21: Exit code `3` overloads multiple terminal meanings (audit refuse vs ambiguous clarify state)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Wrappers branching only on exit `3` cannot distinguish “needs `/design`/clarify” from “marker graph inconsistent / needs manual repair,” increasing mis-routing and bad retries.
- **Suggested revision**: Introduce a distinct exit code or a machine-parseable stderr sentinel for the ambiguous case; document the automation contract alongside SKILL tables.

### FINDING_22: `/fix-issue` discovery text omits plan-mandated flags (`--merge` / `--no-dedup`)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: YAML `argument-hint` / description surfaces omit flags that the plan and forwarding paths expect, causing operators to miss supported argv.
- **Suggested revision**: Update `skills/fix-issue/SKILL.md` argument-hint (and related description line if needed) to match plan C.1 and actual forwards.

### FINDING_23: Topology authority still uses “hard and simple panels” phrasing (`topology.tsv`)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Projection row description preserves SIMPLE/HARD split language despite a unified internal panel story, undermining the “single internal panel + `POST_PLAN_WORKFLOW_PATH` semantics” messaging sweep.
- **Suggested revision**: Reword the row to unified hard panel semantics (and post-plan workflow depth), keeping `topology.tsv` consistent with counted projection authority.
```
