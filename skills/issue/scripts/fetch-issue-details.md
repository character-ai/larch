# fetch-issue-details.sh contract

`skills/issue/scripts/fetch-issue-details.sh` fetches full body and capped comments for candidate issues used by `/issue` Phase 2 semantic dedup reasoning. It writes every fetched issue into an untrusted-content wrapper so the downstream LLM treats GitHub text as data.

## Interface

```
fetch-issue-details.sh --numbers "N1,N2,N3" --output FILE [--repo OWNER/REPO] [--max-comments N] [--max-body-chars N]
```

When `--repo` is omitted, the script resolves the current repository with `scripts/resolve-repo.sh` and passes `--repo` to `gh issue view` when resolution succeeds. If resolution fails, it preserves the prior ambient-repo fallback.

## Output

Stdout emits one status line per requested number:

```
FETCH_STATUS_<N>=ok|failed
```

The output file is overwritten and wrapped in `<external_issues_corpus>`. Non-numeric issue ids are skipped with `FETCH_STATUS_<value>=failed`; individual fetch failures are partial failures and do not change the script's zero exit status. Non-zero exits are reserved for usage and numeric-limit validation errors.

## Edit-in-sync

Update `skills/issue/SKILL.md` Phase 2 dedup prose if the wrapper tags, truncation behavior, or status keys change.
