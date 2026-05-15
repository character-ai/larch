# get-issue-details.sh contract

`skills/fix-issue/scripts/get-issue-details.sh` fetches an issue's title, body, labels, creation timestamp, and all comments into a structured markdown file for `/fix-issue` triage.

## Interface

```
get-issue-details.sh --issue NUMBER --output PATH
```

The script resolves the current repository with `scripts/resolve-repo.sh`, passes `--repo` to `gh issue view`, and uses the same resolved `OWNER/REPO` in its comments API path. Resolution failure exits 1 before any output file is written.

## Output

On success, stdout emits:

```
OUTPUT_FILE=<path>
```

The output file includes title, labels, created-at timestamp, issue body, and each comment body with author attribution. Comments whose first line starts with `<!-- larch:` (any larch-generated summary marker from prior `/implement` runs) are excluded to prevent feedback-loop context pollution on retry runs. Exit 1 covers argument errors and GitHub fetch failures.

## Edit-in-sync

When changing the output format, update `/fix-issue` Step 2 consumers in `skills/fix-issue/SKILL.md`.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.
