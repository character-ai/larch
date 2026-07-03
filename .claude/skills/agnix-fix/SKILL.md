---
name: agnix-fix
description: "Use when fixing an open agent-sh/agnix issue from this larch clone. Prepares fork label state, then forwards to /implement --forked after /design writes the plan."
argument-hint: "<upstream-issue-number> [extra-flags...]"
allowed-tools: Bash, Skill
---

# Agnix-Fix Skill

**MANDATORY — READ ENTIRE FILE before composing user-facing prose: `$PWD/skills/shared/readability-style.md`.**

Private convenience alias for fixing `agent-sh/agnix` issues from a fork clone. Goes beyond `larch:alias` flag-forwarding by (a) fetching the upstream issue body so `/implement` does not have to research it, (b) provisioning the `skip-changelog` label on the fork (idempotent), and (c) baking CI-monitoring guidance into the prompt so the orchestrator interprets the fork's deterministic `add-to-project` failure correctly.

Not shipped to other plugin consumers — placed under `.claude/skills/agnix-fix/` (dev-only).

## CI-monitoring contract

Forks of `agent-sh/agnix` cannot access org-level secrets. The `add` check (run by `add-to-project.yml` via `pull_request_target`) requires `secrets.PROJECT_TOKEN` and **always fails** on fork PRs in ~2s with `Input required and not supplied: github-token` (the action's parameter name, not the auto-provided `GITHUB_TOKEN`). The orchestrator MUST treat this as expected-to-fail and not loop on it.

**A green run on the fork** means: `ci` (`agnix` + `test`) green, `claude-review` green, `Build docs site` green, `Verify Changelog` skipped (via `[skip changelog]` title token or `skip-changelog` label). If any of those four fail, that is a real failure to fix. The `add` failure is ignored. The upstream PR (later opened by the operator against `agent-sh/agnix`) runs on `agent-sh`'s runners with all secrets, so `add-to-project` succeeds there.

For issues touching only `knowledge-base/`, `crates/agnix-rules/`, or `website/docs/rules/generated/` (rule-metadata or generated-docs corrections), prefix the PR title with `[skip changelog]`. For issues materially changing behavior or user-facing surfaces, do NOT add the prefix and author a `CHANGELOG.md` entry as part of the implementation.

### `/implement` exit routing (delegated runs)

This skill forwards to `/implement` (`skills/implement/SKILL.md`). Parse exit codes like the implement orchestrator:

| Code | Meaning |
|------|---------|
| **0** | Normal completion of the scripted path for that attempt. |
| **2** | Operator-visible hard errors (argv, missing/malformed `larch:plan`, `gh` / plan helpers, `persist-post-plan-keys` / related validation, etc.). |
| **3** | **Preflight audit refused** — terminal for this attempt until upstream work resolves the plan/clarify state. On the normal clarify path, the operator must run `/design <N>` before retrying `/implement`. When `STATE=ambiguous` from `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" clarify state`, Preflight exits **3** **before** posting or labeling; the thread must be repaired manually — exit **3** does **not** imply a new clarify request was posted. |

Do not treat every non-zero exit as a blind retry; route **3** back through `/design` / manual clarify repair, not generic re-invocation of `/implement` with the same inputs.

<!-- step:1 — Parse Arguments -->

Parse `$ARGUMENTS` as: first whitespace-separated token is the upstream issue number; any remaining tokens are passed through verbatim as extra flags to `/implement`.

```bash
read -r ISSUE_NUMBER EXTRA <<< "$ARGUMENTS"
if ! [[ "$ISSUE_NUMBER" =~ ^[0-9]+$ ]]; then
  echo "**ERROR: Usage: /agnix-fix <upstream-issue-number> [extra-flags...]**"
  exit 1
fi
```

<!-- step:2 — Verify Upstream Remote and Fetch Issue -->

Before touching the fork, confirm the current clone is wired to upstream `agent-sh/agnix` (matches `larch:set-up-forked-open-source-repo`'s output: `origin` is the fork, `upstream` is the canonical repo). Without this guard the skill would happily apply an agnix issue body to a wrong repository.

Strict owner/repo match — substring-style globs would silently accept `agent-sh/agnix-experimental`, `notagent-sh/agnix`, etc.

```bash
UPSTREAM_REPO=agent-sh/agnix
UPSTREAM_URL=$(git remote get-url upstream 2>/dev/null) || UPSTREAM_URL=""
# Normalize HTTPS (https://github.com/owner/repo[.git]) and SSH (git@github.com:owner/repo[.git],
# ssh://git@github.com/owner/repo[.git]) forms to "owner/repo". The first sed expression handles
# SSH forms; the second handles HTTPS / scp-less forms.
UPSTREAM_NWO=$(printf '%s\n' "$UPSTREAM_URL" \
  | sed -E \
      -e 's#^(ssh://)?git@github[.]com[:/]##' \
      -e 's#^(https?://)?(www[.])?github[.]com[:/]##' \
      -e 's#[.]git$##' \
      -e 's#/+$##')
if [[ "$UPSTREAM_NWO" != "$UPSTREAM_REPO" ]]; then
  echo "**ERROR: 'upstream' remote resolves to '$UPSTREAM_NWO' (raw: '$UPSTREAM_URL'), not '$UPSTREAM_REPO'. /agnix-fix only runs from a clone whose upstream is agent-sh/agnix.**"
  exit 1
fi
```

`gh` stderr is captured separately so warnings or auth hints cannot corrupt the JSON stream that `jq` parses.

```bash
GH_STDERR=$(mktemp -t agnix-fix-gh-stderr.XXXXXX)
if ! ISSUE_JSON=$(gh issue view "$ISSUE_NUMBER" --repo "$UPSTREAM_REPO" --json title,body,state,url 2>"$GH_STDERR"); then
  echo "**ERROR: gh issue view failed for $UPSTREAM_REPO#$ISSUE_NUMBER. Check authentication and that the issue exists.**"
  cat "$GH_STDERR" >&2
  rm -f "$GH_STDERR"
  exit 1
fi
rm -f "$GH_STDERR"

URL=$(echo "$ISSUE_JSON" | jq -r '.url')
STATE=$(echo "$ISSUE_JSON" | jq -r '.state')
TITLE=$(echo "$ISSUE_JSON" | jq -r '.title')
BODY=$(echo "$ISSUE_JSON" | jq -r '.body')

# PR detection by URL form (issue URLs are .../issues/<N>; PR URLs are .../pull/<N>).
if [[ "$URL" == *"/pull/"* ]]; then
  echo "**ERROR: $URL is a pull request, not an issue.**"
  exit 1
fi

if [[ "$STATE" != "OPEN" ]]; then
  echo "**ERROR: $URL is $STATE; only OPEN issues are accepted.**"
  exit 1
fi
```

<!-- step:3 — Provision skip-changelog Label on the Fork (Best-Effort) -->

Detection uses `gh api` (machine-readable HTTP status) instead of grepping the `gh label list` table, which is not a stable contract.

```bash
FORK_REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null) || FORK_REPO=""
if [[ -n "$FORK_REPO" ]]; then
  if ! gh api "repos/$FORK_REPO/labels/skip-changelog" --silent 2>/dev/null; then
    gh label create skip-changelog --repo "$FORK_REPO" \
      --description "PR does not require a CHANGELOG entry" --color ededed 2>/dev/null \
      || true
  fi
fi
```

Failure is non-fatal — the operator can add `[skip changelog]` to the PR title without the label.

<!-- step:4 — Operator briefing (no FEATURE_FILE handoff to /implement) -->

`/implement` Preflight reads the `larch:plan` block from GitHub via `python/cli.py plan-block read` and wraps issue title/body/plan in the `<reviewer_issue_title>` / `<reviewer_issue_body>` / `<reviewer_plan>` trust-boundary envelope for the adequacy audit (`skills/implement/references/preflight-plan-audit.md`). Step 1 then re-fetches the full upstream issue into `$IMPLEMENT_TMPDIR/feature-description.txt` via `gh issue view` (with `--repo "$UPSTREAM_REPO"` under `--forked`). **Do not** compose a separate delimiter-wrapped `FEATURE_FILE` expecting `/implement` to consume it — the implementer path overwrites feature text from GitHub and does not treat ad-hoc local files as authoritative.

Before invoking `/implement`, keep the CI-monitoring and changelog guidance from this skill's **CI-monitoring contract** section in orchestrator context (and in PR titles / `CHANGELOG.md` as appropriate). The upstream issue body was already fetched in Step 2 for your own verification; `/implement` repeats the read against the same upstream issue number.

<!-- step:5 — Delegate to /implement -->

Invoke the Skill tool:

- Try skill `"implement"` first (bare name). On `Unknown skill`, try `"larch:implement"` (fully-qualified plugin name).
- args: `--forked --coder=codex` then one ASCII space, then the upstream issue number `$ISSUE_NUMBER` as the **positional** `<issue-N>` tail, then any optional extra flag tokens from `$EXTRA` (must be `/implement`-supported flags only — no removed `--auto`, no verbal feature tails).

`--coder=codex` is passed explicitly so the auto-route to the main agent for small surgical plans (per issue #1481) does NOT fire on agnix work — agnix is a Rust codebase and Codex is the appropriate implementer regardless of plan size. Issue #1475 (the protected-path-modified false-positive) has landed, so the older `--coder=claude` workaround is no longer needed.

**Prerequisite**: `/design $ISSUE_NUMBER` must have written a valid `larch:plan` block to the upstream issue body before delegation — `/implement` rejects verbal feature argv and reads the plan from GitHub.
