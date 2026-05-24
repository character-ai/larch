## Decision 1: Marker namespace for /design's rigid summary block
- **Question**: Should /design use `<!-- larch:final-summary v1 runid=<R> -->` (reuse /implement's marker) or introduce a new `<!-- larch:design-summary v1 runid=<R> -->`?
- **Resolution**: Reuse `larch:final-summary`. Run-id is embedded in the marker text; `tracking-issue-summary.sh upsert-summary` matches comments by FULL marker (including `runid=...`), so /design and /implement comments on the same tracking issue coexist naturally as separate comments keyed by their distinct run-ids. The rendered body's title prefix (`## /design run …` vs `## /implement run …`) disambiguates visually.
- **Source**: user

## Decision 2: Behavior on intermediate failure/cancel exit paths after Step 0a
- **Question**: For /design exit paths (Step 0b clarify-loop exit, Step 2b.5 Cancel, Step 5c plan-block-write failure, Gate C cancellation), should the rendered summary be emitted, or should those paths stay silent?
- **Resolution**: Emit the rendered summary on ALL post-Step-0a exits. The outcome field carries the appropriate value (e.g. `cancelled`, `failed`, `clarified`, `approved`); the cost bullet is always present so operators see the partial spend. Strongest single-source guarantee — there is no separate code path that prints the cost line. Pre–Step-0a aborts (session-setup failure, tier-flag mutex violation) skip the renderer because `$DESIGN_TMPDIR` does not yet exist.
- **Source**: user

## Decision 3: Chat-tail verbosity in both skills
- **Question**: Should /design adopt /implement's Step 18 chat-tail prints of `token-report.sh --summary` / `timing-report.sh --summary` (with the cost line stripped), or should both skills stay terse?
- **Resolution**: Both skills go terse. /implement Step 18's chat-tail prints are dropped entirely — both the default `--summary` branch and the `LARCH_VERBOSE_TOKENS=true --full --markdown` branch. End-of-run chat output is exactly: the rendered summary block (with the single dollar-primary cost bullet) + the machine footer. Power users still get the full per-step token/timing breakdown via the committed `larch-logs/<skill>/<run-id>/token-report.md` and `timing-report.md` log batches (produced by `refresh-run-logs.sh` → `larch-log.sh write --batch`). The Step 18 anti-paraphrase invariant prose ("do not paraphrase, reformat, or drop the dollar-primary cost line") is OBSOLETE once those prints are gone; it gets removed (not just reworded) since the new sole-source location is the rendered summary block enforced by the renderer.
- **Source**: user

## Decision 4: Load-bearing /implement Step 18 internals to preserve
- **Question**: Which /implement Step 18 mechanisms must NOT be dropped during the chat-tail removal?
- **Resolution**: Preserve (a) `token-report.sh --since-last-mark --terse > /dev/null` and `timing-report.sh --since-last-mark --terse > /dev/null` at SKILL.md ~lines 1922-1923 — these are load-bearing for the per-run token ledger window cap, not chat emissions (their stdout is already redirected to /dev/null); (b) the closing `Step 18 — done` `timing-ledger.sh mark` at ~line 1929, which caps the ledger window so subsequent runs cannot accrue to the prior run's `Step 18 — cleanup` bucket. Only the chat-printing calls (`token-report.sh --summary`, `timing-report.sh --summary`, and the `LARCH_VERBOSE_TOKENS=true` markdown variants that go to chat) are removed.
- **Source**: codebase (skills/implement/SKILL.md lines 1818, 1832-1836, 1922-1923, 1929)

## Decision 5: Multi-run coexistence on the same tracking issue
- **Question**: When a /design run is followed by an /implement run on the same tracking issue, how do their `larch:final-summary` comments interact?
- **Resolution**: They coexist as two distinct comments. `tracking-issue-summary.sh upsert-summary` (scripts/tracking-issue-summary.sh:71) matches by exact marker string including the `runid=<R>` segment. /design and /implement runs have distinct run-ids, so their markers are distinct, and the upsert creates separate comments rather than overwriting. Re-running /design with a preserved `$DESIGN_TMPDIR` (same run-id) updates its OWN comment via the PATCH path. No backward-compat migration is needed for existing tracking issues that already have older /implement-only `larch:final-summary` comments — they keep their original run-id-keyed identity.
- **Source**: codebase (scripts/tracking-issue-summary.sh:71)

## Decision 6: Committed log-batch cost duplication
- **Question**: Should the committed `larch-logs/<skill>/<run-id>/token-report.md` and `timing-report.md` files (produced by `refresh-run-logs.sh` → `larch-log.sh write --batch`) be audited to ensure no dollar-line duplication?
- **Resolution**: Yes — audit in scope. The acceptance criterion is "the rendered summary is the single authoritative dollar line". The plan must verify whether `larch-log.sh write --batch token-report` currently transcribes a dollar line into the committed `.md` from `token-report.sh`'s JSON output. If it does (e.g. via a `summary_line` field in the JSON), strip it from the batch markdown. If it does not (the JSON contains per-bucket detail without a pre-formatted dollar line), the audit is a no-op. The committed batches retain all per-bucket numeric detail; only the dollar-primary `💰 Cost: ...` line is exclusive to the rendered summary block.
- **Source**: codebase (scripts/refresh-run-logs.sh:75-80, scripts/lib-larch-log.sh inspection)

## Decision 7: Non-applicable schema fields for /design summary
- **Question**: /implement's rendered summary includes `- **PR**:` and `- **Code review**:` lines. These do not apply to /design (no PR is opened; no code is reviewed in /design — only the plan is reviewed). How should the renderer handle them?
- **Resolution**: The renderer's `--skill design` mode HIDES inapplicable lines entirely rather than emitting `N/A`. The current /implement renderer already conditionally hides the PR line when N/A (render-run-summary.sh:181-187). Extend the same conditional pattern so `--skill design` omits both `- **PR**:` and `- **Code review**:`. The `- **Plan review**:` line is meaningful for /design (carries the voting tally / accepted-finding count) and stays. For `--trivial` /design (no plan-review panel runs), the `- **Plan review**:` line shows `skipped (trivial)`. `- **OOS filed**:` stays for all /design tiers (shows `0` when none were filed). The `byte-aligned invariant` between the committed `final-summary.md` and the GitHub upsert body must hold for /design just as it does for /implement.
- **Source**: codebase (scripts/render-run-summary.sh:181-200 conditional-PR pattern) + issue body (acceptance: byte-aligned invariant)
