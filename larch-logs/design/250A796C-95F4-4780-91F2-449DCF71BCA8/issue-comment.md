## `/design --simple 3031` re-verification

Step 0c symbol scan + targeted re-reads against current `main` (commit `c17ee7f2`). Findings:

### Already addressed in the current tree — drop from scope

- **Item A** (`AGENTS.md:56` post-monitor wait): Contract is present at `AGENTS.md:58` — "Top-level Family B background+monitor pairs must capture the writer PID and `wait` after `breadcrumb-monitor.sh`; use the canonical two-branch pattern in `BASH_AUTHORING.md` §4."
- **Item D** (`README.md:59-61`, `docs/skills.md:50-54`): Both now describe `--brainstorm` as running "before the Step 1d.7 outline-approval gate (Gate A re-entry only post-plan)" (README line 61, docs/skills.md line 55). The outline gate is mentioned.
- **Item E** (`README.md:32-80` `/larch:pause`): Present at `README.md:64-67` (skills table row with description).
- **Item F** (`docs/issue-anchored-plan.md:49-71` `larch:design-pause`): `## Design Pause Block Format` section exists at line 73+ with full marker schema and `BODY_HASH` / `WARN=body-drift` semantics.

### Drop — references a feature that doesn't exist in the tree

- **Item H** (`docs/run-logs.md:126-129` assessor-verdict / plan-after-round): No `assessor-verdict-*.txt` or `plan-after-round-*.txt` paths exist in `larch-logs/design/` consumers.
- **Item I** (`skills/shared/topology.tsv` Step 3.6 plan-quality assessor): No `Step 3.6` in `skills/design/SKILL.md`, no `assessor` script under `skills/design/scripts/` or `scripts/`, no `plan-quality` references.
- **Item J** (`SECURITY.md:53-59` external assessor panel): The assessor panel referenced does not exist; current SECURITY.md already covers the existing external reviewer panels (sketch, plan-review, dialectic judges).

### Real remaining work — 3 items

- **Item B**: `docs/linting.md` harness inventory table is missing `make test-stall-recovery-report`. The harness exists at `skills/implement/scripts/test-stall-recovery-report.sh` and CI runs it via the `test-harnesses-N` shard. One new table row.
- **Item C**: `skills/implement/SKILL.md` Step 18 contains 46 `awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} ...'` rehydration lines (4 unique forms; the bulk are byte-identical). Consolidate to one canonical block plus references.
- **Item G**: `skills/design/SKILL.md:375` prose says "this cancellation fence and Step 5c item 9" but the `render-final-summary.sh --post-publish-only` invocation lives at item **10** (item 9 is `design-log-publish.sh`). One-word fix.

### Plan

Proceeding with `--simple` tier covering only Items B, C, G. When this PR ships, source OOS issues #3017, #3015, #3012, #3010 can close as superseded — only the three real edits will land, and the seven dropped items either need no change or document a non-existent feature.
