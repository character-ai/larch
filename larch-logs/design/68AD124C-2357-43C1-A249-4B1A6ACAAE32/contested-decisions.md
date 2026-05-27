### DECISION_1: Verdict file location (top-level vs subdirectory under $DESIGN_TMPDIR)
- **Chosen**: top-level — `$DESIGN_TMPDIR/assessor-verdict-round-<N>.txt`
- **Alternative**: subdirectory — `$DESIGN_TMPDIR/plan-quality/round-<N>/verdict.txt` (mirrors `plan-review/round-<N>/` shape)
- **Tension**: Claude-Arch fallback argues top-level wins because `design-log-publish.sh` uses `find $DESIGN_TMPDIR -maxdepth 1 -type f` to harvest files — a subdirectory file would be orphaned unless publish-side code is also changed. Claude-Edge fallback argues the subdirectory is more consistent with the existing `plan-review/round-<N>/` layout and groups related round artifacts together; it also gives a natural home for the `.in-progress` sentinel without polluting the top level. The user's Round 1 D2 says the verdict file must be "flushed with logs" — top-level satisfies this by construction.
- **Impact**: High (affects design-log durability of the verdict + whether publish code needs concurrent changes)
- **Affected files**: `skills/design/scripts/snapshot-plan-round.sh`, `skills/design/scripts/assess-plan-round.sh`, `scripts/design-log-publish.sh`, `scripts/test-design-log-publish.sh`, `skills/design/references/assessor.md`

### DECISION_2: Combine assessor entry + dispatcher into one driver vs split into two scripts
- **Chosen**: one driver — single `skills/design/scripts/assess-plan-round.sh` that does workflow_path/round gating, snapshot validation, panel dispatch, tally, and KV emission
- **Alternative**: split — `assess-plan-round.sh` (entry orchestrator, skip/gating, calls sub-scripts) + `dispatch-plan-assessors.sh` (cross-model panel launcher) + `tally-plan-assessor.sh` (verdict tally)
- **Tension**: Codex-Pragmatic explicitly recommends collapsing the count: "consider collapsing `dispatch-plan-assessors.sh` and `assess-plan-round.sh` unless the repo's sibling-doc/testing convention strongly favors one script per concern." The repo DOES favor one-script-per-concern (the existing `dispatch-plan-voters.sh` / `tally-plan-review.sh` / `plan-review-loop.sh` triad is a precedent), but assessor is a much narrower call. Tally must remain separate (different unit of measurement from per-finding voters). The contested point is whether to also split out a dedicated dispatcher script.
- **Impact**: Medium (controls new-script count: 4 vs 5 — plus their `.md` siblings and offline harnesses)
- **Affected files**: `skills/design/scripts/assess-plan-round.sh`, `skills/design/scripts/dispatch-plan-assessors.sh` (if split), `skills/design/scripts/tally-plan-assessor.sh`, `skills/design/scripts/snapshot-plan-round.sh`, `skills/shared/scripts/render-assessor-prompt.sh`, `Makefile`, `scripts/test-design-structure.sh`

### DECISION_3: Best-so-far comparison vs prev-vs-current only
- **Chosen**: prev-vs-current only (matches user's original problem statement: "previous round's plan")
- **Alternative**: best-so-far guard — compare current against BOTH previous round AND best-known-so-far (Codex-Innovation's idea)
- **Tension**: The user's problem statement specifies prev-vs-current ("previous round's plan"); deviating would expand scope. Codex-Innovation's "best-so-far" insight catches a real failure mode — round 2 slightly better than round 1, round 3 slightly better than round 2, but cumulative drift from original. The original-plan anchor (`plan.txt-original`) gives the assessor SOME insight into cumulative drift via the prompt template (the original is the third input alongside prev + current), so the binary verdict can implicitly account for drift without needing an explicit "best" file.
- **Impact**: High (defines what the 3-input assessor prompt actually compares; alternative materially expands the snapshot file layout)
- **Affected files**: `skills/shared/scripts/render-assessor-prompt.sh`, `skills/design/scripts/snapshot-plan-round.sh`, `skills/design/scripts/assess-plan-round.sh`, `skills/design/references/assessor.md`

### DECISION_4: Verdict file body format strictness
- **Chosen**: user-specified compact body — `NOT_WORSE` on line 1 alone, OR `WORSE: <brief justification — a few sentences>` (line 1 carries semantics; user's Round 1 D2 contract verbatim)
- **Alternative**: strict KV header — `ASSESSMENT=NOT_WORSE` (line 1) plus `JUSTIFICATION=<one-line>` (line 2) on the WORSE path; case-insensitive prefix-tolerant parser per Claude-Edge fallback
- **Tension**: The compact body matches the user's Round 1 D2 byte-for-byte and is simpler for humans to read. The KV header is more parse-robust against Cursor's `**ASSESSMENT: WORSE**` markdown wrapping or assessors that emit prefixes/suffixes. But the verdict FILE (after tally) is produced by `tally-plan-assessor.sh` — the per-assessor raw output (which IS subject to markdown drift) is parsed by the tally, then the tally writes the final verdict in whichever format we choose. So the format strictness lives in the tally's OUTPUT contract, not its INPUT parsing — both options preserve tolerant parsing of assessor raw outputs upstream.
- **Impact**: Medium (affects #2871 future consumers and verdict-file readability; tally parser tolerance is independent)
- **Affected files**: `skills/design/scripts/tally-plan-assessor.sh`, `skills/design/scripts/test-tally-plan-assessor.sh`, `skills/design/references/assessor.md`

### DECISION_5: Render prompt — extend `render-voter-prompt.sh` with new id-grammar mode vs new `render-assessor-prompt.sh`
- **Chosen**: new `skills/shared/scripts/render-assessor-prompt.sh` (separate script with its own grammar, sibling to `render-voter-prompt.sh`)
- **Alternative**: extend `render-voter-prompt.sh` with `--id-grammar quality-binary` mode (Claude-Arch's idea — reuses the vendor-neutral prompt synthesis machinery)
- **Tension**: Extending `render-voter-prompt.sh` reduces total script count and inherits its prompt-rendering polish (vendor-neutral, panel-role aware, verification-context plumbing). But voter and assessor grammars are structurally different (per-ID FINDING_N/OOS_N ballot vs whole-plan binary verdict), and the voter renderer has tight coupling to `lib-vote-tally.sh`-shaped outputs. A separate render script keeps each concern uncluttered (single-responsibility) and avoids "what does this prompt produce" mode-flag confusion for future maintainers. Anti-pattern #6 also notes that voter and assessor outputs use different units of measurement (per-finding vs whole-plan delta).
- **Impact**: Medium (affects coupling between assessor and voter machinery; downstream regression risk from voter-renderer drift)
- **Affected files**: `skills/shared/scripts/render-voter-prompt.sh` (if extended), `skills/shared/scripts/render-assessor-prompt.sh` (if separate), the corresponding `.md` siblings and test harnesses
