# extract-plan-scope-paths.sh

Extracts the canonical plan scope from a plan file's `## Files to modify/create` section.

Usage:

```bash
scripts/extract-plan-scope-paths.sh --plan-file plan.txt
scripts/extract-plan-scope-paths.sh --plan-file plan.txt -z
```

The grammar reads `### NEW:`, `### UPDATED:`, and `### REWRITTEN:` headings inside `## Files to modify/create` or the legacy `## Files to modify` heading. When neither parent heading exists, it preserves the historical scout-wrapper behavior and scans the full file. It extracts every backticked path token from the heading tail, preserving first-seen order and de-duplicating exact repeats. If a legacy heading has no backticks, it falls back to the first whitespace-delimited token when that token looks path-like.

By default the helper writes one path per line. With `-z` / `--null`, it writes NUL-delimited paths for callers that pass results into git pathspec files.

Primary callers:

- `skills/design/scripts/scout-plan-archetypes-wrapper.sh` derives scout scope files.
- `/implement` recovery flows use the same grammar for plan-scope alignment.

Edit-in-sync:

- `skills/design/scripts/scout-plan-archetypes-wrapper.sh` previously carried the inline parser; keep its behavior equivalent when changing this helper.
- `skills/implement/SKILL.md` recovery prose and `skills/implement/scripts/step2-implement.md` document this as the shared scope grammar.
