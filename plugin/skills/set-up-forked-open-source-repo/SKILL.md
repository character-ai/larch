---
name: set-up-forked-open-source-repo
description: "Use when configuring a clone for upstream-fork OSS work: set origin/upstream remotes, disable upstream pushes, and optionally mirror-sync the fork."
argument-hint: "--upstream <owner/repo> --fork <owner/repo> [--mirror-confirmed] [--init-submodules]"
allowed-tools: Bash
---

# Set Up Forked Open Source Repo

**MANDATORY: READ ENTIRE FILE before composing user-facing prose: `${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md`.**

Configure the current git checkout for contributing through a personal fork:
`origin` becomes the fork, `upstream` becomes the canonical repository,
upstream pushes are disabled, and `main` tracks `origin/main`.

This skill is deliberately single-clone: one run may operate per clone at a
time, while separate clones can run independently. Run it from the checkout you
want to configure. It refuses dirty linked worktrees in the same clone,
in-progress git operations in any linked worktree, non-`main` checkouts, local
`main` ahead of `origin/main`, diverged local/remote `main`, ambiguous remote
layouts, and non-parseable or mixed-host remotes.

## Prerequisites

- `git` (any reasonably recent version).
- `gh` authenticated against the repository host (`github.com` by default;
  GitHub Enterprise hosts are selected from the stored `origin` URL).
- `jq` on `PATH` — used to parse `gh repo view --json` output. The coordinator
  fails fast in `phase_preflight` with an actionable message when `jq` is
  absent.
- `flock` is preferred when available, but the coordinator uses an atomic
  `mkdir` lock as the portable cross-platform guard when `flock` is absent
  (including default macOS installs).

## Trust caveat: `url.*.insteadOf`

The coordinator's URL-override allowlist
(`LARCH_FORKED_REPO_ALLOW_URL_OVERRIDE`) gates the test-seam env vars but does
NOT scan or override Git's built-in `url.<other>.insteadOf` rewrites in
user/global `gitconfig`. A `url.https://my-evil.example/.insteadOf
https://github.com/` rule would silently redirect every `git ls-remote`,
`git clone`, `git fetch`, and `git push` issued by the coordinator,
bypassing the `gh repo view` parent guard. Same-user trust model — review
your `git config --global --get-regexp '^url\..*\.insteadOf$'` before
running the skill on a profile inherited from a less-trusted source. See
SECURITY.md "Fork setup URL-override footgun" for the residual-risk
discussion. Pre-fetch URL classification (`phase_preflight` calls
`normalize_github_url` on `origin.url` before the first `git fetch origin`)
catches non-parseable, mixed-host, and multi-URL stored remote layouts but does
NOT see transport-time `insteadOf` rewrites.

## Run

Strip `--run-id <ID>` from `$ARGUMENTS` before invoking the coordinator (the script does not accept this flag). Then invoke the coordinator:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" forked-repo setup $ARGUMENTS
```

The coordinator contract lives in `python/forked_repo.py`.

## Arguments

- `--upstream owner/repo` — canonical upstream GitHub repository.
- `--fork owner/repo` — existing fork repository. If it is missing, the script
  prints fork-creation instructions and exits without local mutation.
- `--mirror-confirmed` — allow destructive mirror-sync when fork `main` differs
  from upstream `main`. In a non-TTY run, divergence refuses unless this flag is
  present.
- `--init-submodules` — opt into `git submodule update --init --recursive`
  after remotes are configured. Submodule setup is intentionally not default.
- `--run-id <ID>` — common semantics: `${CLAUDE_PLUGIN_ROOT}/skills/shared/run-id-flag.md`.

## Anti-Patterns

- **NEVER** run `git push --mirror` from the user's working clone, or an
  unscoped mirror push from any clone. Working clones may carry remote-tracking
  refs, and GitHub can advertise non-branch/tag refs. The coordinator uses a
  fresh temporary mirror clone plus scoped branch/tag refspecs.
- **NEVER** mutate remotes when classification is ambiguous. Guessing between
  multiple fork remotes, unexpected `upstream`, non-parseable URLs, mixed-host
  layouts, or multi-URL config can corrupt unrelated branch tracking.
- **NEVER** skip fork parent verification. A fork whose parent is not the
  declared upstream could receive a destructive sync from the wrong project.
- **NEVER** fall back to `master` or `HEAD`. This workflow is scoped to
  `refs/heads/main`; silent substitution hides mismatched repository policy.
- **NEVER** conflate `gh repo view` failures. Only explicit not-found means
  "fork missing"; auth, rate-limit, network, SSO, and API errors are real
  failures.
- **NEVER** fail open on rollback. If remote rewrite rollback itself fails, the
  coordinator emits a machine-readable recovery report so the operator can
  inspect and repair the local config.
- **NEVER** fast-forward from a non-`main` checkout. The coordinator refuses
  before mutation so a feature branch is never accidentally merged.
- **NEVER** initialize submodules by default. Submodule updates bypass the
  edit-hook boundary and can leave partial state; operators must opt in.
- **NEVER** trust the pre-confirmation divergence probe across a user pause. The
  coordinator re-probes immediately before the destructive fork sync.
