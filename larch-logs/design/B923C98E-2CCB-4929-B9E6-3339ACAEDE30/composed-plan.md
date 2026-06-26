## Plan

## Approach

- Treat `approach-synthesis.txt` as `NO_SKETCHES`.
- Follow the approved outline as binding scope.
- Do not re-wire CI-fix grounding.
- Do not edit `/implement` `SKILL.md` or agent prompts.
- Preserve the only unique runtime guidance from `skills/shared/ci-fix-failure-patterns.md` by moving the two `topology.tsv` constraints into `.claude/rules/topology-generation.md`.
- Delete the three orphaned reference files.
- Remove stale references that would fail missing-file checks or edit-in-sync guidance.

## Files to modify/create

### UPDATED: .claude/rules/topology-generation.md

Add a short `topology.tsv row constraints` paragraph after the existing regeneration guidance.

Include these constraints:

- `composition` must match `[A-Za-z0-9 ./+-]` only.
- `value` must appear verbatim in the row's `runtime_authority`; add new values to the authority first, then align `skills/shared/topology.tsv`.

Keep the existing paths frontmatter unchanged.

### UPDATED: skills/shared/ci-fix-failure-patterns.md

Delete this file after porting its topology-specific constraints into `.claude/rules/topology-generation.md`.

Do not replace it with a new CI launcher prompt fragment.

### UPDATED: skills/shared/focus-area-prompt.md

Delete this file.

Do not add a replacement focus-area definition.

### UPDATED: python/voting.py

Remove `"skills/shared/focus-area-prompt.md"` from `BACKTICKED_FOCUS_FILES`.

Leave `UNQUOTED_FOCUS_FILES` and focus-area enum logic unchanged.

### UPDATED: .github/workflows/ci.yaml

Remove `skills/shared/focus-area-prompt.md` from the `BACKTICKED_FILES` array in the focus-area enum check.

Do not otherwise change the CI workflow.

### UPDATED: skills/implement/references/codex-manifest-schema.digest.md

Delete this file.

Do not point Step 2 dispatch at the digest.

### UPDATED: skills/implement/references/codex-manifest-schema.md

Remove the edit-in-sync bullet that names `skills/implement/references/codex-manifest-schema.digest.md`.

Do not change the manifest schema, validation rules, examples, or bail-token list.

## Edge cases

- `python/voting.py` and `.github/workflows/ci.yaml` both enforce missing-file failures for focus-area surfaces. Remove both references in the same change as the file deletion.
- `.claude/rules/topology-generation.md` should keep the guidance concise. It should not duplicate the deleted CI-fix document wholesale.
- The topology `composition` constraint already exists in `python/rendering.py`; the rule should document it for editors, not alter validation.

## Failure modes

- If any deleted path remains in tracked files, lint or future readers may point to missing references.
- If the topology constraints are not ported before deletion, editors lose the path-triggered reminder for `skills/shared/topology.tsv`.
- If the manifest digest bullet remains, schema editors may try to update a deleted file.

## Testing strategy

Run targeted checks first:

1. `git grep -n "ci-fix-failure-patterns.md\\|focus-area-prompt.md\\|codex-manifest-schema.digest.md" -- ':!larch-logs'`
   - Expect no matches.
2. `python3 python/cli.py lint focus-area-enum`
   - Verifies the focus-area file list no longer expects the deleted file.
3. `python3 python/cli.py lint topology-rule-paths`
   - Verifies topology rule frontmatter still covers runtime authorities.
4. `python3 python/cli.py generate topology-docs --check`
   - Verifies the documented topology constraints still match generator behavior.

Then run the local subset from the outline:

5. `make py-lint`
6. `make agent-sync`

Run `make lint` if time permits or CI parity is required.

## Acceptance

Run targeted checks first:

1. `git grep -n "ci-fix-failure-patterns.md\\|focus-area-prompt.md\\|codex-manifest-schema.digest.md" -- ':!larch-logs'`
   - Expect no matches.
2. `python3 python/cli.py lint focus-area-enum`
   - Verifies the focus-area file list no longer expects the deleted file.
3. `python3 python/cli.py lint topology-rule-paths`
   - Verifies topology rule frontmatter still covers runtime authorities.
4. `python3 python/cli.py generate topology-docs --check`
   - Verifies the documented topology constraints still match generator behavior.

Then run the local subset from the outline:

5. `make py-lint`
6. `make agent-sync`

Run `make lint` if time permits or CI parity is required.

review_status: complete
rounds_completed: 1
diff_added: 5
diff_deleted: 69
mechanical_churn: false
diff_lines: 74
