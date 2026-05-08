---
name: set-up-forked-open-source-repo
description: "Use when configuring the current clone for upstream-fork OSS contribution: rewire origin/upstream remotes, disable upstream pushes, and optionally mirror-sync the fork. Triggers: set up forked repo, configure fork remotes, rewire fork."
argument-hint: "--upstream <owner/repo> --fork <owner/repo> [--mirror-confirmed] [--init-submodules]"
allowed-tools: Bash
---

# Set Up Forked Open Source Repo

Configure the current git checkout for contributing through a personal fork:
`origin` becomes the fork, `upstream` becomes the canonical repository,
upstream pushes are disabled, and `main` tracks `origin/main`.

This skill is deliberately single-clone. Run it from the checkout you want to
configure. It refuses dirty worktrees, non-`main` checkouts, local `main` ahead
of `origin/main`, diverged local/remote `main`, ambiguous remote layouts, and
non-GitHub remotes.

## Run

Invoke the coordinator:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/set-up-forked-open-source-repo/scripts/setup-forked-open-source-repo.sh" $ARGUMENTS
```

The sibling contract for the coordinator lives at
`${CLAUDE_PLUGIN_ROOT}/skills/set-up-forked-open-source-repo/scripts/setup-forked-open-source-repo.md`.

## Arguments

- `--upstream owner/repo` — canonical upstream GitHub repository.
- `--fork owner/repo` — existing fork repository. If it is missing, the script
  prints fork-creation instructions and exits without local mutation.
- `--mirror-confirmed` — allow destructive mirror-sync when fork `main` differs
  from upstream `main`. In a non-TTY run, divergence refuses unless this flag is
  present.
- `--init-submodules` — opt into `git submodule update --init --recursive`
  after remotes are configured. Submodule setup is intentionally not default.

## Anti-Patterns

- **NEVER** run `git push --mirror` from the user's working clone, or an
  unscoped mirror push from any clone. Working clones may carry remote-tracking
  refs, and GitHub can advertise non-branch/tag refs. The coordinator uses a
  fresh temporary mirror clone plus scoped branch/tag refspecs.
- **NEVER** mutate remotes when classification is ambiguous. Guessing between
  multiple fork remotes, unexpected `upstream`, non-GitHub URLs, or multi-URL
  config can corrupt unrelated branch tracking.
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
