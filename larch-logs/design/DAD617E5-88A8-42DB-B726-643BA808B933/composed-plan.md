## Plan

Approach

`approach-synthesis.txt` is `NO_SKETCHES`, so draft from direct repo inspection.

Make the smallest prompt and docs change:

1. Keep `/combine-issues` as a dev-only skill.
2. Preserve the required `Use when` trigger in frontmatter.
3. Add merit-gate wording to the frontmatter and catalog blurb.
4. Tighten oos-4 rescue handling so ambiguous rescue prose cannot reject the wrong item.

Files to modify/create

### UPDATED: .claude/skills/combine-issues/SKILL.md

Update the frontmatter `description:` to mention OOS actuality and merit checks while staying under the 200-character description cap.

In oos-4, **replace in full** the `Merit rejections require an explicit merit batch outcome:` block and the `After any rescue, rerun deduplication and grouping...` paragraph. Do not append the new contract beside the old text; delete those legacy bullets so nothing contradicts the new rules. Also update the AskUserQuestion option text to say "rescue by stable key (e.g. A or #12/A)" and remove all "free prose" language.

The replacement contract is:

**Rescue matching (key-only)**:

- **Rescue matching uses stable display keys only.** Match against the keys shown in the `Rejected items (merit)` list (e.g., `A`, `B`, `item-3`). Do not match item titles or description substrings. When bare keys collide across sources, require `#source/key` form (e.g., `#12/A`).
- **Zero-match rescue**: keep all staged merit rejections pending; emit "Rescue matched no keys; all rejections remain pending." Return to the operator for explicit keys or cancel. Do not confirm any rejection from that rescue text.
- **Multi-match rescue**: matched items stay on the staged rejection list; they are neither rescued nor confirmed rejected until the operator confirms the exact intended keys. Emit a re-confirmation prompt listing the matched items and their sources. Matched-but-unconfirmed items stay merit-pending and close-blocking.
- **Unambiguous unique-key rescue**: the named item moves to the kept-item set; unrescued listed items remain for the merit batch confirmation step.

**Single-response ordering rule**: in a single operator response, resolve rescue matching (including any multi-match key confirmation) before any merit-batch confirmation, including Apply all. Exclude confirmed-rescued keys from rejection. Apply all does not confirm merit rejections while any rescue text is zero-match or multi-match ambiguous.

**Merit batch timing**:

- Batch approval confirms rejection only for keys neither rescued nor left pending from unresolved rescue matching.
- Merit batch cannot run while any multi-match rescue awaits key confirmation.
- Confirmed rescued keys move from the staged rejection list to the kept-item set. Cancel leaves all merit rejections pending.

**Deduplication timing**:

- Rerun deduplication and grouping **only after confirmed rescues**. Do not trigger dedup after a zero-match or multi-match rescue attempt before key confirmation.

Keep all rescue and merit-batch logic as prompt prose.

### UPDATED: docs/skills.md

Update the `/combine-issues` catalog paragraph so `--oos` says it checks actuality and merit, stages low-merit rejections for approval, and proposes aggressive combinations.

Do not broaden the docs change beyond this skill entry.

Edge cases

- Keep the frontmatter description below the lint cap.
- Preserve `Use when` in the description so `agent-lint` accepts the trigger.
- Do not imply merit rejections are automatic. They still require explicit batch approval.
- Zero-match and multi-match ambiguous items remain merit-pending and close-blocking.
- Avoid changing dependency, closure, or GitHub CLI behavior.
- Bare key collision across sources requires `#source/key` disambiguation.
- Legacy `Merit rejections require...` block and `After any rescue, rerun...` paragraph must be removed; no legacy bullets may remain alongside the new contract.

Failure modes

- A too-long frontmatter description fails `lint-skill-description-length`.
- Old free-prose rescue text surviving beside the new contract creates contradictions; implementer must replace, not append.
- A rescue that triggers dedup before key confirmation produces a stale rollup; guard dedup with the confirmed-rescues gate.

Testing strategy

Run focused checks after editing:

- `python3 python/cli.py lint skill-description-length`
- `pre-commit run agent-lint --files .claude/skills/combine-issues/SKILL.md`
- `pre-commit run lint-skill-description-length --files .claude/skills/combine-issues/SKILL.md`
- `pre-commit run lint-mermaid-fences --files .claude/skills/combine-issues/SKILL.md docs/skills.md`
- `pre-commit run lint-literal-counts --files .claude/skills/combine-issues/SKILL.md docs/skills.md`

## Acceptance

See Testing strategy in plan.

review_status: complete
rounds_completed: 2
difficulty: MODERATE
diff_added: 40
diff_deleted: 8
mechanical_churn: false
diff_lines: 48
