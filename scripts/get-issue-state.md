# scripts/get-issue-state.sh — contract

`scripts/get-issue-state.sh` is the wrapper around the `gh issue view <N> --json state,url` probe that `/implement` **Step 0** uses on the adopt-by-`--issue` branch and the PR-body recovery branch to validate the adoption target before any side effect. It exists so SKILL.md no longer carries a raw `gh issue view` call inline, and so PR-vs-issue detection is one tested place rather than a `[[ "$url" == *"/pull/"* ]]` check that lives in prose.

## Inputs

- `--issue N` (required) — issue number (or PR number — the script does not assume; it reports `IS_PR=true` when the URL `gh` returns contains `/pull/`).
- `--repo OWNER/REPO` (optional) — passed through to `gh issue view`. When omitted, the script resolves the current repo with `scripts/resolve-repo.sh` and passes `--repo` if resolution succeeds; if resolution fails, `gh` resolves the repo from the cwd's git config.

## Outputs

Success (exit 0):

```
STATE=OPEN|CLOSED
URL=<url>
IS_PR=true|false
```

Failure (exit 1):

```
FAILED=true
ERROR=<single-line>
```

`gh` failure messages (multi-line, may include redactions) are flattened to a single space-separated line in `ERROR=` so the envelope stays parseable.

## Behavior notes

- **Self-validation**: `--issue` is checked for non-empty first, then validated as numeric before repo resolution or `gh` invocation. Non-empty non-numeric values fail with `FAILED=true` and `ERROR=--issue must be numeric`.
- `gh` returns the URL of whatever `<N>` resolves to, including pull-request URLs, because `gh issue view` accepts a number and dispatches against either issue or PR objects sharing the repo's number namespace. The `/pull/` substring check is the load-bearing PR-vs-issue discriminator and matches the inline rule SKILL.md previously used.
- The script does not encode the SKILL.md branching ("if `IS_PR=true`, abort; if `STATE=CLOSED`, emit `IMPLEMENT_BAIL_REASON=adopted-issue-closed`"). Callers consume the envelope and apply the policy. Keeping policy out of the wrapper means future **Step 0** adoption-branch changes (e.g., honoring `STATE=DRAFT` PRs differently) do not require touching this script.

## When to update

Update this file when the wrapper grows new fields (e.g., `LABELS=`), when the `gh` invocation changes, or when the PR-detection heuristic evolves. The `/pull/` URL substring is the canonical marker today; any switch to `gh issue view --json …` flag-based PR detection should land here and in `skills/implement/SKILL.md` **Step 0** (tracking adoption / PR-body recovery) in the same PR.

## Test harness

`scripts/test-get-issue-state.sh` is the offline regression harness for this wrapper. It is wired as Makefile target `test-get-issue-state` and registered in shard `test-harnesses-18`.

Coverage pins numeric `--issue` validation, preserved missing-argument behavior, valid numeric values reaching the `gh` boundary, `gh` failure envelopes, and the success envelope (`STATE=`, `URL=`, `IS_PR=`) with a PATH-stubbed `gh`.
