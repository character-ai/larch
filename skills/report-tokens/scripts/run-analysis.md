# run-analysis.sh contract

`skills/report-tokens/scripts/run-analysis.sh` is the coordinator for `/report-tokens`.

## Purpose

Fetch closed GitHub issues in the current larch repository whose comments contain `token-report-begin`, parse the latest structured token report on each issue, estimate per-issue dollar costs for Claude/Codex/Cursor, classify issues by `**Workflow path**`, generate SIMPLE and HARD cost-over-time PNG plots, and print a written analysis.

## Primary caller

- `skills/report-tokens/SKILL.md` Step 1.

## Inputs

The script takes no positional arguments. It resolves the repository from `LARCH_REPORT_TOKENS_REPO` or `gh repo view --json nameWithOwner`.

Optional environment variables:

- `LARCH_REPORT_TOKENS_REPO=<owner/repo>` overrides repository resolution.
- `LARCH_REPORT_TOKENS_LIMIT=<N>` limits the number of matching issues fetched after search.
- `LARCH_REPORT_TOKENS_NO_OPEN=1` suppresses opening generated PNGs.
- `LARCH_RATE_<VENDOR>_<FIELD>` overrides the printed default rates in USD per million tokens.

## GitHub access

The script uses:

- `gh api --paginate -X GET search/issues -f q="repo:<owner/repo> is:issue is:closed token-report-begin in:comments" -f per_page=100 --jq ...`
- `gh issue view <number> --repo <owner/repo> --comments --json number,title,url,closedAt,body,comments`

`gh`, `jq`, and `python3` are required. Missing commands are hard failures.

## Parsing invariants

- Token reports are found by whole-line sentinel blocks from `scripts/token-report.sh`: `<!-- token-report-begin -->` through `<!-- token-report-end -->`. If no sentinel pair exists but token-report headings are present, the whole text is parsed as a fallback.
- Claude `**Grand total**` rows support both the current six-cell table shape (`Step`, `Skill`, input, cache read, cache create, output) and the legacy four-cell shape (`Step`, `Skill`, input, output).
- Codex/Cursor `**Grand total**` rows use the five-cell vendor table shape (`Step`, `Skill`, input, output, total).
- `**Workflow path**: SIMPLE|HARD|unknown` is parsed from the combined issue body and comments.
- Issue-level JSON is cached under a fresh `${TMPDIR:-/tmp}/larch-report-tokens.*` directory. The cache file is written via a temporary file and `mv`.

## Outputs

Stdout contains progress lines while fetching and then a markdown analysis with:

- cache JSON path
- generated plot paths, or a plot-skipped reason
- rates used
- aggregate cost by workflow
- top SIMPLE issues by estimated cost
- HARD phase breakdown
- cache-read dominance
- cost-reduction suggestions

Generated plots are written to `tempfile.gettempdir()` as `larch-report-tokens-simple.png` and `larch-report-tokens-hard.png`. On macOS, the script attempts to open them with `open` unless `LARCH_REPORT_TOKENS_NO_OPEN=1` is set. Plotting runs in a child Python process so missing or crashing `matplotlib` skips plot generation without losing the textual analysis.

## Cost model

The default rates are transparent estimates, not billing truth. Claude uses separate input/cache-read/cache-create/output rates; Codex and Cursor use input/output plus an aggregate rate for total-only or hidden cache-like vendor tokens. Override rates with environment variables whenever model routing or vendor pricing changes.

## Edit-in-sync

When token-report table shapes change in `scripts/token-report.sh`, update this parser and contract in the same PR.
